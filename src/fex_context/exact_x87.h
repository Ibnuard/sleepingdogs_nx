// SPDX-License-Identifier: MIT
// Exact shortcut for the PES13/FEXTendo x87 context serializer. This is not
// guest arithmetic: do not use host floating-point conversions or fast-math.
#pragma once
#include <cstdint>

namespace sd_fex_context {
template<typename Extended, typename Fallback>
inline __attribute__((always_inline)) uint64_t narrow(Extended value, uint16_t control,
                                                      Fallback fallback) {
    const unsigned exponent = value.exponent & 0x7fff;
    const uint64_t sign = (value.exponent & 0x8000) << 48;
    // A normalized extended value in binary64's normal exponent range whose
    // low 11 significand bits are zero is already exactly representable.
    // Every x87 rounding mode therefore gives these same bits. The explicit
    // integer bit must be set; unsupported x87 encodings use the old path.
    if (exponent - 15361u <= 2045u && (value.significand >> 63) &&
        !(value.significand & 0x7ff)) {
        return sign | (uint64_t(exponent - 15360u) << 52) |
               ((value.significand >> 11) & 0xfffffffffffffULL);
    }
    // Signed zero is common in untouched registers. A zero significand with
    // a nonzero exponent is an unsupported encoding, not a zero.
    if (!exponent && !value.significand) return sign;
    return fallback(value, control);
}
}
