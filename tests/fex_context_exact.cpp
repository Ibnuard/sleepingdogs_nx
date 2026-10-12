// SPDX-License-Identifier: MIT
// Differential against the pinned serializer plus an independent host x87
// arithmetic oracle. The candidate remains integer-only even for signaling NaNs.
#include "horizon_fpu.h"
#include "exact_x87.h"
#include <cstdio>
#include <cstdlib>
#include <cfenv>
#include <cfloat>
#include <chrono>
#include <algorithm>
#include <vector>
#include <cstring>
#pragma STDC FENV_ACCESS ON
using pes13_fex_fp::Extended;
extern "C" void OldImport(void*,const void*,uint16_t,uint16_t,bool);
extern "C" void NewImport(void*,const void*,uint16_t,uint16_t,bool);
extern "C" void OldExport(void*,const void*,uint16_t,bool);
static uint64_t checks=0,oracle=0,seed=0x134580047771dead;
static uint64_t random_bits(){seed^=seed<<13;seed^=seed>>7;seed^=seed<<17;return seed;}
static void require(bool ok){++checks;if(!ok){std::fprintf(stderr,"FAIL at check %llu\n",(unsigned long long)checks);std::exit(1);}}
static uint64_t fast(Extended x,uint16_t c){return sd_fex_context::narrow(x,c,pes13_fex_fp::narrow);}
static void compare(Extended x) {
    for(unsigned mode=0;mode<4;++mode){uint16_t c=0x37f|(mode<<10);require(fast(x,c)==pes13_fex_fp::narrow(x,c));}
}
int main(int argc,char**) {
    const uint64_t sigs[]={0,1,0x3ff,0x400,0x7ff,0x800,0x7fffffffffffffffULL,
        0x8000000000000000ULL,0x8000000000000001ULL,0x8000000000000400ULL,
        0x8000000000000800ULL,0xfffffffffffff800ULL,~uint64_t(0)};
    // Every 15-bit exponent, both signs, all four rounding modes; the values
    // straddle integer-bit, rounding, underflow, overflow and exactness edges.
    for(unsigned e=0;e<65536;++e)for(auto s:sigs)compare({s,e});
    for(unsigned i=0;i<500000;++i) {
        compare({random_bits(),random_bits()});
        auto bits=random_bits();auto x=pes13_fex_fp::expand(bits);compare(x);
        for(unsigned mode=0;mode<4;++mode)require(fast(x,0x37f|(mode<<10))==bits);
    }
    for(unsigned i=0;i<8192;++i)for(unsigned top=0;top<8;++top)for(unsigned reduced=0;reduced<2;++reduced) {
        alignas(16) uint64_t input[8][2],a[10][2],b[10][2];
        for(auto& r:input){r[0]=random_bits();r[1]=random_bits();}
        if(i&1)for(auto& r:input){auto x=pes13_fex_fp::expand(r[0]);r[0]=x.significand;r[1]=x.exponent;}
        std::memset(a,0xa5,sizeof(a));std::memset(b,0xa5,sizeof(b));
        auto control=uint16_t(random_bits());
        OldImport(a+1,input,top<<11,control,reduced);NewImport(b+1,input,top<<11,control,reduced);
        require(!std::memcmp(a,b,sizeof(a)));
    }
#if defined(__x86_64__) && LDBL_MANT_DIG==64
    int modes[]={FE_TONEAREST,FE_DOWNWARD,FE_UPWARD,FE_TOWARDZERO};
    for(unsigned mode=0;mode<4;++mode){require(!fesetround(modes[mode]));
        for(unsigned i=0;i<40000;++i){
            Extended x={random_bits()|(1ULL<<63),(random_bits()%0x7ffe)+1};if(i&1)x.exponent|=0x8000;
            long double raw=0;std::memcpy(&raw,&x,10);volatile long double input=raw;
            volatile double converted=static_cast<double>(input);double value=converted;uint64_t bits;std::memcpy(&bits,&value,8);
            require(bits==fast(x,0x37f|(mode<<10)));++oracle;
        }
    }
    require(!fesetround(FE_TONEAREST));
#endif
    // Separate, alternating, warmed host CPU measurements. No GPU/FEX/Wine
    // execution; these numbers cannot be converted into gameplay FPS.
    std::printf("{\"status\":\"PASS\",\"checks\":%llu,\"x87_oracle\":%llu,\"benchmark\":[",(unsigned long long)checks,(unsigned long long)oracle);
    const char* names[]={"normal","zero","mixed_special","general80"};
    uint64_t checksum=0;
    if(argc>1)for(unsigned kind=0;kind<4;++kind){
        alignas(16) uint64_t values[64][8][2],out[8][2];
        for(auto& row:values)for(auto& r:row){
            auto x=pes13_fex_fp::expand(kind==0?(0x3fe0000000000000ULL|(random_bits()&0xfffffffffffffULL)):
                kind==1?(random_bits()&(1ULL<<63)):random_bits());
            r[0]=kind==3?random_bits():x.significand;r[1]=kind==3?random_bits():x.exponent;
        }
        if(kind==2)for(unsigned j=0;j<64;++j){const uint64_t edges[]={1,0x7ff0000000000000ULL,0x7ff0000000000001ULL,0x8000000000000000ULL};
            for(unsigned i=0;i<4;++i){auto x=pes13_fex_fp::expand(edges[i]);values[j][i][0]=x.significand;values[j][i][1]=x.exponent;}}
        std::vector<double> ns[2];
        for(unsigned pass=0;pass<7;++pass)for(unsigned order=0;order<2;++order){
            unsigned label=order^(pass&1);auto fn=label?NewImport:OldImport;auto start=std::chrono::steady_clock::now();
            for(unsigned i=0;i<1000000;++i){fn(out,values[i&63],(i&7)<<11,0x37f,true);checksum^=out[i&7][0];}
            auto elapsed=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count();
            if(pass)ns[label].push_back(double(elapsed)/1000000);
        }
        for(auto& v:ns)std::sort(v.begin(),v.end());
        auto a=(ns[0][2]+ns[0][3])/2,b=(ns[1][2]+ns[1][3])/2;
        std::printf("%s{\"case\":\"%s\",\"old_ns\":%.3f,\"new_ns\":%.3f,\"ratio\":%.4f}",kind?",":"",names[kind],a,b,a/b);
    }
    std::printf("],\"checksum\":%llu,\"hardware_tested\":false,\"game_fps_measured\":false}\n",(unsigned long long)checksum);
}
