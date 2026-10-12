/* SPDX-License-Identifier: MIT; deterministic host gate/lifetime scenarios. */
#include "../src/native_dxvk_com/present_overlap.h"
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <future>
#include <stdexcept>
#include <vector>

using namespace std::chrono_literals;
struct Object {
    int refs=1,adds=0,releases=0;
    void AddRef(){assert(refs>0);++refs;++adds;}
    void Release(){assert(refs>0);--refs;++releases;}
};
static std::atomic<unsigned> checks{0};
static void require(bool value){++checks;assert(value);}
template<class T> static void ready(std::future<T>& f){require(f.wait_for(5s)==std::future_status::ready);}

int main(){
    for(unsigned iteration=0;iteration<100;++iteration) {
        std::recursive_mutex gate;SdPresentOverlap overlap;Object object;
        std::promise<void> entered,finish;auto entered_future=entered.get_future();auto finish_future=finish.get_future();
        auto presenter=std::async(std::launch::async,[&]{
            std::unique_lock<std::recursive_mutex> lock(gate);
            require(overlap.admit(lock,false));
            return overlap.invoke(lock,&object,[&]{entered.set_value();finish_future.wait();return 123;});
        });
        ready(entered_future);
        auto deferred=std::async(std::launch::async,[&]{
            std::unique_lock<std::recursive_mutex> lock(gate);
            require(overlap.admit(lock,true));require(overlap.active);require(object.refs==2);
            std::unique_lock<std::recursive_mutex> nested(gate);
            require(!overlap.admit(nested,false,true));
            require(!overlap.admit(nested,true,true));
        });
        ready(deferred);deferred.get();
        // Four distinct operations that must remain serialized: immediate,
        // second Present, token Release, and shutdown. All use the same gate.
        std::vector<std::future<void>> serialized;
        std::atomic<unsigned> completed{0};
        for(unsigned n=0;n<4;++n)serialized.emplace_back(std::async(std::launch::async,[&]{
            std::unique_lock<std::recursive_mutex> lock(gate);
            require(overlap.admit(lock,false));require(!overlap.active);require(object.refs==1);++completed;
        }));
        auto deadline=std::chrono::steady_clock::now()+5s;
        for(;;){
            {std::lock_guard<std::recursive_mutex> lock(gate);if(overlap.waited==4)break;}
            require(std::chrono::steady_clock::now()<deadline);std::this_thread::yield();
        }
        require(completed==0);finish.set_value();ready(presenter);require(presenter.get()==123);
        for(auto& work:serialized){ready(work);work.get();}
        require(completed==4);require(overlap.released==1);require(overlap.admitted==1);
        require(object.refs==1&&object.adds==1&&object.releases==1);
    }
    {
        std::recursive_mutex gate;SdPresentOverlap overlap;Object object;
        std::unique_lock<std::recursive_mutex> lock(gate);
        try {
            overlap.invoke(lock,&object,[&]()->int {
                // Model a native callback re-entering dispatch on this thread.
                std::unique_lock<std::recursive_mutex> nested(gate);
                require(!overlap.admit(nested,false));require(!overlap.admit(nested,true));
                throw std::runtime_error("injected Present failure");
            });
            require(false);
        }catch(const std::runtime_error&){}
        require(lock.owns_lock());require(!overlap.active);require(object.refs==1);
        require(overlap.admit(lock,false));
        require(overlap.invoke(lock,&object,[]{return -1;})==-1);
        require(lock.owns_lock()&&!overlap.active&&object.refs==1);
        require(object.adds==2&&object.releases==2);
    }
    std::printf("{\"status\":\"PASS\",\"checks\":%u,\"concurrency_rounds\":100,\"hardware_tested\":false}\n",checks.load());
}
