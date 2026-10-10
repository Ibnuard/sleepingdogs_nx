"""Add bounded F1 crash capture to the isolated native source copy."""
from f1_overlay import exact, replace_function

DECL = '''extern void wine_nx_f1_crash_note(const char *);
extern void wine_nx_f1_crash_stage(const char *, int, unsigned long long, unsigned long long);
'''


def patch_runtime_crash(source: str) -> str:
    source = exact(source, 'static int fx_debug_live;', DECL + '''extern unsigned wine_nx_f1_crash_init(int, int, int);
static uint64_t f1_guest_exit_state;
static int fx_debug_live;''')
    source = exact(source,
        '        __atomic_store_n(&fx_debug_live,0,__ATOMIC_RELEASE);\n'
        '        __atomic_store_n(&f1_startup_watch_enabled,0,__ATOMIC_RELEASE);\n'
        '        pthread_mutex_lock(&fx_debug_file_lock);\n'
        '        if(fx_debug_file){fclose(fx_debug_file);fx_debug_file=NULL;}\n'
        '        pthread_mutex_unlock(&fx_debug_file_lock);',
        '        __atomic_store_n(&f1_startup_watch_enabled,0,__ATOMIC_RELEASE);\n'
        '        wine_nx_f1_crash_note("launcher-released; game surface pending; runtime log remains open");')
    source = exact(source, '        if(ready){log_line("[FEXTENDO-RENDERER]',
        '        if(ready){\n'
        '            unsigned crash_rc=wine_nx_f1_crash_init(fx_ui_view.debug,renderer,selected);\n'
        '            log_line("[F1-CRASH] init_rc=%08x path=crash.log previous=crash-previous.log renderer=%d profile=%d",crash_rc,renderer,selected);\n'
        '            log_line("[FEXTENDO-RENDERER]')
    source = exact(source, '    if (!strncmp(line,"[BIND]",6)) return;',
        '    if (!strncmp(line,"[BIND]",6)) return;\n'
        '    if (!strncmp(line,"[EXC]",5)||!strncmp(line,"[FAIL]",6)||\n'
        '        !strncmp(line,"[STDERR]",8)||!strncmp(line,"[NXVK]",6)||\n'
        '        !strncmp(line,"[NXGL]",6)||!strncmp(line,"[F1-THREAD",10)||\n'
        '        !strncmp(line,"[F1-GUEST",9)||!strncmp(line,"[F1-VKMEM]",10)||\n'
        '        !strncmp(line,"[F1-SCRATCH-RECOVER]",20))\n'
        '        wine_nx_f1_crash_note(line);')
    source = exact(source, '    int compositor = wine_nx_compositor_enabled();\n    NWindow *window = NULL;',
        '    wine_nx_f1_crash_note("window-acquire: enter after launcher handoff");\n'
        '    int compositor = wine_nx_compositor_enabled();\n'
        '    wine_nx_f1_crash_stage("window-acquire: compositor",compositor,0,0);\n'
        '    NWindow *window = NULL;')
    source = exact(source, '    if (window) nwindowSetDimensions( window, WINE_NX_FB_W, WINE_NX_FB_H );',
        '    wine_nx_f1_crash_stage("window-acquire: set-dimensions-enter",0,(uintptr_t)window,0);\n'
        '    if (window) nwindowSetDimensions( window, WINE_NX_FB_W, WINE_NX_FB_H );\n'
        '    wine_nx_f1_crash_stage("window-acquire: set-dimensions-return",0,(uintptr_t)window,0);')
    source = exact(source, 'void wine_nx_runtime_process_exit(unsigned int code)\n{',
        'void wine_nx_runtime_process_exit(unsigned int code)\n{\n'
        '    uint64_t empty=0;\n'
        '    __atomic_compare_exchange_n(&f1_guest_exit_state,&empty,(1ULL<<32)|code,0,__ATOMIC_RELEASE,__ATOMIC_RELAXED);\n'
        '    wine_nx_f1_crash_stage("guest-process-exit",(int)code,0,0);\n'
        '    log_line("[F1-EXIT] code=%08x first_present=%d",code,__atomic_load_n(&fx_first_present,__ATOMIC_ACQUIRE));')
    source = source.replace('DX11 runtime. Startup monitor every 5s.',
                            'Crash capture: crash.log + fex-runtime.log.')
    return source


def patch_native_exception(source: str) -> str:
    source = exact(source,
        '            pes13_fex_fault_stage(1, ctx->pc.x, ctx->far.x, rec.ExceptionCode);',
        '            /* Native Mesa/SDK workers have no Wine TEB. VM fault handling\n'
        '             * and PE exception dispatch require one; otherwise the handler\n'
        '             * can fault again before reaching the persistent crash writer. */\n'
        '            if (!NtCurrentTeb()) goto f1_unhandled_native_fault;\n'
        '            pes13_fex_fault_stage(1, ctx->pc.x, ctx->far.x, rec.ExceptionCode);')
    source = exact(source,
        '            if (pes13_fex_dispatch_exception(&rec, &context)) pes13_fex_restore_context(&context);',
        '            if (NtCurrentTeb() && pes13_fex_dispatch_exception(&rec, &context))\n'
        '                pes13_fex_restore_context(&context);')
    source = exact(source,
        '    if (status)\n    {\n        unsigned int exception_class = esr >> 26;',
        'f1_unhandled_native_fault:\n'
        '    if (status)\n    {\n        unsigned int exception_class = esr >> 26;')
    return exact(source,
        '        /* Handled page faults are ordinary VM activity and must never hit the',
        '        extern void wine_nx_f1_crash_exception(const void *, unsigned);\n'
        '        wine_nx_f1_crash_exception(ctx,(unsigned)status);\n\n'
        '        /* Handled page faults are ordinary VM activity and must never hit the')


