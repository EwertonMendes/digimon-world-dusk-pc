#!/usr/bin/env python3
"""Local-only Dusk ARM9/ARM7 native story smoke test. ROM is never uploaded."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time

SHA256 = "df9522e07be99c5622e0211d3a50132776784db3fb28f42fc7392f588e1ae8cb"

class Native:
    def __init__(self, port: int, proc: subprocess.Popen):
        for _ in range(300):
            if proc.poll() is not None:
                raise RuntimeError("native runner exited before server startup")
            try:
                self.socket = socket.create_connection(("127.0.0.1", port), timeout=120)
                self.data = b""
                return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("native server failed to start")

    def cmd(self, command: str, **args):
        self.socket.sendall((json.dumps(dict(cmd=command, **args)) + "\n").encode())
        while b"\n" not in self.data:
            chunk = self.socket.recv(1 << 19)
            if not chunk:
                raise RuntimeError("native runner disconnected")
            self.data += chunk
        line, self.data = self.data.split(b"\n", 1)
        response = json.loads(line)
        if "error" in response:
            raise RuntimeError(f'{command}: {response["error"]}')
        return response

    def frames(self, n: int):
        target = int(self.cmd("event_counts")["vblank9"]) + n
        for _ in range(100):
            response = self.cmd("run_to_event", event="vblank9", count=target,
                                max_rounds=5000000)
            if response.get("terminal") or response.get("stalled"):
                raise RuntimeError(f"native execution failed: {response}")
            if int(self.cmd("event_counts")["vblank9"]) >= target:
                return
        raise RuntimeError("no progress in requested native frames")

    def button(self, bit: int, settle: int = 80):
        self.cmd("keys", mask=4095 & ~(1 << bit))
        self.frames(5)
        self.cmd("keys", mask=4095)
        self.frames(settle)

    def tap(self, x: int, y: int, settle: int = 70):
        self.cmd("touch", x=x, y=y, down=True)
        self.frames(5)
        self.cmd("touch", x=x, y=y, down=False)
        self.frames(settle)

    def snap(self, directory: Path, label: str):
        result = {}
        for engine in ("A", "B"):
            data = self.cmd("framebuffer", engine=engine)
            if data["w"] != 256 or data["h"] != 192:
                raise RuntimeError("Unexpected graphics resolution")
            rgb = bytes.fromhex(data["rgb"])
            if len(set(rgb[::97])) < 4:
                raise RuntimeError("Potential unrendered screen")
            (directory / f"{label}-{engine}.ppm").write_bytes(
                b"P6\n256 192\n255\n" + rgb)
            result[engine] = hashlib.sha256(rgb).hexdigest()
        return result

def run(args):
    if hashlib.sha256(args.rom.read_bytes()).hexdigest() != SHA256:
        raise RuntimeError("Incorrect ROM: expected verified Digimon World Dusk USA")
    args.out.mkdir(parents=True, exist_ok=True)
    command = [str(args.runner.resolve()), str(args.bios_dir.resolve()),
               "--serve", "--port", str(args.port), "--rom",
               str(args.rom.resolve()), "--no-save", "--boot", "direct",
               "--generated-firmware", "--freebios", "--network", "off"]
    with (args.out / "native-runner.log").open("wb") as log:
        proc = subprocess.Popen(command, cwd=args.runner.resolve().parent,
                                stderr=log, stdout=log,
                                env={**os.environ, "NDS_DEEP_TRACE": "0"})
        try:
            game = Native(args.port, proc)
            game.cmd("reset")
            game.cmd("keys", mask=4095)
            game.frames(840)
            checkpoints = {"title": game.snap(args.out, "title")}
            game.button(3, settle=220)  # START
            game.button(0)              # New game
            game.button(0)              # Boy
            for _ in range(4):
                game.tap(20, 78)        # Player name input
            game.tap(213, 175)         # Done
            game.tap(70, 143, settle=160)  # Confirm player name
            checkpoints["starter-selection"] = game.snap(args.out, "starter-selection")
            game.button(0)             # Balance pack
            game.tap(125, 108, settle=180)  # Accept pack
            for _ in range(3):
                game.tap(213, 175, settle=70)   # Keep suggested Digimon nickname
                game.tap(70, 143, settle=120)   # Confirm
            for attempt in range(12):
                game.frames(60)
                try:
                    checkpoints["story-intro"] = game.snap(args.out, "story-intro")
                    break
                except RuntimeError as error:
                    if "Potential unrendered screen" not in str(error):
                        raise
            else:
                raise RuntimeError("No rendered intro frame after 720 vblanks")
            stats = game.cmd("event_counts")
            report = {
                "status": "real-guest-code-executed-to-story-intro",
                "romSHA256": SHA256,
                "frames": stats["vblank9"],
                "arm9Cycles": stats.get("cyc9"),
                "arm7Cycles": stats.get("cyc7"),
                "screensSHA256": checkpoints,
                "notes": "No saves tested; no complete playthrough or battles validated."
            }
            (args.out / "result.json").write_text(
                json.dumps(report, indent=2) + "\n")
            print(json.dumps(report, indent=2))
            game.socket.close()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runner", required=True, type=Path)
    ap.add_argument("--rom", required=True, type=Path)
    ap.add_argument("--bios-dir", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=Path(".private/story-smoke"))
    ap.add_argument("--port", type=int, default=19879)
    run(ap.parse_args())
