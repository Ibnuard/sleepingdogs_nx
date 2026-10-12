/* SPDX-License-Identifier: MIT; typed ARM64 COM dispatch, no native pointer escapes. */
#include "com_protocol.h"
#include "com_methods.h"
#include "com_progress.h"
#include "com_native_array.h"
#include <d3d11.h>
#include <d3d10.h>
#include <dxgi.h>
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstring>
#include <limits>
#include <map>
#include <mutex>
#include <new>
#include <set>
#include <stdexcept>
#include <unordered_map>
#include <vector>
extern "C" HRESULT CreateDXGIFactory2(UINT,REFIID,void**);
extern "C" int virtual_check_buffer_for_read(const void*,size_t);
extern "C" int virtual_check_buffer_for_write(void*,size_t);
extern "C" void wine_nx_runtime_trace(const char*);

namespace {
struct Fault { HRESULT code; explicit Fault(HRESULT value):code(value){} };
float bits_float(uint32_t u){float f;std::memcpy(&f,&u,4);return f;}
uint32_t bits_float(float f){uint32_t u;std::memcpy(&u,&f,4);return u;}
struct GuidInfo { uint32_t kind;GUID guid;const char* name; };
const GuidInfo guids[]={
#include "com_guids.inc"
};
#include "com_inheritance.inc"
struct Slot { IUnknown* object=nullptr;uint32_t kind=0,refs=0,generation=1,guest_window=0,next_free=0;bool fullscreen=false; };
struct NativeKey {
    IUnknown* pointer;uint32_t kind;
    bool operator==(const NativeKey& b)const{return pointer==b.pointer&&kind==b.kind;}
};
struct KeyHash { size_t operator()(const NativeKey& k)const{return (reinterpret_cast<uintptr_t>(k.pointer)>>3)^k.kind;} };
struct PrivateKey {
    IUnknown* identity;GUID guid;
    bool operator<(const PrivateKey& b)const {
        if(identity!=b.identity)return std::less<IUnknown*>()(identity,b.identity);
        return std::memcmp(&guid,&b.guid,sizeof(guid))<0;
    }
};
struct MapRecord {
    uint32_t id=0,subresource=0,type=0,bytes=0,guest=0;
    ID3D11DeviceContext* context=nullptr;ID3D11Resource* resource=nullptr;
    D3D11_MAPPED_SUBRESOURCE native={};
};
struct Context {
    std::recursive_mutex mutex;
    std::vector<Slot> slots{1};
    uint32_t first_free=0;
    std::unordered_map<NativeKey,uint32_t,KeyHash> index;
    std::map<PrivateKey,bool> private_interfaces;
    std::set<std::array<uint8_t,16>> unknown_iids;
    std::unordered_map<uint32_t,MapRecord> maps;
    uint32_t next_map=1;
    bool stopped=false;
    uint64_t calls=0,presents=0,draws=0,map_bytes=0,failures=0,last_stats_ns=0;
    uint64_t discard_maps=0,discard_zero_bytes_skipped=0;
    uint32_t startup_traces=0;
#ifdef SD_COM_HOST_FAULT_TESTS
    int32_t adopt_failure_after=-1;
#endif
    template<typename T> T* read(uint32_t address,uint64_t count=1) {
        if(!address || !count)return nullptr;
        uint64_t bytes=count*sizeof(T);
        if(count>UINT32_MAX/sizeof(T)||address<0x10000||uint64_t(address)+bytes>(uint64_t(1)<<32)||
           !virtual_check_buffer_for_read(reinterpret_cast<void*>(uintptr_t(address)),size_t(bytes)))throw Fault(E_POINTER);
        return reinterpret_cast<T*>(uintptr_t(address));
    }
    template<typename T> T* write(uint32_t address,uint64_t count=1) {
        if(!address || !count)return nullptr;
        uint64_t bytes=count*sizeof(T);
        // The pinned Wine write probe uses volatile read-modify-write on each
        // page and both endpoints, inside its exception handler. It validates
        // readability as well as writability; do not repeat the read probe.
        // Retain all bounds checks and probe every call (no permission cache).
        if(count>UINT32_MAX/sizeof(T)||address<0x10000||uint64_t(address)+bytes>(uint64_t(1)<<32)||
           !virtual_check_buffer_for_write(reinterpret_cast<void*>(uintptr_t(address)),size_t(bytes)))throw Fault(E_POINTER);
        return reinterpret_cast<T*>(uintptr_t(address));
    }
    template<typename T> T* required_read(uint32_t address,uint64_t count=1) {
        T* p=read<T>(address,count);if(!p)throw Fault(E_POINTER);return p;
    }
    template<typename T> T* required_write(uint32_t address,uint64_t count=1) {
        T* p=write<T>(address,count);if(!p)throw Fault(E_POINTER);return p;
    }
    uint32_t array_count(uint32_t n) {
        if(n>SD_COM_MAX_ARRAY)throw Fault(E_INVALIDARG);
        return n;
    }
    uint32_t keep_array_count(uint32_t n){return n==UINT32_MAX?0:array_count(n);}
    const char* string(uint32_t address) {
        if(!address)return nullptr;
        for(uint32_t i=0;i<4096;++i)if(!*required_read<char>(address+i))return reinterpret_cast<const char*>(uintptr_t(address));
        throw Fault(E_INVALIDARG);
    }
    uint32_t iid(REFIID value) {
        for(const auto& info:guids)if(info.guid==value)return info.kind;
        std::array<uint8_t,16> key;std::memcpy(key.data(),&value,16);
        if(unknown_iids.size()<64&&unknown_iids.insert(key).second){
            char line[192];std::snprintf(line,sizeof(line),"[SD-NDX-COM] UNKNOWN_IID %08x-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x returns E_NOINTERFACE",
                value.Data1,value.Data2,value.Data3,value.Data4[0],value.Data4[1],value.Data4[2],value.Data4[3],value.Data4[4],value.Data4[5],value.Data4[6],value.Data4[7]);
            wine_nx_runtime_trace(line);
        }
        return 0;
    }
    Slot& slot(uint32_t token,uint32_t expected=0) {
        uint32_t n=token&0xffffu,g=token>>16;
        if(!n||n>=slots.size()||!slots[n].object||slots[n].generation!=g||
           (expected&&!interface_is_a(slots[n].kind,expected)))throw Fault(E_INVALIDARG);
        return slots[n];
    }
    template<typename T> T* object(uint32_t token,uint32_t expected) {
        return token?reinterpret_cast<T*>(slot(token,expected).object):nullptr;
    }
    uint32_t adopt(IUnknown* object,uint32_t kind) {
        if(!object)return 0;
        if(!kind){object->Release();throw Fault(E_NOINTERFACE);}
        NativeKey key{object,kind};auto found=index.find(key);
        if(found!=index.end()){++slots[found->second].refs;return (slots[found->second].generation<<16)|found->second;}
        uint32_t n=0;bool reused=false;
        try {
#ifdef SD_COM_HOST_FAULT_TESTS
            if(adopt_failure_after==0){adopt_failure_after=-1;throw std::bad_alloc();}
            if(adopt_failure_after>0)--adopt_failure_after;
#endif
            if(!first_free) {
                if(slots.size()>=65536)throw Fault(E_OUTOFMEMORY);
                n=uint32_t(slots.size());slots.emplace_back();
            } else {n=first_free;reused=true;}
            index.emplace(key,n);
        }catch(...){object->Release();if(n&&!reused&&n+1==slots.size())slots.pop_back();throw;}
        if(reused)first_free=slots[n].next_free;
        slots[n].object=object;slots[n].kind=kind;slots[n].refs=1;slots[n].guest_window=0;slots[n].fullscreen=false;
        return (slots[n].generation<<16)|n;
    }
    IUnknown* identity(IUnknown* object) {
        IUnknown* result=nullptr;
        if(FAILED(object->QueryInterface(__uuidof(IUnknown),reinterpret_cast<void**>(&result))))throw Fault(E_NOINTERFACE);
        result->Release();return result;
    }
    void QueryInterface(sd_com_packet& p) {
        const auto value=*required_read<GUID>(p.args[0]);auto output=required_write<uint32_t>(p.args[1]);*output=0;
        uint32_t kind=iid(value);if(!kind){p.ret=E_NOINTERFACE;return;}
        const auto original=slot(p.object);
        IUnknown* obj=nullptr;p.ret=original.object->QueryInterface(value,reinterpret_cast<void**>(&obj));
        if(SUCCEEDED(HRESULT(p.ret))){*output=adopt(obj,kind);auto& alias=slot(*output);
            alias.guest_window=original.guest_window;alias.fullscreen=original.fullscreen;}
    }
    void set_window_metadata(uint32_t token,uint32_t window,bool fullscreen) {
        auto key=identity(slot(token).object);
        for(auto& s:slots)if(s.object&&identity(s.object)==key){s.guest_window=window;s.fullscreen=fullscreen;}
    }
    void AddRef(sd_com_packet& p){auto& s=slot(p.object);s.object->AddRef();p.ret=++s.refs;}
    void Release(sd_com_packet& p) {
        uint32_t n=p.object&0xffffu;auto& s=slot(p.object);
        uint32_t refs=--s.refs;IUnknown* obj=s.object;
        if(!refs){index.erase({s.object,s.kind});s.object=nullptr;s.kind=0;
            if(s.generation<0xffffu){++s.generation;s.next_free=first_free;first_free=n;}}
        obj->Release();p.ret=refs;
    }
    void unsupported(sd_com_packet& p,const char* method) {
        char line[224];std::snprintf(line,sizeof(line),"[SD-NDX-COM] UNSUPPORTED %s object=%08x",method,p.object);wine_nx_runtime_trace(line);
        p.ret=E_NOTIMPL;p.fault=E_NOTIMPL;
    }
    void report(bool force=false) {
        // Reports are ten seconds apart. Avoid a clock query per state/draw.
        if(!force&&(calls&1023u))return;
        uint64_t now=sd_com_clock_ns();if(!force&&now-last_stats_ns<10000000000ull)return;
        last_stats_ns=now;char line[256];
        std::snprintf(line,sizeof(line),"[SD-NDX-COM] calls=%llu draws=%llu presents=%llu live_interfaces=%zu maps=%zu map_copy_bytes=%llu failures=%llu; ARM64 DXVK, real COM",
            (unsigned long long)calls,(unsigned long long)draws,(unsigned long long)presents,index.size(),maps.size(),(unsigned long long)map_bytes,(unsigned long long)failures);
        wine_nx_runtime_trace(line);
        std::snprintf(line,sizeof(line),"[SD-NDX-MAP] discard_maps=%llu zero_fill_skipped_bytes=%llu; preserving copy-in and full copy-out retained",
            (unsigned long long)discard_maps,(unsigned long long)discard_zero_bytes_skipped);
        wine_nx_runtime_trace(line);
    }
    void abort_map(uint32_t id) {
        auto it=maps.find(id);if(it==maps.end())throw Fault(E_INVALIDARG);
        auto m=it->second;maps.erase(it);m.context->Unmap(m.resource,m.subresource);m.resource->Release();m.context->Release();
    }
    void shutdown() {
        while(!maps.empty())abort_map(maps.begin()->first);
        for(auto& s:slots)if(s.object&&s.kind==SD_COM_IF_ID3D11DeviceContext) {
            auto ctx=reinterpret_cast<ID3D11DeviceContext*>(s.object);ctx->ClearState();ctx->Flush();
        }
        index.clear();
        for(auto& s:slots)if(s.object){auto obj=s.object;uint32_t refs=s.refs;s.object=nullptr;s.refs=s.kind=0;while(refs--)obj->Release();}
        stopped=true;first_free=0;private_interfaces.clear();report(true);
    }
};
Context state;
sd_com_progress::State progress;
sd_com_progress::Snapshot progress_values{}; // Only accessed while holding state.mutex.
constexpr uint64_t progress_stride=256;
uint64_t progress_entries=0;
struct ProgressCall {
    bool active=false;uint64_t entry;
    void begin(sd_com_progress::Stage phase) {
        using namespace sd_com_progress;
        progress_values[Entry]=entry;progress_values[Thread]=sd_com_thread_id();
        progress_values[Call]=progress_values[Interface]=progress_values[Method]=progress_values[Object]=0;
        for(unsigned i=Arg0;i<=Arg4;++i)progress_values[i]=0;
        progress_values[Phase]=phase;progress_values[Begin]=sd_com_clock_ns();
        progress_values[End]=progress_values[Ret]=progress_values[FaultCode]=0;
        progress.publish(progress_values);
    }
    ProgressCall():entry(++progress_entries) {
        active=entry<=128||!(entry&(progress_stride-1));
        if(active)begin(sd_com_progress::Validate);
    }
    void packet(const sd_com_packet& p,bool force=false) {
        bool critical=!p.interface_id||p.interface_id==SD_COM_IF_ID3D11Device||
            (p.interface_id==SD_COM_IF_IDXGISwapChain&&p.method==SD_COM_M_IDXGISwapChain_Present)||
            (p.interface_id==SD_COM_IF_ID3D11DeviceContext&&
             (p.method==SD_COM_M_ID3D11DeviceContext_Map||p.method==SD_COM_M_ID3D11DeviceContext_Unmap||
              p.method==SD_COM_M_ID3D11DeviceContext_Flush));
        if(!active&&(critical||force)){active=true;begin(sd_com_progress::Execute);}
        if(!active)return;
        using namespace sd_com_progress;
        progress_values[Call]=state.calls;progress_values[Interface]=p.interface_id;
        progress_values[Method]=p.method;progress_values[Object]=p.object;
        for(unsigned i=0;i<5;++i)progress_values[Arg0+i]=p.args[i];
        progress_values[Phase]=Execute;progress.publish(progress_values);
    }
    void result(const sd_com_packet& p) {
        if(!active&&HRESULT(p.fault)<0)packet(p,true);
        if(!active)return;
        using namespace sd_com_progress;
        progress_values[Ret]=p.ret;progress_values[FaultCode]=p.fault;
        progress_values[Phase]=ResultCopy;progress.publish(progress_values);
    }
    ~ProgressCall() {
        if(!active)return;
        using namespace sd_com_progress;
        progress_values[Phase]=Idle;progress_values[End]=sd_com_clock_ns();
        progress_values[Calls]=state.calls;progress_values[Draws]=state.draws;
        progress_values[Presents]=state.presents;progress_values[Maps]=state.maps.size();
        progress_values[CopyBytes]=state.map_bytes;progress_values[Refs]=state.index.size();
        progress_values[Failures]=state.failures;progress.publish(progress_values);
    }
};

// Bound synchronous startup logging to three Presents / 128 calls. BEGIN is
// emitted before native work; a missing END identifies an unfinished call,
// not necessarily a deadlock. This is diagnostic wall time, never GPU timing.
const char* startup_call_name(const sd_com_packet& p,uint64_t presents) {
    if(!p.interface_id) {
        if(p.method==SD_COM_BIND_MAP)return "BindMap";
        if(p.method==SD_COM_ABORT_MAP)return "AbortMap";
    }
    if(p.interface_id==SD_COM_IF_IDXGISwapChain&&p.method==SD_COM_M_IDXGISwapChain_Present)return "Present";
    if(p.interface_id==SD_COM_IF_ID3D11DeviceContext) {
        if(p.method==SD_COM_M_ID3D11DeviceContext_Map)return "Map";
        if(p.method==SD_COM_M_ID3D11DeviceContext_Unmap)return "Unmap";
        if(p.method==SD_COM_M_ID3D11DeviceContext_GetData)return "GetData";
        if(p.method==SD_COM_M_ID3D11DeviceContext_Flush)return "Flush";
        if(presents&&p.method>2)return "Context";
    }
    return nullptr;
}
struct StartupTrace {
    Context& c;sd_com_packet& p;const char* name=nullptr;
    uint64_t start=0,call=0,thread=0;
    StartupTrace(Context& context,sd_com_packet& packet):c(context),p(packet) {
        if(c.presents>=3||c.startup_traces>=128)return;
        name=startup_call_name(p,c.presents);if(!name)return;
        ++c.startup_traces;start=sd_com_clock_ns();call=c.calls;thread=sd_com_thread_id();
        char line[384];std::snprintf(line,sizeof(line),
            "[SD-NDX-CALL] BEGIN call=%llu thread=%llx name=%s interface=%u method=%u object=%08x presents=%llu time_us=%llu args=%08x,%08x,%08x,%08x,%08x",
            (unsigned long long)call,(unsigned long long)thread,name,p.interface_id,p.method,p.object,
            (unsigned long long)c.presents,(unsigned long long)(start/1000),p.args[0],p.args[1],p.args[2],p.args[3],p.args[4]);
        wine_nx_runtime_trace(line);
    }
    void finish() {
        if(!name)return;
        uint64_t now=sd_com_clock_ns();char line[384];std::snprintf(line,sizeof(line),
            "[SD-NDX-CALL] END call=%llu thread=%llx name=%s ret=%08x fault=%08x aux=%u bytes=%u wall_us=%llu presents=%llu maps=%zu copy_bytes=%llu",
            (unsigned long long)call,(unsigned long long)thread,name,p.ret,p.fault,p.aux,p.high[0],
            (unsigned long long)((now>=start?now-start:0)/1000),(unsigned long long)c.presents,c.maps.size(),(unsigned long long)c.map_bytes);
        wine_nx_runtime_trace(line);
        if(c.presents>=3||c.startup_traces==128)
            wine_nx_runtime_trace("[SD-NDX-CALL] startup trace complete; three Presents or 128 traced calls reached; normal logging continues");
    }
};

// Pointer-bearing descriptors and mapped data need explicit adapters.
#include "com_native_adapters.inc"

void global_call(Context& c,sd_com_packet& p) {
    switch(p.method) {
    case SD_COM_CREATE_DEVICE: {
        if(p.args[2]){p.ret=E_INVALIDARG;return;}
        auto adapter=c.object<IDXGIAdapter>(p.args[0],SD_COM_IF_IDXGIAdapter);
        auto levels=c.read<D3D_FEATURE_LEVEL>(p.args[4],c.array_count(p.args[5]));
        auto out_device=c.write<uint32_t>(p.args[7]);auto out_context=c.write<uint32_t>(p.args[9]);
        auto out_level=c.write<D3D_FEATURE_LEVEL>(p.args[8]);
        if(out_device)*out_device=0;
        if(out_context)*out_context=0;
        ID3D11Device* device=nullptr;ID3D11DeviceContext* context=nullptr;
        p.ret=D3D11CreateDevice(adapter,D3D_DRIVER_TYPE(p.args[1]),nullptr,p.args[3],levels,p.args[5],p.args[6],
            out_device?&device:nullptr,out_level,out_context?&context:nullptr);
        if(SUCCEEDED(HRESULT(p.ret))){
            uint32_t device_token=0,context_token=0;
            try {
                // adopt consumes its native reference, including on failure.
                if(out_device){auto owned=device;device=nullptr;device_token=c.adopt(owned,SD_COM_IF_ID3D11Device);}
                if(out_context){auto owned=context;context=nullptr;context_token=c.adopt(owned,SD_COM_IF_ID3D11DeviceContext);}
            }catch(...){
                if(device)device->Release();
                if(context)context->Release();
                for(auto token:{context_token,device_token})if(token){sd_com_packet release={};release.object=token;c.Release(release);}
                throw;
            }
            if(out_device)*out_device=device_token;
            if(out_context)*out_context=context_token;
        }
        char line[192];std::snprintf(line,sizeof(line),"[SD-NDX-COM] D3D11CreateDevice hr=%08x device=%08x context=%08x feature=%x native=ARM64",p.ret,out_device?*out_device:0,out_context?*out_context:0,out_level?*out_level:0);wine_nx_runtime_trace(line);return;
    }
    case SD_COM_CREATE_FACTORY: {
        const GUID value=*c.required_read<GUID>(p.args[1]);auto out=c.required_write<uint32_t>(p.args[2]);*out=0;
        uint32_t kind=c.iid(value);if(!kind){p.ret=E_NOINTERFACE;return;}
        IUnknown* factory=nullptr;p.ret=CreateDXGIFactory2(p.args[0],value,reinterpret_cast<void**>(&factory));
        if(SUCCEEDED(HRESULT(p.ret)))*out=c.adopt(factory,kind);
        return;
    }
    case SD_COM_BIND_MAP: {
        auto it=c.maps.find(p.args[0]);if(it==c.maps.end())throw Fault(E_INVALIDARG);auto& m=it->second;
        if(m.guest||p.args[2]!=m.bytes)throw Fault(E_INVALIDARG);
        auto shadow=c.required_write<unsigned char>(p.args[1],m.bytes);m.guest=p.args[1];
        if(m.type!=D3D11_MAP_WRITE_DISCARD){std::memcpy(shadow,m.native.pData,m.bytes);c.map_bytes+=m.bytes;}
        else {
            // WRITE_DISCARD defines prior contents as undefined. Reused guest
            // storage need not be zeroed; the application initializes the data
            // it consumes. All preserving modes still copy in, and Unmap still
            // copies out. Writable-range validation above remains mandatory.
            ++c.discard_maps;c.discard_zero_bytes_skipped+=m.bytes;
        }
        p.ret=0;return;
    }
    case SD_COM_ABORT_MAP:c.abort_map(p.args[0]);p.ret=0;return;
    case SD_COM_STATS: {
        auto out=c.required_write<uint32_t>(p.args[0],8);
        out[0]=uint32_t(c.calls);out[1]=uint32_t(c.draws);out[2]=uint32_t(c.presents);out[3]=uint32_t(c.index.size());
        out[4]=uint32_t(c.maps.size());out[5]=uint32_t(c.map_bytes);out[6]=uint32_t(c.failures);out[7]=SD_COM_ABI;p.ret=0;c.report(true);return;
    }
    case SD_COM_SHUTDOWN:c.shutdown();p.ret=0;return;
    default:c.unsupported(p,"invalid global call");return;
    }
}
void execute(Context& c,sd_com_packet& p) {
    if(!p.interface_id){global_call(c,p);return;}
    switch(p.interface_id) {
#include "com_native_dispatch.inc"
    default:return c.unsupported(p,"invalid interface id");
    }
}
int32_t unix_dispatch(void* request) {
    progress.waiting.fetch_add(1);
    std::lock_guard<std::recursive_mutex> guard(state.mutex);
    progress.waiting.fetch_sub(1);
    ProgressCall watch;
    uintptr_t address=reinterpret_cast<uintptr_t>(request);
    if(address>UINT32_MAX)return int32_t(0xc0000005u);
    sd_com_packet* output=nullptr;
    try {
        output=state.required_write<sd_com_packet>(uint32_t(address));sd_com_packet p=*output;
        if(p.abi!=SD_COM_ABI||p.reserved)return int32_t(0xc000000du);
        p.ret=p.fault=p.aux=0;
        ++state.calls;
        watch.packet(p);
        StartupTrace trace(state,p);
        try{if(state.stopped&&!(p.interface_id==0&&p.method==SD_COM_STATS))throw Fault(E_INVALIDARG);execute(state,p);}catch(const Fault& f){p.fault=p.ret=f.code;}catch(const std::bad_alloc&){p.fault=p.ret=E_OUTOFMEMORY;}catch(...){p.fault=p.ret=E_FAIL;}
        trace.finish();
        if(HRESULT(p.fault)<0){++state.failures;char line[192];std::snprintf(line,sizeof(line),"[SD-NDX-COM] FAULT interface=%u method=%u object=%08x hr=%08x",p.interface_id,p.method,p.object,p.fault);wine_nx_runtime_trace(line);}
        watch.result(p);*output=p;state.report();return 0;
    }catch(...){return int32_t(0xc0000005u);}
}
}
extern "C" {
void sd_com_progress_report() {
    using namespace sd_com_progress;
    static uint64_t previous=0;uint64_t now=sd_com_clock_ns();
    if(previous&&now>=previous&&now-previous<5000000000ull)return;
    previous=now;Snapshot v{};char line[512];
    if(!progress.read(v)){wine_nx_runtime_trace("[SD-NDX-PROGRESS] snapshot busy; retry next interval");return;}
    uint64_t age=v[Begin]&&now>=v[Begin]?(now-v[Begin])/1000000:0;
    uint64_t wall=v[End]>=v[Begin]?(v[End]-v[Begin])/1000:0;
    const char* phase=v[Phase]==Validate?"validate":v[Phase]==Execute?"execute":v[Phase]==ResultCopy?"result-copy":"idle";
    std::snprintf(line,sizeof(line),"[SD-NDX-PROGRESS] calls=%llu draws=%llu presents=%llu maps=%llu refs=%llu copy_bytes=%llu failures=%llu gate_waiters=%llu sample_stride=256; totals are last sampled completed call",
        (unsigned long long)v[Calls],(unsigned long long)v[Draws],(unsigned long long)v[Presents],(unsigned long long)v[Maps],
        (unsigned long long)v[Refs],(unsigned long long)v[CopyBytes],(unsigned long long)v[Failures],(unsigned long long)progress.waiting.load());
    wine_nx_runtime_trace(line);
    std::snprintf(line,sizeof(line),"[SD-NDX-ACTIVE] entry=%llu call=%llu thread=%llx phase=%s interface=%llu method=%llu object=%08x age_ms=%llu completed_wall_us=%llu ret=%08x fault=%08x args=%08x,%08x,%08x,%08x,%08x",
        (unsigned long long)v[Entry],(unsigned long long)v[Call],(unsigned long long)v[Thread],phase,
        (unsigned long long)v[Interface],(unsigned long long)v[Method],unsigned(v[Object]),(unsigned long long)age,(unsigned long long)wall,
        unsigned(v[Ret]),unsigned(v[FaultCode]),unsigned(v[Arg0]),unsigned(v[Arg1]),unsigned(v[Arg2]),unsigned(v[Arg3]),unsigned(v[Arg4]));
    wine_nx_runtime_trace(line);
}
extern const sd_com_unix_entry wine_nx_sd_com_wow64_unix_funcs[]={unix_dispatch};
extern const unsigned int wine_nx_sd_com_wow64_unix_count=1;
void sd_com_shutdown(){std::lock_guard<std::recursive_mutex> guard(state.mutex);state.shutdown();}
#ifdef SD_COM_HOST_FAULT_TESTS
void sd_com_test_fail_adopt_after(int32_t count){std::lock_guard<std::recursive_mutex> guard(state.mutex);state.adopt_failure_after=count;}
int sd_com_test_progress_snapshot(uint64_t* out) {
    sd_com_progress::Snapshot value{};if(!progress.read(value))return 0;
    std::memcpy(out,value.data(),sizeof(value));return 1;
}
#endif
}
