"""Replace spoken segments of a reference narration with new takes, keeping its exact length and pauses (free, local).

usage: python splice.py --ref REF.mp3 --replace 3=new.mp3 [--replace 7=other.wav ...] --out "C:/path/Name"
Writes Name.wav and (if the reference is MP3) Name.mp3 at the reference's constant bitrate, then verifies the result.
Segment numbers come from measure_pauses.py.

Per replacement, in this order (each step fixes a problem found on the first real job):
  1. trim the new take to its speech
  2. fit it to the slot by shortening/lengthening word gaps - never time-stretch (stretching sounded glitchy)
  3. copy the reference's frequency ceiling (e.g. nothing above 11 kHz) with one clean resample, not stacked
     low-pass filters (those dulled the 6-11 kHz clarity range)
  4. match tone band by band to the reference speech (clamped to +-6 dB)
  5. match loudness to the slot it replaces
  6. ease the first word if it comes out louder than the reference's first word (the "and" jump)
  7. 5 ms fade in / 10 ms fade out, so the joins in the pauses never click
"""
import argparse
import json

import numpy as np

import _audio as A
from fitgaps import fit

STANDARD_KBPS = [96, 128, 160, 192, 224, 256, 320]


def ceiling(y, sr):
    """Highest content frequency of the reference, if it is clearly band-limited below Nyquist."""
    s = np.abs(np.fft.rfft(y)) ** 2
    f = np.fft.rfftfreq(len(y), 1 / sr)
    tot = s.sum()
    for c in (8000, 11025, 16000):
        if c < sr / 2 - 500 and 10 * np.log10(s[f > c].sum() / tot + 1e-20) < -55:
            return c
    return None


def tone_match(new, ref_speech, sr, top):
    rb, nb = A.bands(ref_speech, sr), A.bands(new, sr)
    entries = []
    for (a, b), rv in rb.items():
        if (top and a >= top) or rv < -50:
            continue
        entries.append((np.sqrt(a * b), float(np.clip(rv - nb[(a, b)], -6, 6))))
    if not entries:
        return new, []
    chain = "firequalizer=gain_entry='" + ";".join(f"entry({fc:.0f},{g:.2f})" for fc, g in entries) + "'"
    return A.filt(new, sr, chain), entries


