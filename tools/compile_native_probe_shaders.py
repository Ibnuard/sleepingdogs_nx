"""Compile original probe HLSL with the Windows system D3D compiler.

Shader source is project-owned; no game or proprietary LSFG input is used.
"""
from pathlib import Path
import ctypes
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[1]
VS = b'''float4 main(uint id : SV_VertexID) : SV_Position {
  float2 p = id == 0 ? float2(-1,-1) : id == 1 ? float2(-1,3) : float2(3,-1);
  return float4(p, 0, 1);
}'''
PS = b'float4 main() : SV_Target { return float4(0.25, 0.5, 0.75, 1.0); }'


def blob_call(blob, index, result):
    table = ctypes.cast(blob, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return ctypes.WINFUNCTYPE(result, ctypes.c_void_p)(table[index])(blob)


def main():
    if os.name != 'nt':
        raise RuntimeError('Shader compilation requires the Windows system D3D compiler')
    library = ctypes.WinDLL('d3dcompiler_47.dll')
    compile_shader = library.D3DCompile
    compile_shader.restype = ctypes.c_int32
    compile_shader.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p,
        ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p)]
    output = ROOT / 'src/native_dxvk/probe_shaders.h'
    lines = ['/* SPDX-License-Identifier: MIT; generated from original probe HLSL. */',
             '#pragma once', '#include <stdint.h>']
    hashes = {}
    for name, source, profile in [('probe_vs', VS, b'vs_5_0'), ('probe_ps', PS, b'ps_5_0')]:
        shader, error = ctypes.c_void_p(), ctypes.c_void_p()
        status = compile_shader(source, len(source), b'fextendo-native-probe', None,
                                None, b'main', profile, 1 << 15, 0,
                                ctypes.byref(shader), ctypes.byref(error))
        if status < 0:
            message = ctypes.string_at(blob_call(error, 3, ctypes.c_void_p)).decode() if error else hex(status)
            raise RuntimeError(message)
        data = ctypes.string_at(blob_call(shader, 3, ctypes.c_void_p), blob_call(shader, 4, ctypes.c_size_t))
        blob_call(shader, 2, ctypes.c_uint32)
        if error:
            blob_call(error, 2, ctypes.c_uint32)
        assert data[:4] == b'DXBC' and len(data) % 4 == 0
        words = [int.from_bytes(data[i:i+4], 'little') for i in range(0, len(data), 4)]
        lines += [f'static const uint32_t {name}[] = {{']
        lines += ['  ' + ', '.join(f'0x{word:08x}u' for word in words[i:i+8]) + ',' for i in range(0, len(words), 8)]
        lines += ['};']
        hashes[name] = {'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}
    output.write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(hashes, indent=2))


if __name__ == '__main__':
    main()
