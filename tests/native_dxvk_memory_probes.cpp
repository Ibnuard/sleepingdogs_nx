/* Actual Context range methods and pinned Wine probe bodies are generated
 * from source. POSIX signal recovery models Wine SEH; not a Wine runtime test. */
#include <algorithm>
#include <atomic>
#include <chrono>
#include <csetjmp>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <sys/mman.h>
#include <thread>
#include <unistd.h>
using BOOL=int;using SIZE_T=size_t;
#define TRUE 1
#define FALSE 0
static size_t host_page_size;
struct Fault { int code; explicit Fault(int v):code(v){} };
constexpr int E_POINTER=int(0x80004003u);
struct ProbeFrame;
static thread_local ProbeFrame* frame_top;
struct ProbeFrame {
    sigjmp_buf state;ProbeFrame* prior;
    ProbeFrame():prior(frame_top){frame_top=this;}
    ~ProbeFrame(){frame_top=prior;}
};
static void fault_handler(int signal) {
    if(frame_top)siglongjmp(frame_top->state,1);
    _exit(128+signal);
}
#define __TRY do { ProbeFrame frame; if(sigsetjmp(frame.state,1)==0)
#define __EXCEPT else
#define __ENDTRY } while(0);
static thread_local uint64_t read_probes,write_probes;
#include "wine_probe_bodies.inc"
extern "C" int virtual_check_buffer_for_read(const void* p,size_t n){++read_probes;return pinned_read(p,n);}
extern "C" int virtual_check_buffer_for_write(void* p,size_t n){++write_probes;return pinned_write(p,n);}
#include "bridge_ranges.inc"
static std::atomic<unsigned> checks{0};
static void require(bool good){++checks;if(!good)throw std::runtime_error("memory probe assertion");}
template<typename T,typename C> bool probe(C& c,bool write,uint32_t address,uint64_t count){
    try{auto out=write?c.template write<T>(address,count):c.template read<T>(address,count);return !address||!count?out==nullptr:out!=nullptr;}
    catch(const Fault& f){require(f.code==E_POINTER);return false;}
}
int main(){try{
    host_page_size=size_t(sysconf(_SC_PAGESIZE));require(host_page_size==4096);
    struct sigaction action{},old_segv{},old_bus{};action.sa_handler=fault_handler;sigemptyset(&action.sa_mask);
    require(!sigaction(SIGSEGV,&action,&old_segv));require(!sigaction(SIGBUS,&action,&old_bus));
    constexpr uint32_t base=0x20000000;
    auto memory=static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(uintptr_t(base)),16384,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
    require(memory!=MAP_FAILED&&uintptr_t(memory)==base);std::memset(memory,0xa7,16384);
    OldRanges old;NewRanges current;
    for(unsigned mask=0;mask<27;++mask){
        unsigned bits=mask;
        for(unsigned page=0;page<3;++page){unsigned mode=bits%3;bits/=3;int protection=mode==0?PROT_NONE:mode==1?PROT_READ:PROT_READ|PROT_WRITE;
            require(!mprotect(memory+page*4096,4096,protection));}
        for(uint32_t offset:{0u,1u,4095u,4096u,4097u,8191u,8192u,12287u})
        for(uint64_t count:{0ull,1ull,2ull,159ull,160ull,4096ull,4097ull,8193ull})
        for(bool write:{false,true}){
            bool before=probe<unsigned char>(old,write,base+offset,count);
            bool after=probe<unsigned char>(current,write,base+offset,count);
            require(before==after);require(frame_top==nullptr);
        }
    }
    require(!mprotect(memory,16384,PROT_READ|PROT_WRITE));
    for(unsigned i=0;i<16384;++i)require(memory[i]==0xa7);
    for(uint32_t address:{0u,1u,0xffffu,0x10000u,0xfffffff0u,0xffffffffu})
    for(uint64_t count:{0ull,1ull,32ull,0xffffffffull,0x100000000ull,0xffffffffffffffffull})
    for(bool write:{false,true})require(probe<uint64_t>(old,write,address,count)==probe<uint64_t>(current,write,address,count));
    // One native writable packet check per call instead of read + write. The
    // old/new paths execute the same volatile Wine probe bodies and exception
    // model, not a constant-return permission stub.
    constexpr unsigned iterations=100000;
    uint64_t probes[2][2]{};double elapsed[2]{};
    for(unsigned version=0;version<2;++version){
        read_probes=write_probes=0;auto begin=std::chrono::steady_clock::now();
        for(unsigned i=0;i<iterations;++i)require(version?probe<unsigned char>(current,true,base+17,160):probe<unsigned char>(old,true,base+17,160));
        elapsed[version]=double(std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-begin).count())/iterations;
        probes[version][0]=read_probes;probes[version][1]=write_probes;
    }
    require(probes[0][0]==iterations&&probes[0][1]==iterations&&probes[1][0]==0&&probes[1][1]==iterations);
    // Fault recovery frames are thread-local; valid calls must still work
    // after repeatedly probing an unmapped address from simultaneous workers.
    std::thread a([&]{NewRanges c;for(unsigned i=0;i<1000;++i){require(!probe<char>(c,true,0x10000,160));require(probe<char>(c,true,base+128,160));}});
    std::thread b([&]{NewRanges c;for(unsigned i=0;i<1000;++i){require(!probe<char>(c,false,0x10000,160));require(probe<char>(c,true,base+8192,160));}});
    a.join();b.join();require(!munmap(memory,16384));
    require(!probe<char>(current,true,base,160));require(!sigaction(SIGSEGV,&old_segv,nullptr));require(!sigaction(SIGBUS,&old_bus,nullptr));
    std::printf("{\"status\":\"PASS\",\"checks\":%u,\"protection_layouts\":27,\"iterations\":%u,\"old_read_probes\":%llu,\"old_write_probes\":%llu,\"current_read_probes\":%llu,\"current_write_probes\":%llu,\"old_ns_per_check\":%.3f,\"current_ns_per_check\":%.3f}\n",checks.load(),iterations,(unsigned long long)probes[0][0],(unsigned long long)probes[0][1],(unsigned long long)probes[1][0],(unsigned long long)probes[1][1],elapsed[0],elapsed[1]);
}catch(const std::exception& e){std::fprintf(stderr,"FAIL %s\n",e.what());return 1;}}
