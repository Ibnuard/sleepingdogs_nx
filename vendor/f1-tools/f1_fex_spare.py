"""Disable only the unused eager JIT spare in the pinned F1 ARM64 FEX module.

The approved module was built with a different host toolchain. Preserve every
address and translated-code implementation by replacing the optional void
PES13FexPrimeCodeCache entry with ARM64 RET. No live cache is freed or resized.
Normal TryAllocateCode/growth/fallback are byte-identical. This is a reproducible
patch to our MIT-licensed FEX adapter, never a change to the game executable.
"""
from pathlib import Path
import hashlib, json, struct
import pefile

BASE_SHA256 = '17dcf3e78371a717a9c41da5bffa4d6a5755d6479afa0a8ade12abcc7639ad23'
ENTRY = 'PES13FexPrimeCodeCache'
RET = bytes.fromhex('c0035fd6')


def symbols(data, pe):
    start, count = pe.FILE_HEADER.PointerToSymbolTable, pe.FILE_HEADER.NumberOfSymbols
    strings = start + 18 * count
    result = {}
    i = 0
    while i < count:
        name, value, section, _, _, aux = struct.unpack_from('<8sIhHBB', data, start + 18*i)
        if name[:4] == bytes(4):
            pos = strings + int.from_bytes(name[4:], 'little')
            name = data[pos:data.index(b'\0', pos)]
        else:
            name = name.rstrip(b'\0')
        if section > 0:
            result[name.decode()] = pe.sections[section-1].VirtualAddress + value
        i += 1 + aux
    return result


def patch(data):
    assert hashlib.sha256(data).hexdigest() == BASE_SHA256, 'Unreviewed FEX module'
    pe = pefile.PE(data=data)
    assert pe.FILE_HEADER.Machine == 0xaa64 and pe.OPTIONAL_HEADER.Magic == 0x20b
    rva = symbols(data, pe)[ENTRY]
    section = pe.get_section_by_rva(rva)
    assert section and section.Characteristics & 0x20000000 and rva % 4 == 0
    offset = pe.get_offset_from_rva(rva)
    result = bytearray(data)
    assert result[offset:offset+4] != RET
    original_entry = bytes(result[offset:offset+32])
    result[offset:offset+4] = RET
    # Keep the optional PE checksum correct without touching any other header.
    checksum_offset = pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')
    changed = pefile.PE(data=result)
    struct.pack_into('<I', result, checksum_offset, changed.generate_checksum())
    allowed = set(range(offset, offset+4)) | set(range(checksum_offset, checksum_offset+4))
    diff = [i for i, (a,b) in enumerate(zip(data,result)) if a != b]
    assert set(diff) <= allowed and len(result) == len(data)
    report = {'method': 'pinned ARM64 void function entry RET; PE checksum refreshed',
        'base_sha256': BASE_SHA256, 'sha256': hashlib.sha256(result).hexdigest(),
        'entry': ENTRY, 'rva': rva, 'file_offset': offset,
        'original_entry_32_bytes': original_entry.hex(), 'replacement_instruction': RET.hex(),
        'changed_offsets': diff, 'checksum_offset': checksum_offset,
        'behavior': 'No eager spare; initial 128 MiB cache and normal growth/fallback unchanged',
        'hardware_tested': False}
    return bytes(result), report


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();data,report=patch(a.input.read_bytes())
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_bytes(data)
    a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
