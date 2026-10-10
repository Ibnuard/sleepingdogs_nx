/* SPDX-License-Identifier: MIT. Process restart, never an in-process NRO reload. */
#ifndef F1_RELAUNCH_H
#define F1_RELAUNCH_H
#include <stdint.h>
#include <stddef.h>

enum f1_relaunch_kind { F1_RETURN_GUEST = 1, F1_RETURN_EXCEPTION,
                       F1_RETURN_ABORT, F1_RETURN_NATIVE_EXIT, F1_RETURN_RESOURCE,
                       F1_RETURN_COMPILER };
struct f1_return_record { uint32_t words[16]; };

static uint32_t f1_return_checksum(const struct f1_return_record *r)
{
    const unsigned char *bytes = (const unsigned char *)r;
    uint32_t hash = 2166136261u;
    for (unsigned i = 0; i < 60; ++i) hash = (hash ^ bytes[i]) * 16777619u;
    return hash;
}
static struct f1_return_record f1_return_make(uint64_t pending)
{
    struct f1_return_record r = {{0}};
    r.words[0] = 0x31524646; /* FFR1, little endian */
    r.words[1] = 1;
    r.words[2] = pending >> 32;
    r.words[3] = (uint32_t)pending;
    r.words[4] = 128;
    r.words[15] = f1_return_checksum(&r);
    return r;
}
static int f1_return_valid(const struct f1_return_record *r, size_t size)
{
    return size == sizeof(*r) && r->words[0] == 0x31524646 && r->words[1] == 1 &&
        r->words[2] >= F1_RETURN_GUEST && r->words[2] <= F1_RETURN_COMPILER &&
        r->words[15] == f1_return_checksum(r);
}

unsigned wine_nx_f1_relaunch_arm(void);
void wine_nx_f1_relaunch_disarm(void);
int wine_nx_f1_relaunch_consume(char *message, size_t capacity);
int wine_nx_f1_relaunch_request(unsigned kind, unsigned code);
void wine_nx_f1_relaunch_fatal(unsigned kind, unsigned code);
void wine_nx_f1_compiler_stopped(unsigned bytes);
void wine_nx_f1_relaunch_poll(void);
#endif
