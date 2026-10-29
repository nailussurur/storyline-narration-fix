"""Loudness in 50 ms windows over a time range, to compare individual words (e.g. a too-loud first word).

usage: python word_levels.py START END FILE [FILE ...]
"""
import os
import sys

import numpy as np

import _audio as A

t0, t1 = float(sys.argv[1]), float(sys.argv[2])
times = np.arange(t0, t1, 0.05)
print("window start (s)".ljust(28), " ".join(f"{t:6.2f}" for t in times))
for path in sys.argv[3:]:
    sr = A.probe(path)["sample_rate"]
    y = A.load(path, sr)
    print(os.path.basename(path)[:28].ljust(28), " ".join(f"{A.window_db(y, sr, t, t + 0.05):6.1f}" for t in times))
