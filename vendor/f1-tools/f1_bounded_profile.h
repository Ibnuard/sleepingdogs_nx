/* LGPL-2.1-or-later. Pure gate for the F1 circuit diagnostic sampler. */
#ifndef F1_BOUNDED_PROFILE_H
#define F1_BOUNDED_PROFILE_H
#include <stdint.h>
struct f1_profile_gate {
    unsigned slow_windows, attempted;
};
/* Two consecutive nonempty 3-25 FPS windows, each at least eight seconds.
 * This is a workload heuristic, not detection of the game's current scene. */
static int f1_profile_gate_window(struct f1_profile_gate *gate,
                                  uint64_t elapsed_us, uint64_t frames)
{
    if (gate->attempted) return 0;
    int slow = elapsed_us >= UINT64_C(8000000) && elapsed_us <= UINT64_C(30000000) &&
        frames >= 1 && frames <= UINT64_C(1000000) &&
        frames*UINT64_C(1000000) >= elapsed_us*3 &&
        frames*UINT64_C(1000000) <= elapsed_us*25;
    gate->slow_windows = slow ? gate->slow_windows+1 : 0;
    if (gate->slow_windows < 2) return 0;
    gate->attempted = 1;
    return 1;
}
#endif
