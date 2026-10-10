// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>

// Execution breakpoints only. Data/I/O watchpoints must not become execution traps.
inline uint32_t SDExecDebugMask(uint32_t dr7) {
  uint32_t mask = 0;
  for (unsigned i = 0; i != 4; ++i)
    if (((dr7 >> (2 * i)) & 3) && !((dr7 >> (16 + 4 * i)) & 15))
      mask |= 1u << i;
  return mask;
}

bool SDHasDebugTargets();
bool SDIsDebugTarget(uint64_t address);
