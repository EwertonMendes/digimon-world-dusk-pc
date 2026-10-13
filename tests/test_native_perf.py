"""ROM-free test fixtures for native performance log aggregation."""
import importlib.util
from pathlib import Path
import unittest

module=Path(__file__).resolve().parents[1]/"tools"/"analyze_native_perf.py"
spec=importlib.util.spec_from_file_location("perf",module)
perf=importlib.util.module_from_spec(spec)
spec.loader.exec_module(perf)


class PerfTests(unittest.TestCase):
    def test_report_worst_windows_and_audio(self):
        events=[
            {"kind":"session"},
            {"kind":"perf","frames":100,"fps":59.8,
             "ms_per_frame":{"emu":9.2,"present":0.5},"governor":{"stage":0}},
            {"kind":"perf","frames":160,"fps":18.6,
             "ms_per_frame":{"emu":44.0,"present":1.0},
             "tier3_delta":{"arm9":{"instructions":90000}},
             "underruns_delta":3,"governor":{"stage":2}}
        ]
        report=perf.summarize(events[1:])
        self.assertEqual(report["sample_intervals"],2)
        self.assertEqual(report["worst_intervals"][0]["fps"],18.6)
        self.assertEqual(report["worst_intervals"][0]["tier3_arm9"],90000)
        self.assertEqual(report["below_95pct_target"],1)
        self.assertEqual(report["audio_underruns"],3)

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            perf.summarize([{"kind":"perf","fps":"invalid"}])


if __name__=="__main__":
    unittest.main()
