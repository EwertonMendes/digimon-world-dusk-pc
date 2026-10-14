#!/usr/bin/env python3
"""ROM-private, deterministic native Dusk gameplay regression runner.

Only scripted original DS button/touch inputs and framebuffer/cycle checks.
No savestates, injected guest RAM, patching or replacement game logic.
Run with a locally built real-game NDSRecomp runner; never upload ROM/screens.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from test_dusk_native_story import Native, SHA256

BUTTONS = {"a": 0, "b": 1, "select": 2, "start": 3,
           "right": 4, "left": 5, "up": 6, "down": 7,
           "r": 8, "l": 9, "x": 10, "y": 11}
ALLOWED = {"frames", "button", "touch", "checkpoint"}
IDENT = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def validate_scenario(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != {"id", "actions"}:
        raise ValueError("scenario must contain only 'id' and 'actions'")
    if not isinstance(value["id"], str) or not IDENT.fullmatch(value["id"]):
        raise ValueError("invalid scenario id")
    actions = value["actions"]
    if not isinstance(actions, list) or not 1 <= len(actions) <= 1000:
        raise ValueError("scenario actions: expected between 1 and 1000")
    checkpoints = set()
    for i, action in enumerate(actions):
        if not isinstance(action, dict) or action.get("type") not in ALLOWED:
            raise ValueError(f"unknown action at {i}")
        kind = action["type"]
        expected = {
            "frames": {"type", "count"},
            "button": {"type", "name", "settle"},
            "touch": {"type", "x", "y", "settle"},
            "checkpoint": {"type", "name", "changed_since"},
        }[kind]
        if set(action) - expected or "type" not in action:
            raise ValueError(f"unexpected action field at {i}")
        if kind == "frames":
            if type(action.get("count")) is not int or not 1 <= action["count"] <= 30000:
                raise ValueError(f"invalid frame count at {i}")
        if kind == "button":
            if action.get("name") not in BUTTONS:
                raise ValueError(f"invalid button name at {i}")
        if kind == "touch":
            x, y = action.get("x"), action.get("y")
            if type(x) is not int or type(y) is not int or not (0 <= x < 256 and 0 <= y < 192):
                raise ValueError(f"invalid touch coordinates at {i}")
        if kind in ("button", "touch"):
            settle = action.get("settle", 60)
            if type(settle) is not int or not 0 <= settle <= 30000:
                raise ValueError(f"invalid settling frames at {i}")
        if kind == "checkpoint":
            name = action.get("name")
            if not isinstance(name, str) or not IDENT.fullmatch(name) or name in checkpoints:
                raise ValueError(f"invalid or duplicate checkpoint at {i}")
            earlier = action.get("changed_since")
            if earlier is not None and earlier not in checkpoints:
                raise ValueError(f"checkpoint {name}: changed_since needs a prior checkpoint")
            checkpoints.add(name)
    if not checkpoints:
        raise ValueError("scenario must contain at least one checkpoint")
    return value


def execute_actions(game: Native, scenario: dict, out: Path) -> dict:
    snapshots: dict[str, dict] = {}
    checkpoints: list[dict] = []
    initial = game.cmd("event_counts")
    previous = int(initial["vblank9"])
    for action in scenario["actions"]:
        kind = action["type"]
        if kind == "frames":
            game.frames(action["count"])
        elif kind == "button":
            game.button(BUTTONS[action["name"]], action.get("settle", 60))
        elif kind == "touch":
            game.tap(action["x"], action["y"], action.get("settle", 60))
        else:
            hashes = game.snap(out, action["name"])
            baseline = action.get("changed_since")
            if baseline and hashes == snapshots[baseline]:
                raise RuntimeError(f"checkpoint {action['name']} unexpectedly equals {baseline}")
            snapshots[action["name"]] = hashes
            counters = game.cmd("event_counts")
            vblank = int(counters["vblank9"])
            if vblank < previous:
                raise RuntimeError("guest vblank counter regressed")
            previous = vblank
            checkpoints.append({
                "name": action["name"], "vblanks": vblank,
                "arm9Cycles": counters.get("cyc9"), "arm7Cycles": counters.get("cyc7"),
                "frameSHA256": hashes,
            })
    return {
        "scenario": scenario["id"],
        "status": "passed-scripted-original-game-inputs",
        "checkpoints": checkpoints,
        "coverage": "only the explicitly scripted sequence; no claim of complete story or battle correctness",
    }


def run(args) -> None:
    if hashlib.sha256(args.rom.read_bytes()).hexdigest() != SHA256:
        raise RuntimeError("Expected the verified original Dusk USA ROM")
    scenario = validate_scenario(json.loads(args.scenario.read_text(encoding="utf-8")))
    out = args.out / scenario["id"]
    out.mkdir(parents=True, exist_ok=True)
    command = [
        str(args.runner.resolve()), str(args.bios_dir.resolve()),
        "--serve", "--port", str(args.port), "--rom", str(args.rom.resolve()),
        "--no-save", "--boot", "direct", "--generated-firmware",
        "--freebios", "--network", "off",
    ]
    with (out / "native-runner.log").open("wb") as log:
        proc = subprocess.Popen(command, cwd=args.runner.resolve().parent,
                                stdout=log, stderr=log,
                                env={**os.environ, "NDS_DEEP_TRACE": "0"})
        try:
            game = Native(args.port, proc)
            game.cmd("reset")
            game.cmd("keys", mask=4095)
            game.frames(840)
            report = execute_actions(game, scenario, out)
            (out / "result.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
            print(json.dumps(report, indent=2))
            game.socket.close()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--bios-dir", type=Path, required=True)
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path(".private/gameplay-regression"))
    parser.add_argument("--port", type=int, default=19880)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