def patch_thread_detach(source: str) -> str:
    source = exact(source, 'static void thread_detach(void)\n{', DECL + '\nstatic void thread_detach(void)\n{')
    start = source.index('static void thread_detach(void)\n{')
    end = source.index('\n}', start) + 2
    body = source[start:end]
    # The actual failing call is unknown. Persist completed cleanup boundaries,
    # keeping the original order, ownership, and cleanup functions unchanged.
    for name, call in (
        ('windows', 'destroy_thread_windows();'),
        ('driver', 'user_driver->pThreadDetach();'),
        ('rawinput', 'free( thread_info->rawinput );'),
        ('imm', 'cleanup_imm_thread();'),
        ('queue', 'NtClose( thread_info->server_queue );'),
        ('idle', 'if (thread_info->idle_event) NtClose( thread_info->idle_event );'),
        ('session', 'free( thread_info->session_data );'),
        ('tracking', 'free( thread_info->mouse_tracking_info );')):
        body = exact(body, '    ' + call,
            '    wine_nx_f1_crash_stage("thread-detach-' + name + '-enter",0,GetCurrentThreadId(),0);\n'
            '    ' + call + '\n'
            '    wine_nx_f1_crash_stage("thread-detach-' + name + '-return",0,GetCurrentThreadId(),0);')
    return source[:start] + body + source[end:]


def wrap_vk(source: str, name: str, args: str, values: str) -> str:
    """Log enter/return (including early returns) without changing Vulkan results."""
    signature = 'static VkResult ' + name + '('
    start = source.index(signature)
    brace = source.index('{', start)
    declaration = source[start:brace]
    marked = replace_function(source, signature, 'F1_VK_FUNCTION_MARKER')
    end = start + len(source) - len(marked) + len('F1_VK_FUNCTION_MARKER')
    original = source[start:end].replace(name+'(', 'f1_impl_'+name+'(', 1)
    label = name.removeprefix('win32u_')
    wrapper = declaration + '''{
    static unsigned calls, errors;
    unsigned attempt=__atomic_add_fetch(&calls,1,__ATOMIC_RELAXED);
    if (attempt<=3) wine_nx_f1_crash_stage("''' + label + '''-enter",0,''' + values + ''');
    VkResult result=f1_impl_''' + name + '(' + args + ''');
    if (attempt<=3 || (result<0 && __atomic_add_fetch(&errors,1,__ATOMIC_RELAXED)<=8))
        wine_nx_f1_crash_stage("''' + label + '''-return",result,''' + values + ''');
    return result;
}'''
    return marked.replace('F1_VK_FUNCTION_MARKER',original+'\n\n'+wrapper)


def patch_surface(source: str) -> str:
    source = exact(source, 'WINE_DEFAULT_DEBUG_CHANNEL(vulkan);', 'WINE_DEFAULT_DEBUG_CHANNEL(vulkan);\n'+DECL)
    source = exact(source, '    if ((res = wine_nx_vkCreateViSurfaceNN(',
        '    wine_nx_f1_crash_stage("vkCreateViSurfaceNN-enter",0,(uintptr_t)info.window,(uintptr_t)hwnd);\n'
        '    if ((res = wine_nx_vkCreateViSurfaceNN(')
    return wrap_vk(source, 'nx_vulkan_surface_create', 'hwnd,raw,instance,handle,client',
                   '(uintptr_t)hwnd,raw')


def patch_vulkan(source: str) -> str:
    source = exact(source, 'WINE_DEFAULT_DEBUG_CHANNEL(vulkan);', 'WINE_DEFAULT_DEBUG_CHANNEL(vulkan);\n'+DECL)
    for name, args, values in (
        ('win32u_vkCreateSwapchainKHR','client_device,create_info,allocator,ret',
         '((unsigned long long)create_info->imageExtent.width<<32)|create_info->imageExtent.height,create_info->imageFormat'),
        ('win32u_vkAcquireNextImageKHR','client_device,client_swapchain,timeout,client_semaphore,client_fence,image_index',
         'timeout,(unsigned long long)client_swapchain'),
        ('win32u_vkAcquireNextImage2KHR','client_device,acquire_info,image_index',
         'acquire_info->timeout,(unsigned long long)acquire_info->swapchain'),
        ('win32u_vkQueuePresentKHR','client_queue,client_present_info',
         'client_present_info->swapchainCount,client_present_info->waitSemaphoreCount'),
        ('win32u_vkQueueSubmit','client_queue,count,submits,client_fence','count,(unsigned long long)client_fence'),
        ('win32u_vkQueueSubmit2','client_queue,count,submits,client_fence','count,(unsigned long long)client_fence'),
        ('win32u_vkQueueSubmit2KHR','client_queue,count,submits,client_fence','count,(unsigned long long)client_fence')):
        source = wrap_vk(source,name,args,values)
    return source
