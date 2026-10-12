/* SPDX-License-Identifier: MIT; temporary native COM pointer conversion storage. */
#pragma once
#include <algorithm>
#include <array>
#include <cstddef>
#include <type_traits>

namespace sd_com {

// D3D11 binding arrays fit in 128 entries. Larger supported bridge arrays retain
// a throwing heap fallback, so the dispatcher's existing E_OUTOFMEMORY handling
// still applies. This owns the array storage only, never the COM references.
template<typename Pointer, std::size_t InlineCapacity = 128>
class NativePointerArray {
    static_assert(std::is_pointer<Pointer>::value, "COM pointer storage only");
    static_assert(InlineCapacity > 0, "inline storage must not be empty");
    std::array<Pointer, InlineCapacity> inline_;
    std::size_t size_;
    Pointer* data_;

public:
    explicit NativePointerArray(std::size_t count)
        : size_(count),
          data_(count > InlineCapacity ? new Pointer[count]() : count ? inline_.data() : nullptr) {
        // Initialize only the live prefix; zeroing unused capacity would add
        // work to the common one-element and short binding calls.
        if (count && count <= InlineCapacity) std::fill_n(data_, count, nullptr);
    }
    ~NativePointerArray() {
        if (size_ > InlineCapacity) delete[] data_;
    }
    NativePointerArray(const NativePointerArray&) = delete;
    NativePointerArray& operator=(const NativePointerArray&) = delete;
    NativePointerArray(NativePointerArray&&) = delete;
    NativePointerArray& operator=(NativePointerArray&&) = delete;

    std::size_t size() const { return size_; }
    Pointer* data() { return data_; }
    const Pointer* data() const { return data_; }
    Pointer& operator[](std::size_t index) { return data_[index]; }
    const Pointer& operator[](std::size_t index) const { return data_[index]; }
};

} // namespace sd_com
