/* LGPL-2.1-or-later. Reserved native backing for late Wine worker stacks. */
#pragma once
#include <switch.h>

void wine_nx_f1_native_stacks_init(void);
void wine_nx_f1_native_stacks_snapshot(void);
Result wine_nx_f1_native_stack_retry(Result previous, Thread *thread, ThreadFunc entry,
                                   void *arg, void *stack, size_t size, int priority, int core);
