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
import shutil
import subprocess
import tempfile

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
            "checkpoint": {"type", "name", "changed_since", "retry_frames"},
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
            retries = action.get("retry_frames", 0)
            if type(retries) is not int or not 0 <= retries <= 12:
                raise ValueError(f"invalid checkpoint retry_frames at {i}")
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
            for attempt in range(action.get("retry_frames", 0) + 1):
                try:
                    hashes = game.snap(out, action["name"])
                    break
                except RuntimeError as exc:
                    if "Potential unrendered screen" not in str(exc) or attempt >= action.get("retry_frames", 0):
                        raise
                    game.frames(60)
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


def cartridge_fixture(source: Path, out: Path) -> tuple[list[str], str]:
    """Clone an owner's *in-game* save into an isolated scenario run.

    Never open a live or canonical save for writing. The test runner may change
    only this private temporary copy. No save states, memory snapshots or
    save-slot formats are involved.
    """
    if not source.is_file() or source.stat().st_size != 65536:
        raise ValueError("Dusk USA in-game EEPROM must be an existing 65536-byte .sav file")
    sandbox = Path(tempfile.mkdtemp(prefix="cartridge-fixture-", dir=out))
    target = sandbox / "dusk.sav"
    config = sandbox / "dusk-cartridge.toml"
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    shutil.copyfile(source, target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != original:
        raise RuntimeError("Cartridge save fixture did not copy bit-for-bit")
    config.write_text('[cartridge]\\nsave_type = "eeprom"\\nsave_size = 65536\\n',
                      encoding="utf-8")
    return ["--save-path", str(target), "--config", str(config)], original


def run(args) -> None:
    if hashlib.sha256(args.rom.read_bytes()).hexdigest() != SHA256:
        raise RuntimeError("Expected the verified original Dusk USA ROM")
    scenario = validate_scenario(json.loads(args.scenario.read_text(encoding="utf-8")))
    out = args.out / scenario["id"]
    out.mkdir(parents=True, exist_ok=True)
    source_save = getattr(args, "save", None)
    save_flags, source_digest = (cartridge_fixture(source_save, out)
                                 if source_save is not None else (["--no-save"], None))
    command = [
        str(args.runner.resolve()), str(args.bios_dir.resolve()),
        "--serve", "--port", str(args.port), "--rom", str(args.rom.resolve()),
        *save_flags, "--boot", "direct", "--generated-firmware",
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
            if source_digest is not None:
                # The source path is read only; the runner gets only a clone.
                if hashlib.sha256(source_save.read_bytes()).hexdigest() != source_digest:
                    raise RuntimeError("Source save changed while testing; abort")
                report["save_fixture"] = "isolated-cartridge-copy; original untouched"
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
    parser.add_argument("--save", type=Path, help="owner .sav input; cloned to isolated test profile")
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path(".private/gameplay-regression"))
    parser.add_argument("--port", type=int, default=19880)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
