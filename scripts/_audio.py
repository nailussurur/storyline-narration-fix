"""Shared helpers: decode/encode through ffmpeg pipes (no temp files, so long Windows paths never matter)."""
import json
import re
import subprocess

import numpy as np

BANDS = [(80, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000),
         (4000, 6000), (6000, 8000), (8000, 11000), (11000, 16000), (16000, 22050)]


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration,bit_rate:stream=codec_name,sample_rate,channels",
                          "-of", "json", str(path)], capture_output=True, check=True, text=True).stdout
    info = json.loads(out)
    st = info["streams"][0]
    return {"duration": float(info["format"]["duration"]), "bit_rate": int(info["format"].get("bit_rate", 0)),
            "codec": st["codec_name"], "sample_rate": int(st["sample_rate"]), "channels": int(st["channels"])}


def load(path, sr):
    """Decode any audio file to mono float64 at sample rate sr."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).astype(np.float64)


def _pipe_args(sr):
    return ["-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-"]


def save(y, path, sr, mp3_bitrate=None):
    args = ["ffmpeg", "-v", "error", "-y", *_pipe_args(sr)]
    if mp3_bitrate:
        args += ["-c:a", "libmp3lame", "-b:a", mp3_bitrate]  # constant bitrate, like the reference
    args.append(str(path))
    subprocess.run(args, input=y.astype(np.float32).tobytes(), check=True)


def filt(y, sr, chain):
    """Run an ffmpeg audio filter chain over a signal and return the result at the same rate."""
    p = subprocess.run(["ffmpeg", "-v", "error", *_pipe_args(sr), "-af", chain,
                        "-f", "f32le", "-ar", str(sr), "-ac", "1", "-"],
                       input=y.astype(np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32).astype(np.float64)


def _stderr(y, sr, chain):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *_pipe_args(sr), "-af", chain, "-f", "null", "-"],
                          input=y.astype(np.float32).tobytes(), capture_output=True).stderr.decode(errors="replace")


def silences(y, sr, threshold=-35, min_len=0.15):
    """Pauses as (start, end) seconds, using ffmpeg silencedetect (the measurement the workflow was built on)."""
    err = _stderr(y, sr, f"silencedetect=noise={threshold}dB:d={min_len}")
    starts = [float(v) for v in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(v) for v in re.findall(r"silence_end: ([\d.]+)", err)]
    dur = len(y) / sr
    return [(s, ends[i] if i < len(ends) else dur) for i, s in enumerate(starts)]


def segments(y, sr, threshold=-35, min_len=0.15):
    """Spoken parts between pauses, as (start, end) seconds."""
    dur = len(y) / sr
    segs, t = [], 0.0
    for s, e in silences(y, sr, threshold, min_len):
        if s - t > 0.05:
            segs.append((t, s))
        t = e
    if dur - t > 0.05:
        segs.append((t, dur))
    return segs


def lufs(y, sr):
    err = _stderr(y, sr, "ebur128")
    vals = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    return float(vals[-1]) if vals else float("nan")


def bands(y, sr):
    """Energy per band in dB relative to the total."""
    s = np.abs(np.fft.rfft(y)) ** 2
    f = np.fft.rfftfreq(len(y), 1 / sr)
    tot = s.sum() + 1e-20
    return {(a, b): 10 * np.log10(s[(f >= a) & (f < b)].sum() / tot + 1e-12) for a, b in BANDS if a < sr / 2}


def frame_db(y, sr, hop=0.01):
    n = int(hop * sr)
    return np.array([20 * np.log10(np.sqrt(np.mean(y[i:i + n] ** 2)) + 1e-9) for i in range(0, len(y) - n + 1, n)])


def window_db(y, sr, t0, t1):
    seg = y[int(t0 * sr):int(t1 * sr)]
    return 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9) if len(seg) else float("-inf")


def speech_bounds(y, sr, threshold=-35):
    """First and last 10 ms frame louder than threshold, in seconds."""
    loud = np.where(frame_db(y, sr) > threshold)[0]
    if not len(loud):
        return 0.0, len(y) / sr
    return loud[0] * 0.01, min((loud[-1] + 1) * 0.01, len(y) / sr)
