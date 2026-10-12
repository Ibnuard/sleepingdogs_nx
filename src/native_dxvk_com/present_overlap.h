/* SPDX-License-Identifier: MIT; bounded overlap of Present and deferred contexts. */
#pragma once
#include <condition_variable>
#include <cstdint>
#include <mutex>
#include <thread>
#include <utility>

/* Every field and method is protected by the bridge's recursive mutex. Only
 * the raw, independently pinned swapchain Present runs without that mutex.
 * Callers admit genuine deferred-context methods and the BindMap/AbortMap
 * lifecycle of those contexts. Immediate/device/swapchain/other global calls,
 * including shutdown, must wait.
 * Explicit Multithread Enter scopes and nested dispatch retain the old path. */
struct SdPresentOverlap {
    std::condition_variable_any changed;
    std::thread::id owner;
    bool active=false;
    uint64_t released=0,admitted=0,waited=0;

    bool admit(std::unique_lock<std::recursive_mutex>& lock,bool deferred,bool nested=false) {
        // Waiting would release only the innermost recursive lock. A callback
        // from an admitted deferred worker must fail rather than retaining its
        // outer lock while the presenting thread waits to reacquire it.
        if(active && (nested || owner==std::this_thread::get_id()))return false;
        if(active && deferred){++admitted;return true;}
        if(active)++waited;
        changed.wait(lock,[this]{return !active;});
        return true;
    }
    template<class Object,class Call>
    auto invoke(std::unique_lock<std::recursive_mutex>& lock,Object* object,Call call)
        -> decltype(call()) {
        // Pin before publication or unlock. The bridge token may be dropped by
        // future compatible work; this independently owns the native lifetime.
        object->AddRef();
        active=true;owner=std::this_thread::get_id();++released;
        lock.unlock();
        try {
            auto result=call();
            lock.lock();
            active=false;owner={};
            object->Release();
            changed.notify_all();
            return result;
        } catch(...) {
            lock.lock();
            active=false;owner={};
            object->Release();
            changed.notify_all();
            throw;
        }
    }
};
