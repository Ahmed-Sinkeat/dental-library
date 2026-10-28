#!/usr/bin/env python3
"""Shrink the Telegram export for R2: speech audio -> Opus 32k mono, video -> AV1 + Opus.
Originals in channel/ are never touched; output goes to channel_r2/. Re-runnable (skips done files).
Usage: python3 compress.py            # convert + rewrite links + verify
       python3 compress.py --verify   # verify only
"""
import html, json, os, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SRC = Path(__file__).parent / "channel"
OUT = Path(__file__).parent / "channel_r2"
AUDIO = {".m4a", ".mp3", ".aac", ".3gpp", ".wav"}
VIDEO = {".mp4", ".mov", ".mkv"}
MAP = OUT.parent / "channel_r2.renames.json"  # old rel path -> new rel path


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                        "-of", "json", str(p)], capture_output=True, text=True)
    if r.returncode:
        return None, set()
    j = json.loads(r.stdout)
    return float(j.get("format", {}).get("duration", 0) or 0), {s["codec_type"] for s in j.get("streams", [])}


def convert(src):
    rel = src.relative_to(SRC)
    ext = src.suffix.lower()
    dur, kinds = probe(src) if ext in AUDIO | VIDEO else (None, set())
    if "video" in kinds and ext in VIDEO:
        dst = OUT / rel.with_suffix(".mp4")
        args = ["-map", "0:v:0", "-map", "0:a?", "-c:v", "libsvtav1", "-preset", "8", "-crf", "35",
                "-g", "300", "-pix_fmt", "yuv420p", "-c:a", "libopus", "-b:a", "48k", "-movflags", "+faststart"]
    elif "audio" in kinds and "video" not in kinds:
        dst = OUT / rel.with_suffix(".opus")
        args = ["-vn", "-ac", "1", "-c:a", "libopus", "-b:a", "32k", "-application", "voip"]
    else:
        dst = OUT / rel
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        return rel, rel, "copy"

    if dst.exists():
        return rel, dst.relative_to(OUT), "done"
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(".tmp." + dst.name)
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
                        *args, "-map_metadata", "0", "-f", "mp4" if dst.suffix == ".mp4" else "ogg", str(tmp)],
                       capture_output=True, text=True)
    new_dur, _ = probe(tmp) if tmp.exists() else (None, set())
    # Safety: a truncated or bigger output means keep the original as-is.
    ok = r.returncode == 0 and new_dur and abs(new_dur - dur) <= max(1.5, dur * 0.01)
    if ok and tmp.stat().st_size < src.stat().st_size:
        tmp.rename(dst)
        return rel, dst.relative_to(OUT), "conv"
    tmp.unlink(missing_ok=True)
    print(f"KEEP ORIGINAL {rel}: rc={r.returncode} dur {dur}->{new_dur} {r.stderr[-200:]}", flush=True)
    shutil.copy2(src, OUT / rel)
    return rel, rel, "kept"


def rewrite_links(renames):
    for name, enc in (("result.json", lambda s: json.dumps(s, ensure_ascii=False)),
                      ("messages.html", lambda s: '"' + html.escape(s, quote=True) + '"')):
        p = OUT / name
        text = (SRC / name).read_text(encoding="utf-8")
        for old, new in renames.items():
            if old != new:
                text = text.replace(enc(old), enc(new))
        p.write_text(text, encoding="utf-8")


def verify():
    src_files = sorted(p for p in SRC.rglob("*") if p.is_file())
    renames = json.loads(MAP.read_text())
    bad = [r for r in renames.values() if not (OUT / r).is_file()]
    assert not bad, f"missing outputs: {bad[:5]}"
    assert len(renames) == len(src_files), f"{len(renames)} mapped vs {len(src_files)} source files"
    out_files = [p for p in OUT.rglob("*") if p.is_file() and not p.name.startswith(".tmp.")]
    assert len(out_files) == len(src_files), f"{len(out_files)} out vs {len(src_files)} src"
    json.loads((OUT / "result.json").read_text(encoding="utf-8"))  # still valid JSON
    # every media link in the export must point at a file that exists
    for name in ("result.json", "messages.html"):
        text = (OUT / name).read_text(encoding="utf-8")
        for old, new in renames.items():
            if old != new:
                assert f'"{html.escape(old)}"' not in text and json.dumps(old, ensure_ascii=False) not in text, \
                    f"stale link to {old} in {name}"
    s = sum(p.stat().st_size for p in src_files) / 2**30
    o = sum(p.stat().st_size for p in out_files) / 2**30
    print(f"VERIFY OK: {len(out_files)} files, {s:.2f} GiB -> {o:.2f} GiB ({100 * o / s:.0f}%)")


if __name__ == "__main__":
    if "--verify" not in sys.argv:
        files = sorted(p for p in SRC.rglob("*") if p.is_file())
        is_video = lambda p: p.suffix.lower() in VIDEO
        results = []
        with ThreadPoolExecutor(8) as ex:  # audio + copies in parallel
            results += ex.map(convert, [p for p in files if not is_video(p)])
        for i, p in enumerate(v := [p for p in files if is_video(p)], 1):  # SVT-AV1 already uses ~5 cores
            print(f"video {i}/{len(v)}: {p.name}", flush=True)
            results.append(convert(p))
        renames = {str(a): str(b) for a, b, _ in results}
        MAP.write_text(json.dumps(renames, ensure_ascii=False, indent=1))
        rewrite_links(renames)
        print({k: sum(1 for *_, s in results if s == k) for k in ("conv", "done", "copy", "kept")})
    verify()