def first_word_end(y, sr, limit=0.4):
    db = A.frame_db(y[:int(limit * sr)], sr)
    for k in range(5, len(db) - 2):
        if (db[k:k + 3] < -35).all():
            return k * 0.01
    return 0.13


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--replace", action="append", required=True, help="N=file (segment number from measure_pauses)")
    ap.add_argument("--out", required=True, help="output path without extension")
    ap.add_argument("--report", help="optional JSON report path")
    a = ap.parse_args()

    info = A.probe(a.ref)
    sr = info["sample_rate"]
    ref = A.load(a.ref, sr)
    segs = A.segments(ref, sr)
    top = ceiling(ref, sr)
    ref_speech = np.concatenate([ref[int(s * sr):int(e * sr)] for s, e in segs])
    out = ref.copy()
    report = {"ref": a.ref, "ceiling_hz": top, "replacements": []}
    print(f"reference: {info['duration']:.3f}s, {len(segs)} segments, content ceiling "
          f"{top or 'none'} Hz, {A.lufs(ref, sr):.1f} LUFS")

    for item in a.replace:
        n, path = item.split("=", 1)
        n = int(n)
        s, e = segs[n - 1]
        i0, i1 = int(round(s * sr)), int(round(e * sr))
        slot = ref[i0:i1]
        new = A.load(path, sr)
        b0, b1 = A.speech_bounds(new, sr, threshold=-50)  # keep the soft edges until the sound is final
        new = new[int(b0 * sr):int(b1 * sr)]
        if top:
            new = A.filt(new, sr, f"aresample={2 * top}:resampler=soxr,aresample={sr}:resampler=soxr")
        new, eq = tone_match(new, ref_speech, sr, top)
        gain = A.lufs(slot, sr) - A.lufs(new, sr)
        new = new * 10 ** (gain / 20)
        # trim with the same -35 dB rule that defines the slot, so the pauses either side keep their lengths
        b0, b1 = A.speech_bounds(new, sr)
        new = new[int(b0 * sr):int(b1 * sr)]
        speech_len = len(new) / sr
        new, fit_note = fit(new, sr, (i1 - i0) / sr)
        jump = A.window_db(new, sr, 0, 0.15) - A.window_db(slot, sr, 0, 0.15)
        eased = 0.0
        if jump > 1.5:
            t1 = first_word_end(new, sr)
            t = np.arange(len(new)) / sr
            g = np.where(t < t1, 10 ** (-jump / 20),
                         np.where(t < t1 + 0.03, 10 ** (-jump / 20) + (1 - 10 ** (-jump / 20)) * (t - t1) / 0.03, 1))
            new, eased = new * g, jump
        new = A.filt(new, sr, f"afade=t=in:d=0.003,afade=t=out:st={(i1 - i0) / sr - 0.005:.4f}:d=0.005")
        new = np.pad(new, (0, max(0, (i1 - i0) - len(new))))[:i1 - i0]
        out[i0:i1] = new
        rep = {"segment": n, "file": path, "slot": [round(s, 3), round(e, 3)], "new_speech_s": round(speech_len, 3),
               "fit": fit_note, "eq_db": [[round(fc), round(g, 1)] for fc, g in eq], "gain_db": round(gain, 2),
               "first_word_eased_db": round(eased, 1)}
        report["replacements"].append(rep)
        print(f"segment {n}: {s:.3f}-{e:.3f}s | {fit_note} | gain {gain:+.1f} dB | "
              f"first word {'eased ' + format(eased, '.1f') + ' dB' if eased else 'ok'}")

    A.save(out, a.out + ".wav", sr)
    if info["codec"] == "mp3":
        kbps = min(STANDARD_KBPS, key=lambda k: abs(k - info["bit_rate"] / 1000))
        A.save(out, a.out + ".mp3", sr, f"{kbps}k")
        report["mp3_kbps"] = kbps

    # verify against the reference
    check = A.load(a.out + ".mp3" if info["codec"] == "mp3" else a.out + ".wav", sr)
    rp, op = A.silences(ref, sr), A.silences(check, sr)
    worst = max((abs((oe - os_) - (re_ - rs)) for (rs, re_), (os_, oe) in zip(rp, op)), default=0)
    dur_out = A.probe(a.out + ".wav")["duration"]
    ok = len(rp) == len(op) and worst <= 0.02 and abs(dur_out - info["duration"]) < 0.002
    report["verify"] = {"duration_ref": info["duration"], "duration_out": dur_out, "pauses_ref": len(rp),
                        "pauses_out": len(op), "worst_pause_diff_s": round(worst, 3), "ok": ok}
    print(f"\nverify: duration {dur_out:.3f}s vs {info['duration']:.3f}s | pauses {len(op)} vs {len(rp)} | "
          f"worst pause difference {worst:.3f}s | {'OK' if ok else 'CHECK'}")
    rb = A.bands(ref_speech, sr)  # compare with the narrator's voice overall; single words shift a slot's tone
    for r in report["replacements"]:
        s, e = r["slot"]
        ob = A.bands(check[int(s * sr):int(e * sr)], sr)
        off = {f"{a_}-{b_}": round(float(ob[(a_, b_)] - v), 1) for (a_, b_), v in rb.items()
               if v > -50 and abs(ob[(a_, b_)] - v) > 2}
        r["tone_off_db"] = off
        print(f"segment {r['segment']} tone vs the narrator's voice: "
              f"{'all bands within 2 dB' if not off else 'bands off by >2 dB: ' + str(off)}")
    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=1)


if __name__ == "__main__":
    main()
