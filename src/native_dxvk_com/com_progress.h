/* SPDX-License-Identifier: MIT; snapshots never acquire the COM dispatch gate. */
#ifndef SD_COM_PROGRESS_H
#define SD_COM_PROGRESS_H
#include <array>
#include <atomic>
#include <cstdint>

namespace sd_com_progress {
enum Field { Thread, Entry, Call, Interface, Method, Object, Arg0, Arg1, Arg2, Arg3, Arg4,
             Phase, Begin, End, Ret, FaultCode, Calls, Draws, Presents, Maps, CopyBytes, Refs, Failures, Count };
enum Stage { Idle, Validate, Execute, ResultCopy };
using Snapshot=std::array<uint64_t,Count>;
struct State {
    // One writer, protected by the existing COM gate. Atomic fields keep even
    // rejected optimistic reads well-defined under the C++ memory model.
    std::atomic<uint64_t> sequence{0},waiting{0};
    std::array<std::atomic<uint64_t>,Count> fields{};
    void publish(const Snapshot& value) {
        sequence.fetch_add(1);
        for(unsigned i=0;i<Count;++i)fields[i].store(value[i]);
        sequence.fetch_add(1);
    }
    bool read(Snapshot& value) const {
        for(unsigned attempt=0;attempt<3;++attempt) {
            uint64_t before=sequence.load();if(before&1)continue;
            for(unsigned i=0;i<Count;++i)value[i]=fields[i].load();
            if(sequence.load()==before)return true;
        }
        return false;
    }
};
static_assert(std::atomic<uint64_t>::is_always_lock_free,"Progress must not acquire hidden locks");
}
#endif
