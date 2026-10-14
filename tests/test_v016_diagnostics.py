import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from analyze_v016_sessions import summarize


class SafeDiagnosticsTest(unittest.TestCase):
    def test_safe_summary_does_not_leak_host_paths_or_game_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            perf = root / "performance.jsonl"
            coverage = root / "coverage.json"
            host = root / "host.ndshp"
            cartridge = "a" * 40
            perf.write_text("\n".join([
                json.dumps({"kind": "session", "rom_sha1": cartridge,
                            "host": {"username": "DO_NOT_EXPORT"}}),
                json.dumps({"kind": "perf", "fps": 59.8, "ms_per_frame": {"emu": 4.5, "present": 1.1},
                            "underruns_delta": 2, "tier3_delta": {"arm9": {"instructions": 12}}}),
                json.dumps({"kind": "perf", "fps": 45.0, "ms_per_frame": {"emu": 5, "present": 1},
                            "underruns_delta": 0, "tier3_delta": {"arm9": {"instructions": 2}}}),
            ]) + "\n", encoding="utf-8")
            coverage.write_text(json.dumps({
                "schema": 4, "kind": "ndsrecomp-tier3-coverage", "rom_sha1": cartridge,
                "pages": {"entries": [
                    {"cpu": 9, "addr": "0x02200000", "sha1": "b" * 40, "data": "DO_NOT_EXPORT"},
                    {"cpu": 9, "addr": "0x02200000", "sha1": "c" * 40, "data": "DO_NOT_EXPORT"},
                ], "dropped": 0},
                "static_coverage": {"tier3_entries9": 23},
            }), encoding="utf-8")
            host.write_bytes((json.dumps({
                "format": "ndsrecomp-hostprof", "version": 1,
                "hist_total": 5, "ring_evicted": 2, "roles": {"emu": 3, "render": 2},
                "modules": [{"path": "C:\\\\PRIVATE_PATH"}],
            }) + "\n").encode() + b"private-host-stack-binary")
            result = summarize([perf], [coverage], [host])
            self.assertEqual(result["totals"]["audio_underruns"], 2)
            self.assertEqual(result["totals"]["pages_with_multiple_generations"], 1)
            self.assertEqual(result["performance_sessions"][0]["tier3_arm9_instructions"], 14)
            clean = json.dumps(result)
            self.assertNotIn("DO_NOT_EXPORT", clean)
            self.assertNotIn("PRIVATE_PATH", clean)
            self.assertEqual(result["hostprof_sessions"][0]["ring_evicted"], 2)

    def test_rejects_mismatched_cartridge(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            a, b, c = p / "a.jsonl", p / "b.json", p / "c.ndshp"
            a.write_text('{"kind":"session","rom_sha1":"' + "a" * 40 + '"}\n'
                         '{"kind":"perf","fps":59.8}\n', encoding="utf-8")
            b.write_text(json.dumps({"schema": 4, "kind": "ndsrecomp-tier3-coverage",
                                     "rom_sha1": "b" * 40, "pages": {"entries": []}}), encoding="utf-8")
            c.write_bytes(b'{"format":"ndsrecomp-hostprof","version":1}\n')
            with self.assertRaises(ValueError):
                summarize([a], [b], [c])


if __name__ == "__main__":
    unittest.main()
