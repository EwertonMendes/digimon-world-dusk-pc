"""ROM-free safety checks for structural Spanish translation comparison."""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_spanish_dusk_reference import pack_entries, changed_entries


def make_pack(entries):
    offset = 4 + len(entries) * 8
    table = bytearray(struct.pack("<I", len(entries)))
    body = bytearray()
    for item in entries:
        table.extend(struct.pack("<II", offset, len(item) | 0x80000000))
        body.extend(item)
        offset += len(item)
    return bytes(table + body)


class SpanishReferenceAuditTests(unittest.TestCase):
    def test_unchanged_entries(self):
        src = make_pack([b"ABCD", b"EFGH"])
        self.assertEqual(changed_entries(src, src)["changed_ids"], [])

    def test_changed_index_not_file_offset(self):
        left = make_pack([b"1234", b"5678", b"abcdefgh"])
        right = make_pack([b"12345678", b"5678", b"abcdefgh"])
        self.assertEqual(changed_entries(left, right)["changed_ids"], [0])

    def test_entries_added(self):
        left = make_pack([b"1234"])
        right = make_pack([b"1234", b"5678"])
        self.assertEqual(changed_entries(left, right)["added_ids"], [1])

    def test_truncated_pack_rejected(self):
        with self.assertRaises(ValueError):
            pack_entries(b"notpack")

    def test_out_of_bounds_rejected(self):
        with self.assertRaises(ValueError):
            pack_entries(struct.pack("<III", 1, 5000, 8))

    def test_overlapping_index_rejected(self):
        data = bytearray(make_pack([b"abcdefgh", b"12345678"]))
        struct.pack_into("<I", data, 4 + 8, 4 + 16 + 2)
        with self.assertRaises(ValueError):
            pack_entries(bytes(data))

    def test_invalid_count_rejected(self):
        with self.assertRaises(ValueError):
            pack_entries(struct.pack("<I", 65535) + b"\0" * 100)


if __name__ == "__main__":
    unittest.main()
