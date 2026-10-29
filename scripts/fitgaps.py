"""Fit speech to an exact length WITHOUT time-stretching, by shortening or lengthening the quiet gaps between words.

Time-stretching (rubberband/atempo) made the replaced sentence sound glitchy, so the length is taken from or given to
the gaps instead; the words themselves are never touched.

usage: python fitgaps.py IN OUT --target SECONDS   (IN is trimmed to its speech first)
"""
import argparse

import numpy as np

import _audio as A

MAX_SHARE = 0.5  # never take away (or add) more than half of the total gap time; beyond that it sounds rushed/slow


def find_gaps(y, sr, threshold=-35, min_gap=0.04):
    db = A.frame_db(y, sr)
    hop = int(0.01 * sr)
    gaps, run = [], None
    for k, quiet in enumerate(db < threshold):
        if quiet and run is None:
            run = k
        if not quiet and run is not None:
            if (k - run) * 0.01 >= min_gap and run > 0:
                gaps.append((run * hop, k * hop))
            run = None
    return gaps


def fit(y, sr, target):
    """Return (y_fitted, report). Raises ValueError if the gaps cannot absorb the difference."""
    want = int(round(target * sr))
    diff = len(y) - want  # > 0: too long, shorten gaps; < 0: too short, lengthen gaps
    gaps = find_gaps(y, sr)
    total = sum(b - a for a, b in gaps)
    if diff == 0:
        return y, "already the right length"
    if not gaps or abs(diff) > MAX_SHARE * total:
        raise ValueError(f"needs {diff / sr:+.3f}s but word gaps total only {total / sr:.3f}s "
                         f"(limit {MAX_SHARE:.0%}); generate a new take instead of stretching")
    fade = int(0.005 * sr)
    ramp = np.linspace(0, 1, fade)
    out, pos, done = [], 0, 0
    for i, (a, b) in enumerate(gaps):
        n = round(abs(diff) * (b - a) / total) if i < len(gaps) - 1 else abs(diff) - done
        done += n
        mid = (a + b) // 2
        if diff > 0:  # cut exactly n samples from the middle of the gap, crossfading the join
            c0, c1 = mid - n // 2, mid - n // 2 + n
            head = y[pos:c0 + fade].copy()  # the fade overlaps the kept audio, so it removes nothing extra
            head[-fade:] = head[-fade:] * (1 - ramp) + y[c1:c1 + fade] * ramp
            out.append(head)
            pos = c1 + fade
        else:  # insert n samples of the gap's own quiet sound (looped), so the room tone stays continuous
            out.append(y[pos:mid])
            bed = y[a:b]
            out.append(np.resize(bed, n) if len(bed) else np.zeros(n))
            pos = mid
    out.append(y[pos:])
    z = np.concatenate(out)[:want]
    z = np.pad(z, (0, want - len(z)))
    share = abs(diff) / total
    verb = "removed" if diff > 0 else "added"
    return z, f"{len(gaps)} word gaps ({total / sr:.3f}s), {verb} {abs(diff) / sr:.3f}s = {share:.0%} of each gap"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--target", type=float, required=True)
    ap.add_argument("--sr", type=int, default=44100)
    a = ap.parse_args()
    y = A.load(a.inp, a.sr)
    s, e = A.speech_bounds(y, a.sr)
    z, rep = fit(y[int(s * a.sr):int(e * a.sr)], a.sr, a.target)
    A.save(z, a.out, a.sr)
    print(rep)
