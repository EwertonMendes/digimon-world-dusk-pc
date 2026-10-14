"""ROM-free scenario validation and execution-contract tests."""
import importlib.util
from pathlib import Path
import sys
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
from dusk_gameplay_scenarios import validate_scenario, execute_actions


class FakeGame:
    def __init__(self):
        self.vblanks = 840
        self.events = []
        self.picture = 0

    def frames(self, count):
        self.events.append(("frames", count))
        self.vblanks += count

    def button(self, bit, settle=60):
        self.events.append(("button", bit, settle))
        self.vblanks += 5 + settle

    def tap(self, x, y, settle=60):
        self.events.append(("touch", x, y, settle))
        self.vblanks += 5 + settle

    def snap(self, path, name):
        self.picture += 1
        return {"A": "%064d" % self.picture, "B": "%064d" % self.picture}

    def cmd(self, name):
        if name != "event_counts":
            raise AssertionError(name)
        return {"vblank9": self.vblanks, "cyc9": self.vblanks * 100,
                "cyc7": self.vblanks * 50}


class ScenarioValidationTests(unittest.TestCase):
    def scenario(self, actions):
        return {"id": "battle-1", "actions": actions}

    def test_valid_original_input_and_differential_checkpoint(self):
        v = validate_scenario(self.scenario([
            {"type":"frames","count":10},
            {"type":"button","name":"a","settle":70},
            {"type":"touch","x":200,"y":120,"settle":80},
            {"type":"checkpoint","name":"before"},
            {"type":"button","name":"b"},
            {"type":"checkpoint","name":"after","changed_since":"before"},
        ]))
        r = execute_actions(FakeGame(), v, Path("."))
        self.assertEqual(r["status"], "passed-scripted-original-game-inputs")
        self.assertEqual(len(r["checkpoints"]), 2)
        self.assertGreater(r["checkpoints"][1]["vblanks"], r["checkpoints"][0]["vblanks"])

    def test_rejects_unscripted_memory_or_save_state_actions(self):
        for name in ("savestate", "save-state", "memory-write", "patch-rom", "reset"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    validate_scenario(self.scenario([{"type":name,"name":"x"}]))

    def test_rejects_out_of_bounds_or_non_integer_touch(self):
        for x,y in ((256,0),(1,-1),(3.5,10),(0,192)):
            with self.subTest(x=x,y=y), self.assertRaises(ValueError):
                validate_scenario(self.scenario([
                    {"type":"touch","x":x,"y":y},
                    {"type":"checkpoint","name":"ok"},
                ]))

    def test_rejects_duplicate_checkpoint_and_forward_reference(self):
        for actions in (
            [{"type":"checkpoint","name":"a"},{"type":"checkpoint","name":"a"}],
            [{"type":"checkpoint","name":"a","changed_since":"b"}],
        ):
            with self.assertRaises(ValueError):
                validate_scenario(self.scenario(actions))

    def test_rejects_no_proof_of_progress(self):
        with self.assertRaises(ValueError):
            validate_scenario(self.scenario([{"type":"frames","count":30}]))

    def test_rejects_guest_frame_overrun(self):
        for count in (0,-1,30001,True):
            with self.subTest(count=count), self.assertRaises(ValueError):
                validate_scenario(self.scenario([
                    {"type":"frames","count":count},
                    {"type":"checkpoint","name":"ok"},
                ]))

if __name__ == "__main__":
    unittest.main()
