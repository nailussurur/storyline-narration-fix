"""Compare loudness and tone (energy per frequency band) of audio files or parts of them.

usage: python tone_check.py FILE[@START-END] FILE[@START-END] ...
The first file is the reference; bands differing from it by more than 2 dB are marked with *.
"""
import os
import sys

import _audio as A


def parse(arg):
    path, _, rng = arg.partition("@")
    t = [float(v) for v in rng.split("-")] if rng else None
    return path, t


rows = []
for arg in sys.argv[1:]:
    path, t = parse(arg)
    sr = A.probe(path)["sample_rate"]
    y = A.load(path, sr)
    if t:
        y = y[int(t[0] * sr):int(t[1] * sr)]
    rows.append((os.path.basename(arg), A.lufs(y, sr), A.bands(y, sr)))

keys = list(rows[0][2])
def hz(v):
    return f"{v / 1000:g}k" if v >= 1000 else str(v)


print("file".ljust(34), "LUFS ", " ".join(f"{hz(a)}-{hz(b)}".rjust(9) for a, b in keys))
for i, (name, loud, b) in enumerate(rows):
    cells = []
    for k in keys:
        v = b.get(k, float("nan"))
        mark = "*" if i and abs(v - rows[0][2][k]) > 2 and rows[0][2][k] > -50 else " "
        cells.append(f"{v:8.1f}{mark}")
    print(name[:34].ljust(34), f"{loud:5.1f}", " ".join(cells))
