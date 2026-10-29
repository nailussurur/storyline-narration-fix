"""Measure a reference narration: format, loudness, every pause and every spoken segment (free, local).

usage: python measure_pauses.py REF.mp3 [--json OUT.json] [--threshold -35] [--min 0.15]
Segment numbers printed here are the ones splice.py --replace N=... expects.
"""
import argparse
import json

import _audio as A

ap = argparse.ArgumentParser()
ap.add_argument("ref")
ap.add_argument("--json")
ap.add_argument("--threshold", type=float, default=-35)
ap.add_argument("--min", type=float, default=0.15)
a = ap.parse_args()

info = A.probe(a.ref)
sr = info["sample_rate"]
y = A.load(a.ref, sr)
pauses = A.silences(y, sr, a.threshold, a.min)
segs = A.segments(y, sr, a.threshold, a.min)
loud = A.lufs(y, sr)

print(f"{info['codec']} {info['sample_rate']} Hz, {info['channels']} ch, {info['bit_rate'] // 1000} kbps, "
      f"{info['duration']:.3f} s, {loud:.1f} LUFS")
print(f"\n{len(pauses)} pauses (quieter than {a.threshold} dB for at least {a.min} s):")
for i, (s, e) in enumerate(pauses, 1):
    print(f"  {i:2d}  {s:7.3f} -> {e:7.3f}   {e - s:6.3f} s")
print(f"\n{len(segs)} spoken segments:")
for i, (s, e) in enumerate(segs, 1):
    print(f"  {i:2d}  {s:7.3f} -> {e:7.3f}   {e - s:6.3f} s")

if a.json:
    with open(a.json, "w", encoding="utf-8") as f:
        json.dump({"info": info, "lufs": loud, "pauses": pauses, "segments": segs}, f, indent=1)
