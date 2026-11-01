"""Render a terminal REPLAY video of the captured demo transcript.

Source: evidence/logs/demo_transcript.txt.

This is a replay of real, previously captured output, typed out with captions: not a live screen
recording and not narrated. Output: docs/img/demo_replay.mp4 (needs ffmpeg and Pillow).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

import matplotlib
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H, FPS = 1280, 720, 15
FONT = ImageFont.truetype(
    str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSansMono.ttf"), 17
)
BOLD = ImageFont.truetype(
    str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSansMono-Bold.ttf"), 17
)
CAPTION_FONT = ImageFont.truetype(
    str(Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"), 22
)
BG, FG, CMD, DIM, CAP_BG = (
    (16, 18, 24),
    (214, 222, 235),
    (126, 231, 135),
    (139, 148, 158),
    (31, 41, 55),
)
CAPTIONS = {
    "$ no key": "No API key: the gateway fails closed (HTTP 401).",
    "$ with key": "Messages the cheap model is confident about are answered locally (path: cheap).",
    "$ idempotency": "Same Idempotency-Key twice: the second answer is a replay, no second teacher call.",
    "$ oversize": "Oversized input is rejected (HTTP 413).",
    "$ status": "Status after 60 requests: audits, teacher calls, spend, no drift alarm.",
    "$ metrics": "Prometheus metrics: what the Grafana dashboard reads.",
}


def caption_for(cmd: str) -> str:
    return next((v for k, v in CAPTIONS.items() if cmd.startswith(k)), "")


def card(draw: ImageDraw.ImageDraw, lines: list[str]) -> None:
    y = 200
    for i, line in enumerate(lines):
        draw.text((90, y), line, font=BOLD if i == 0 else FONT, fill=FG if i == 0 else DIM)
        y += 40


def frame(
    shown: list[tuple[str, bool]], caption: str, title: list[str] | None = None
) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    if title:
        card(d, title)
        return img
    visible = shown[-27:]
    for i, (text, is_cmd) in enumerate(visible):
        d.text((20, 14 + i * 24), text, font=BOLD if is_cmd else FONT, fill=CMD if is_cmd else FG)
    if caption:
        d.rectangle((0, H - 70, W, H), fill=CAP_BG)
        d.text((24, H - 52), caption, font=CAPTION_FONT, fill=(255, 255, 255))
    return img


def main() -> None:
    lines = (ROOT / "evidence/logs/demo_transcript.txt").read_text(encoding="utf-8").splitlines()
    out = ROOT / "docs/img/demo_replay.mp4"
    tmp = Path(tempfile.mkdtemp(prefix="demo-frames-"))
    n = 0

    def save(img: Image.Image, repeat: int = 1) -> None:
        nonlocal n
        for _ in range(repeat):
            img.save(tmp / f"f{n:05d}.png")
            n += 1

    save(
        frame(
            [],
            "",
            [
                "Cascade gateway: end-to-end demo (REPLAY)",
                "Real student + real encoder; the teacher is SIMULATED (300 ms).",
                "Replay of captured output (scripts/demo.sh, evidence/logs/demo_transcript.txt).",
                "Not a live screen recording and not narrated.",
            ],
        ),
        FPS * 4,
    )
    shown: list[tuple[str, bool]] = []
    caption = ""
    for line in lines:
        is_cmd = line.startswith("$ ")
        wrapped = textwrap.wrap(line, width=118, subsequent_indent="  ") or [""]
        if is_cmd:
            caption = caption_for(line)
            for k in range(0, len(line) + 1, 3):  # typewriter
                save(frame([*shown, (line[:k] + "_", True)], caption))
            shown.append((line, True))
            save(frame(shown, caption), FPS // 2)
        else:
            for w in wrapped:
                shown.append((w, False))
            save(frame(shown, caption), FPS)
    save(frame(shown, caption), FPS * 2)
    save(
        frame(
            [],
            "",
            [
                "What this showed",
                "Auth fails closed, scopes enforced, idempotent replays, input limits,",
                "cheap-path answers with confidences, audits, status and metrics.",
                "Results, limits and scorecard: README.md, SCORECARD.md, docs/.",
            ],
        ),
        FPS * 4,
    )
    subprocess.run(  # noqa: S603
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-framerate",
            str(FPS),
            "-i",
            str(tmp / "f%05d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "28",
            str(out),
        ],
        check=True,
    )
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB, {n / FPS:.0f} s)")


if __name__ == "__main__":
    main()
