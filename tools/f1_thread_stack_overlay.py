"""Drop Wine's unused second native stack in the isolated ARM64 Horizon build.

The Switch signal implementation runs syscalls, APCs and callbacks on the
libnx pthread stack.  Its separate kernel_stack allocation has no consumer.
Guest stacks and WoW64 CPU areas are retained without changing their sizes.
"""
from pathlib import Path
import re


OLD_STACK = """    /* kernel stack */
    if ((status = virtual_alloc_thread_stack( &stack, limit_4g, 0, kernel_stack_size, kernel_stack_size, FALSE )))
        return status;
    thread_data->kernel_stack = stack.DeallocationStack;
"""

NEW_STACK = """#if defined(__SWITCH__) && defined(__aarch64__)
    /* F1: Horizon syscalls, APCs, exceptions and callbacks use the active
     * libnx pthread stack.  The Switch signal implementation never switches
     * to Wine's kernel_stack.  Do not allocate a second, unused 1 MiB stack.
     * NULL also keeps virtual_free_teb from freeing the SDK-owned stack. */
    thread_data->kernel_stack = NULL;
#else
""" + OLD_STACK + "#endif\n"

OLD_COMMENT = """    /* kernel_stack lives in Wine-managed virtual memory; Horizon's
     * svcMapMemory only accepts libnx heap pages as thread stacks, so
     * threadCreate fails with it.  Let devkitA64 allocate the pthread
     * stack from the heap; signal_start_thread derives the syscall frame
     * from the running stack, so new threads never touch kernel_stack. */"""

NEW_COMMENT = """    /* Keep the full native pthread stack: Horizon's signal implementation
     * runs directly on it.  init_thread_stack omits only the unused Wine
     * kernel_stack allocation, not this SDK-owned stack or guest stacks. */"""


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def audit_source(source: Path) -> None:
    """Fail closed if the Switch signal/cleanup assumptions cease to hold."""
    unix = source / "dlls/ntdll/unix"
    signal = (unix / "signal_arm64.c").read_text()
    assert signal.count("#else /* __SWITCH__ */") == 1
    switch_signal = signal.split("#else /* __SWITCH__ */", 1)[0]
    code = _code(switch_signal)
    for identifier in ("kernel_stack", "get_syscall_frame", "is_inside_syscall"):
        assert not re.search(r"\b" + identifier + r"\b", code), identifier
    assert re.search(r"void signal_init_process\(void\)\s*\{\s*\}", code)
    assert "stack = virtual_setup_exception((void *)(context->Sp & ~15ull)" in code
    assert "result = f1_enter_apc(" in code
    assert "wine_nx_wow64_thread_start( entry, arg, suspend, teb )" in code
    virtual = (unix / "virtual.c").read_text()
    assert "if (thread_data->kernel_stack)\n    {\n        size = 0;\n        NtFreeVirtualMemory( GetCurrentProcess(), &thread_data->kernel_stack, &size, MEM_RELEASE );\n    }" in virtual
    assert "memset( ptr, 0, teb_size );" in virtual


def apply(source: Path) -> None:
    audit_source(source)
    path = source / "dlls/ntdll/unix/thread.c"
    text = path.read_text()
    if NEW_STACK in text:
        assert text.count(NEW_STACK) == 1 and NEW_COMMENT in text
        return
    assert text.count(OLD_STACK) == 1, "Wine kernel-stack allocation changed"
    assert text.count(OLD_COMMENT) == 1, "Switch pthread stack ownership changed"
    text = text.replace(OLD_STACK, NEW_STACK).replace(OLD_COMMENT, NEW_COMMENT)
    path.write_text(text)
