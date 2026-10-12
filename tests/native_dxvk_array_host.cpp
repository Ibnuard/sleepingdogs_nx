/* SPDX-License-Identifier: MIT; allocation and lifetime checks for COM arrays. */
#include "com_native_array.h"
#include "com_protocol.h"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <new>
#include <vector>

namespace {
std::size_t allocations = 0, frees = 0, live = 0;
bool fail_next = false;
std::size_t checks = 0;

[[noreturn]] void fail(const char* expression, int line) {
    std::fprintf(stderr, "FAIL line %d: %s\n", line, expression);
    std::exit(1);
}
#define CHECK(expression) do { ++checks; if (!(expression)) fail(#expression, __LINE__); } while (0)

__attribute__((noinline)) void* allocate(std::size_t bytes) {
    if (fail_next) { fail_next = false; throw std::bad_alloc(); }
    void* pointer = std::malloc(bytes ? bytes : 1);
    if (!pointer) throw std::bad_alloc();
    ++allocations; ++live;
    return pointer;
}
__attribute__((noinline)) void release(void* pointer) noexcept {
    if (pointer) { ++frees; --live; std::free(pointer); }
}
__attribute__((noinline)) void use(int** values, std::size_t count, int* marker) {
    for (std::size_t i = 0; i < count; ++i) CHECK(values[i] == nullptr);
    if (count) { values[0] = marker; values[count - 1] = marker; }
}
template<typename Array> __attribute__((noinline)) void binding_call(std::size_t count, int* marker) {
    Array values(count);
    use(values.data(), values.size(), marker);
    if (count) CHECK(values[count - 1] == marker);
}
} // namespace

void* operator new(std::size_t bytes) { return allocate(bytes); }
void* operator new[](std::size_t bytes) { return allocate(bytes); }
void operator delete(void* pointer) noexcept { release(pointer); }
void operator delete[](void* pointer) noexcept { release(pointer); }
void operator delete(void* pointer, std::size_t) noexcept { release(pointer); }
void operator delete[](void* pointer, std::size_t) noexcept { release(pointer); }

int main() {
    using Array = sd_com::NativePointerArray<int*>;
    static_assert(!std::is_copy_constructible<Array>::value, "storage cannot alias");
    static_assert(!std::is_move_constructible<Array>::value, "inline pointer cannot escape");
    int marker = 42;
    for (std::size_t count : {std::size_t(0), std::size_t(1), std::size_t(12), std::size_t(128),
                              std::size_t(129), std::size_t(SD_COM_MAX_ARRAY)}) {
        auto before = allocations, live_before = live, frees_before = frees;
        {
            Array values(count);
            CHECK(values.size() == count);
            CHECK((values.data() != nullptr) == (count != 0));
            CHECK(allocations - before == (count > 128 ? 1u : 0u));
            CHECK(live - live_before == (count > 128 ? 1u : 0u));
            if (count && count <= 128) {
                auto start = reinterpret_cast<std::uintptr_t>(&values);
                auto data = reinterpret_cast<std::uintptr_t>(values.data());
                CHECK(data >= start && data + count * sizeof(int*) <= start + sizeof(values));
            }
            use(values.data(), values.size(), &marker);
            const Array& const_values = values;
            if (count) CHECK(const_values.data()[count - 1] == const_values[count - 1]);
        }
        CHECK(live == live_before);
        CHECK(frees - frees_before == (count > 128 ? 1u : 0u));
    }
    // Inline calls must still work when the allocator would fail; the fallback
    // must propagate bad_alloc for the outer bridge catch without leaking.
    fail_next = true;
    binding_call<Array>(128, &marker);
    CHECK(fail_next);
    auto live_before = live, before = allocations;
    bool caught = false;
    try { Array values(129); } catch (const std::bad_alloc&) { caught = true; }
    CHECK(caught && !fail_next);
    CHECK(live == live_before && allocations == before);
    // Exception unwinding from a later dispatch step must release fallback
    // storage, without applying AddRef/Release to its pointer elements.
    try { Array values(129); values[0] = &marker; throw 7; } catch (int value) { CHECK(value == 7); }
    CHECK(live == live_before);

    constexpr unsigned iterations = 10000;
    before = allocations;
    for (unsigned i = 0; i < iterations; ++i) binding_call<std::vector<int*>>(i % 2 ? 12 : 128, &marker);
    auto baseline_allocations = allocations - before;
    before = allocations;
    for (unsigned i = 0; i < iterations; ++i) binding_call<Array>(i % 2 ? 12 : 128, &marker);
    auto inline_allocations = allocations - before;
    CHECK(baseline_allocations == iterations);
    CHECK(inline_allocations == 0);
    CHECK(live == 0 && allocations == frees);
    std::printf("{\"status\":\"PASS\",\"checks\":%zu,\"binding_calls\":%u,\"vector_allocations\":%zu,"
                "\"inline_allocations\":%zu,\"live_allocations\":%zu,\"allocation_failure_checked\":true,"
                "\"zero_initialization_checked\":true,\"unwind_cleanup_checked\":true}\n",
                checks, iterations, baseline_allocations, inline_allocations, live);
}
