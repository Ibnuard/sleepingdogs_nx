/* LGPL-2.1-or-later. Debug context staged while a new WoW64 thread is suspended. */
#ifndef SD_THREAD_DEBUG_H
#define SD_THREAD_DEBUG_H

/* Protected by horizon_server_objects_mutex and owned by the thread object,
 * not its handle or TEB. The child may not have published its TEB yet. */
struct sd_thread_debug
{
    DWORD dr0, dr1, dr2, dr3, dr6, dr7;
    BOOL valid;
};
C_ASSERT(offsetof(I386_CONTEXT, Dr7) - offsetof(I386_CONTEXT, Dr0) == 20);
C_ASSERT(offsetof(struct sd_thread_debug, valid) == 24);

NTSTATUS sd_wow64_remote_debug_context(HANDLE handle, I386_CONTEXT *context, BOOL set);
BOOL sd_wow64_apply_start_debug(TEB *teb, I386_CONTEXT *context);
#endif
