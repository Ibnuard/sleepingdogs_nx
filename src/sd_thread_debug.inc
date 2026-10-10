/* LGPL-2.1-or-later. Included after Horizon's typed handle lookup.
 * Only a never-started, suspended thread has a stable context here. Running
 * remote threads still require a separate FEX safepoint implementation. */
#include "sd_wow64_debug_cache.h"

NTSTATUS sd_wow64_remote_debug_context(HANDLE handle, I386_CONTEXT *context, BOOL set)
{
    struct horizon_server_object *object = NULL;
    TEB *caller = NtCurrentTeb();
    NTSTATUS status;

    if (!context) return STATUS_INVALID_PARAMETER;
    if (context->ContextFlags != CONTEXT_I386_DEBUG_REGISTERS) return STATUS_NOT_SUPPORTED;
    if ((ULONG_PTR)handle > 0xffffffffu) return STATUS_INVALID_HANDLE;

    pthread_mutex_lock(&horizon_server_objects_mutex);
    status = horizon_server_find_typed_object_locked((unsigned int)(ULONG_PTR)handle,
                                                     HORIZON_SERVER_OBJECT_THREAD, &object);
    if (!status)
    {
        if (object->thread.terminated) status = STATUS_THREAD_IS_TERMINATING;
        else if (object->thread.pid != (ULONG_PTR)caller->ClientId.UniqueProcess ||
                 object->thread.started || object->thread.suspend <= 0)
            status = STATUS_NOT_SUPPORTED;
        else if (set)
        {
            memcpy(&object->sd_debug.dr0, &context->Dr0, 24);
            object->sd_debug.valid = TRUE;
        }
        else if (object->sd_debug.valid) memcpy(&context->Dr0, &object->sd_debug.dr0, 24);
        else memset(&context->Dr0, 0, 24);
    }
    pthread_mutex_unlock(&horizon_server_objects_mutex);
    return status;
}

BOOL sd_wow64_apply_start_debug(TEB *teb, I386_CONTEXT *context)
{
    struct horizon_server_object *object;
    BOOL applied = FALSE;

    if (!teb || !context || !get_wow_teb(teb)) return FALSE;
    pthread_mutex_lock(&horizon_server_objects_mutex);
    for (object = horizon_server_threads; object; object = object->thread_next)
    {
        if (object->thread.tid != (ULONG_PTR)teb->ClientId.UniqueThread ||
            object->thread.pid != (ULONG_PTR)teb->ClientId.UniqueProcess) continue;
        if (!object->thread.terminated && object->thread.started &&
            object->thread.teb == (ULONG_PTR)teb && object->sd_debug.valid)
        {
            /* runtime_init_x86_context has already cleared and initialized the
             * CPU area. Publish both copies before WoW64/FEX can load it. */
            memcpy(&context->Dr0, &object->sd_debug.dr0, 24);
            sd_wow64_sync_debug_cache(get_wow_teb(teb), context);
            object->sd_debug.valid = FALSE;
            applied = TRUE;
        }
        break;
    }
    pthread_mutex_unlock(&horizon_server_objects_mutex);
    return applied;
}
