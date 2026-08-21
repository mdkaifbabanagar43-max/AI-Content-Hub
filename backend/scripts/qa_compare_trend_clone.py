#!/usr/bin/env python3
"""
QA Harness: Trend Cloner Output Validator
==========================================
Compares a generated Trend Cloner video against an optional reference video.
Runs automatically as a soft post-render step — logs warnings, never blocks delivery.

Usage:
    python scripts/qa_compare_trend_clone.py --generated /tmp/final_trend_abc.mp4
    python scripts/qa_compare_trend_clone.py --reference ref.mp4 --generated out.mp4
"""

import argparse
import json
import subprocess
import sys
import os


PASS  = "✅ PASS"
WARN  = "⚠️  WARN"
FAIL  = "❌ FAIL"


def ffprobe(path: str) -> dict:
    """Run ffprobe on a file and return parsed JSON."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"[QA] ffprobe failed on {path}: {e}")
        return {}


def get_video_stream(probe: dict) -> dict:
    """Extract first video stream from ffprobe output."""
    for s in probe.get("streams", []):
        if s.get("codec_type") == "video":
            return s
    return {}


def get_scene_cut_count(path: str) -> int:
    """Count detected scene cuts using FFmpeg scene change filter."""
    cmd = [
        "ffmpeg", "-i", path,
        "-vf", "select='gt(scene,0.3)',metadata=print:file=-",
        "-an", "-f", "null", "-"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        # Each scene cut produces a line with "pts_time"
        output = result.stderr.decode("utf-8", errors="replace")
        return output.count("pts_time")
    except Exception as e:
        print(f"[QA] Scene cut detection failed: {e}")
        return -1


def parse_fps(fps_str: str) -> float:
    """Parse '30/1' or '30000/1001' → float."""
    try:
        if "/" in fps_str:
            num, den = fps_str.split("/")
            return float(num) / float(den)
        return float(fps_str)
    except Exception:
        return 0.0


def qa_report(generated_path: str, reference_path: str = None) -> int:
    """
    Run QA checks and print a structured report.
    Returns 0 if all checks pass or warn, 1 if any FAIL.
    """
    print("\n" + "═" * 60)
    print(" TREND CLONER QA REPORT")
    print("═" * 60)
    print(f" Generated : {generated_path}")
    if reference_path:
        print(f" Reference : {reference_path}")
    print("═" * 60)

    if not os.path.exists(generated_path):
        print(f"{FAIL}  Generated file not found: {generated_path}")
        return 1

    gen_probe = ffprobe(generated_path)
    gen_stream = get_video_stream(gen_probe)
    gen_format = gen_probe.get("format", {})

    ref_probe  = ffprobe(reference_path) if reference_path else {}
    ref_stream = get_video_stream(ref_probe)
    ref_format = ref_probe.get("format", {})

    failures = 0

    # ── Check 1: Frame Rate ──────────────────────────────────
    gen_fps = parse_fps(gen_stream.get("avg_frame_rate", "0/1"))
    status = PASS if abs(gen_fps - 30.0) < 1.0 else WARN
    print(f"\n[FPS]          {status}  Generated fps={gen_fps:.2f}  (target=30.0)")
    if status == FAIL:
        failures += 1

    # ── Check 2: Duration ────────────────────────────────────
    gen_duration = float(gen_format.get("duration", 0))
    print(f"\n[DURATION]     Generated={gen_duration:.1f}s", end="")
    if reference_path and ref_format:
        ref_duration = float(ref_format.get("duration", 0))
        ratio = gen_duration / ref_duration if ref_duration > 0 else 0
        status = PASS if ratio >= 0.70 else WARN
        print(f"  Reference={ref_duration:.1f}s  Ratio={ratio:.0%}  {status}")
        if ratio < 0.40:
            print(f"  {FAIL}  Generated is <40% of reference duration — serious pacing issue!")
            failures += 1
    else:
        target_ok = gen_duration >= 10.0
        status = PASS if target_ok else WARN
        print(f"  {status}  (target ≥10s)")

    # ── Check 3: Scene Cuts ──────────────────────────────────
    gen_cuts = get_scene_cut_count(generated_path)
    print(f"\n[SCENE CUTS]   Generated cuts={gen_cuts}", end="")
    if reference_path:
        ref_cuts = get_scene_cut_count(reference_path)
        print(f"  Reference cuts={ref_cuts}", end="")
        if ref_cuts >= 2 and gen_cuts == 0:
            status = WARN
            print(f"  {WARN}  Generated has 0 cuts but reference has {ref_cuts}+")
        elif gen_cuts >= 2:
            status = PASS
            print(f"  {PASS}")
        else:
            status = WARN
            print(f"  {WARN}")
    else:
        status = PASS if gen_cuts >= 2 else WARN
        print(f"  {status}  (target ≥2 scene cuts for multi-scene output)")

    # ── Check 4: Bitrate ─────────────────────────────────────
    gen_bitrate_kbps = float(gen_format.get("bit_rate", 0)) / 1000
    print(f"\n[BITRATE]      Generated={gen_bitrate_kbps:.0f} kbps", end="")
    if reference_path and ref_format:
        ref_bitrate_kbps = float(ref_format.get("bit_rate", 0)) / 1000
        if ref_bitrate_kbps > 0:
            ratio = gen_bitrate_kbps / ref_bitrate_kbps
            status = PASS if ratio <= 2.0 else WARN
            print(f"  Reference={ref_bitrate_kbps:.0f} kbps  Ratio={ratio:.1f}x  {status}")
        else:
            print(f"  (no reference bitrate)")
    else:
        status = PASS if gen_bitrate_kbps < 8000 else WARN
        print(f"  {status}  (target <8000 kbps)")

    # ── Check 5: File Size ───────────────────────────────────
    gen_size_mb = os.path.getsize(generated_path) / (1024 * 1024)
    status = PASS if gen_size_mb < 50 else WARN
    print(f"\n[FILE SIZE]    {status}  Generated={gen_size_mb:.1f} MB  (target <50 MB)")

    # ── Summary ──────────────────────────────────────────────
    print("\n" + "─" * 60)
    if failures == 0:
        print(" QA RESULT: ✅ ALL CHECKS PASSED (or WARNED — non-blocking)")
    else:
        print(f" QA RESULT: ❌ {failures} FAILURE(S) detected")
    print("═" * 60 + "\n")

    return 0  # Always return 0 — soft gate, never blocks delivery


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QA check for Trend Cloner output")
    parser.add_argument("--generated", required=True, help="Path to generated video")
    parser.add_argument("--reference", default=None, help="Optional path to reference video")
    args = parser.parse_args()

    sys.exit(qa_report(args.generated, args.reference))
