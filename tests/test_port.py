"""Executable layout checks protect Wine's fixed-address reservation."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from port_common import DEFAULT_GAME, GAME_EXE, pe_info


class ExecutableLayout(unittest.TestCase):
    def setUp(self):
        self.data = bytearray((DEFAULT_GAME / GAME_EXE).read_bytes())
        self.nt = struct.unpack_from('<I', self.data, 0x3c)[0]

    def check_rejected(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'HKShip.exe'
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                pe_info(path)

    def test_fixed_x86_image(self):
        info = pe_info(DEFAULT_GAME / GAME_EXE)
        self.assertEqual(info['image_base'], 0x400000)
        self.assertEqual(info['image_size'], 0x10e5000)
        self.assertEqual(info['image_end'], 0x14e5000)
        self.assertFalse(info['relocations_available'])
        self.assertFalse(info['large_address_aware'])

    def test_refuse_x64_edition(self):
        struct.pack_into('<H', self.data, self.nt + 4, 0x8664)
        self.check_rejected(self.data)

    def test_refuse_truncated_or_bad_headers(self):
        self.check_rejected(b'MZ')
        struct.pack_into('<I', self.data, 0x3c, 0xfffffffc)
        self.check_rejected(self.data)

    def test_refuse_incompatible_image_base(self):
        struct.pack_into('<I', self.data, self.nt + 24 + 28, 0x14000000)
        self.check_rejected(self.data)

    def test_refuse_unaligned_size(self):
        struct.pack_into('<I', self.data, self.nt + 24 + 56, 0x10e5001)
        self.check_rejected(self.data)


if __name__ == '__main__':
    unittest.main()
