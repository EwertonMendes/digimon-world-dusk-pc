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

    def test_microhitch_stays_visible_inside_normal_one_second_fps(self):
        samples = [
            {"kind":"perf","wall":"16:52:30","frames":100,"fps":59.82,
             "ms_per_frame":{"emu":4.8,"present":0.33},
             "frame_spikes":{"gap_gt_20ms":0,"emu_gt_12ms":0,
                             "emu_over_ds_budget":0,"max_gap_ms":17.0,
                             "max_emu_ms":8.2,"max_present_ms":0.5}},
            {"kind":"perf","wall":"16:52:31","frames":160,"fps":59.81,
             "ms_per_frame":{"emu":5.2,"present":0.34},
             "frame_spikes":{"gap_gt_20ms":1,"emu_gt_12ms":1,
                             "emu_over_ds_budget":1,"max_gap_ms":28.0,
                             "max_emu_ms":22.4,"max_present_ms":0.5,
                             "last_hitch_frame":153}},
        ]
        report = perf.summarize(samples)
        spikes=report["visual_frame_spikes"]
        self.assertEqual(spikes["gap_over_20ms"],1)
        self.assertEqual(spikes["emu_over_ds_budget"],1)
        self.assertEqual(spikes["peak_session_gap_ms"],28)
        self.assertEqual(spikes["peak_session_emu_ms"],22.4)
        self.assertEqual(spikes["worst_windows"][0]["last_hitch_frame"],153)
        self.assertEqual(report["below_95pct_target"],0)

    def test_legacy_v019_samples_no_frame_spike_fields_are_supported(self):
        report = perf.summarize([
            {"kind":"perf","fps":59.8,"ms_per_frame":{"emu":5.0}}])
        self.assertEqual(report["visual_frame_spikes"]["gap_over_20ms"],0)
        self.assertEqual(report["visual_frame_spikes"]["worst_windows"],[])

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            perf.summarize([{"kind":"perf","fps":"invalid"}])


if __name__=="__main__":
    unittest.main()
