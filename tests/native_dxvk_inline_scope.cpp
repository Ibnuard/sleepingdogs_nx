/* SPDX-License-Identifier: MIT; bounds, exception unwinding and thread scopes. */
#include "com_inline.h"
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <thread>
static unsigned checks;
static void check(bool value){++checks;if(!value)std::abort();}
int main() {
    sd_com_packet p{};p.interface_id=SD_COM_IF_ID3D11DeviceContext;p.method=8;p.reserved=SD_COM_INLINE_MAGIC|3u;
    check(!sd_com::current_inline_range().covers(0x10000,4));
    {
        sd_com::InlineScope outer;outer.allow(0x10000,p);
        auto& span=sd_com::current_inline_range();
        check(span.covers(0x1002c,116));check(!span.covers(0x1002b,1));check(!span.covers(0x1009f,2));
        check(!span.covers(0x100a0,1));check(!span.covers(0x100a0,0));check(!span.covers(0xfffffffcu,8));
        check(!span.covers(0x1002c,UINT64_MAX));
        try {
            sd_com::InlineScope inner;check(!span.covers(0x1002c,4));inner.allow(0x20000,p);
            check(span.covers(0x2002c,4));check(!span.covers(0x1002c,4));throw 3;
        } catch(int) {}
        check(span.covers(0x1002c,4));check(!span.covers(0x2002c,4));
        std::atomic<unsigned> ready{0};std::atomic<bool> release{false},passed{true};
        std::thread other([&] {
            if(sd_com::current_inline_range().covers(0x1002c,4))passed=false;
            sd_com::InlineScope inner;inner.allow(0x30000,p);++ready;
            while(!release.load())std::this_thread::yield();
            if(!sd_com::current_inline_range().covers(0x3002c,4)||sd_com::current_inline_range().covers(0x1002c,4))passed=false;
        });
        while(!ready.load())std::this_thread::yield();
        check(span.covers(0x1002c,4));check(!span.covers(0x3002c,4));release=true;other.join();check(passed);
        {
            sd_com::InlineScope unmarked;p.reserved=0x53430003u;
            unmarked.allow(0x10000,p);check(!span.covers(0x1002c,4));
        }
    }
    check(!sd_com::current_inline_range().covers(0x1002c,4));
    std::printf("{\"status\":\"PASS\",\"checks\":%u,\"nested_exception_scope\":true,\"concurrent_scope\":true}\n",checks);
}
