"""Native local named pipes, using the existing Horizon object/IOCP registry."""
import re
from pathlib import Path
from f1_overlay import exact
from port_common import ROOT


def function_start(text, name, code):
    pattern = r'(\b' + re.escape(name) + r'\(\s[^;{}]*?\)\s*\{\n)'
    text, count = re.subn(pattern, lambda m: m[1] + code, text)
    if count != 1:
        raise RuntimeError(f'Expected one function {name}, found {count}')
    return text


def apply(source):
    unix = Path(source) / 'dlls/ntdll/unix'
    for name in ('sd_named_pipe.h', 'sd_named_pipe.inc'):
        (unix / name).write_bytes((ROOT / 'src' / name).read_bytes())
    p = unix / 'horizon.c'
    s = p.read_text()
    s = exact(s, '    int file_fd;\n', '    int file_fd;\n    struct sd_pipe_endpoint *sd_pipe;\n')
    s = exact(s, 'static void horizon_server_free_object( struct horizon_server_object *object )',
              'static void sd_pipe_close_locked(struct horizon_server_object *object);\n'
              'static void sd_pipe_free_locked(struct horizon_server_object *object);\n\n'
              'static void horizon_server_free_object( struct horizon_server_object *object )')
    s = function_start(s, 'horizon_server_free_object', '    if (object && object->sd_pipe) sd_pipe_free_locked(object);\n')
    s = exact(s, '        object = entry->object;\n        horizon_server_unlink_handle_locked( entry );\n',
              '        object = entry->object;\n        horizon_server_unlink_handle_locked( entry );\n'
              '        if (object && object->sd_pipe && !horizon_server_object_has_handles_locked(object))\n'
              '            sd_pipe_close_locked(object);\n')
    s = function_start(s, 'horizon_server_object_is_signaled',
                       '    if (object->sd_pipe) return object->signaled;\n')
    s += '\n#ifdef __SWITCH__\n#include "sd_named_pipe.inc"\n#endif\n'
    p.write_text(s)
    p = unix / 'file.c'
    s = p.read_text()
    s = exact(s, '#include "unix_private.h"', '#include "unix_private.h"\n#ifdef __SWITCH__\n#include "sd_named_pipe.h"\n#endif')
    def hook(name, expression):
        nonlocal s
        s = function_start(s, name, '#ifdef __SWITCH__\n    { NTSTATUS sd_status;\n'
                           '      if (' + expression + ') return sd_status; }\n#endif\n')
    hook('NtCreateFile', 'sd_pipe_open(handle, access, attr, io, disposition, options, &sd_status)')
    s = function_start(s, 'NtCreateNamedPipeFile',
                       '#ifdef __SWITCH__\n    return sd_pipe_create(handle, access, attr, io, sharing, dispo, options,\n'
                       '                          pipe_type, read_mode, completion_mode, max_inst, inbound_quota, outbound_quota);\n#endif\n')
    hook('f1_original_NtReadFile', 'sd_pipe_read_write(handle, event, apc, apc_user, io, buffer, length, FALSE, &sd_status)')
    hook('NtWriteFile', 'sd_pipe_read_write(handle, event, apc, apc_user, io, (void *)buffer, length, TRUE, &sd_status)')
    hook('NtFsControlFile', 'sd_pipe_control(handle, event, apc, apc_context, io, code, out_buffer, out_size, &sd_status)')
    hook('NtQueryInformationFile', 'sd_pipe_query(handle, io, ptr, len, class, &sd_status)')
    hook('NtSetInformationFile', 'sd_pipe_set(handle, io, ptr, len, class, &sd_status)')
    hook('NtQueryVolumeInformationFile', 'sd_pipe_volume(handle, io, buffer, length, info_class, &sd_status)')
    hook('cancel_io', 'sd_pipe_cancel(handle, io, io_status, only_thread, &sd_status)')
    p.write_text(s)
    p = Path(source) / 'wine-nx-probe/source/runtime.c'
    s = p.read_text()
    marker = 'log_line("[SD-FEX] launch_mode=%s",fx_ui_view.debug?"debug":"gui");'
    s = exact(s, marker, marker + '\n                        log_line("[SD-PIPE] local named pipes v1; event/IOCP completion; per-request WoW64 IOSB");')
    p.write_text(s)
