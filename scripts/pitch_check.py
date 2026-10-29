"""Compare the voice pitch of audio files, to check that a candidate voice matches the reference narrator.

usage: python pitch_check.py FILE[@START-END] FILE[@START-END] ...
Same narrator: medians within ~5 Hz and similar middle ranges. Brightness differences are fixed later by tone matching.
"""
import os
import sys

import numpy as np

import _audio as A


def f0_track(x, sr, fmin=70, fmax=400, frame=0.04, hop=0.01):
    n, h = int(frame * sr), int(hop * sr)
    lo, hi = int(sr / fmax), int(sr / fmin)
    rms_all = np.sqrt(np.mean(x ** 2))
    out = []
    for i in range(0, len(x) - n, h):
        f = x[i:i + n] * np.hanning(n)
        if np.sqrt(np.mean(f ** 2)) < 0.5 * rms_all:
            continue
        ac = np.correlate(f, f, "full")[n - 1:]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        lag = lo + np.argmax(ac[lo:hi])
        if ac[lag] > 0.5:
            out.append(sr / lag)
    return np.array(out)


for arg in sys.argv[1:]:
    path, _, rng = arg.partition("@")
    sr = A.probe(path)["sample_rate"]
    y = A.load(path, sr)
    if rng:
        t0, t1 = (float(v) for v in rng.split("-"))
        y = y[int(t0 * sr):int(t1 * sr)]
    f0 = f0_track(y, sr)
    q1, med, q3 = np.percentile(f0, [25, 50, 75])
    print(f"{os.path.basename(arg)[:40]:<40} median pitch {med:6.1f} Hz | middle range {q1:5.1f}-{q3:5.1f} Hz")
