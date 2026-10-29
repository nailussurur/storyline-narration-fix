"""Full re-voice mode: cut one ElevenLabs take (generated with a <break> between every segment) into N pieces.

usage: python split_take.py TAKE.mp3 --count N --out-dir DIR [--sr 44100]
Cuts at the N-1 longest pauses, so the voice's own short comma pauses never cause a wrong cut.
Writes piece_01.wav ... piece_NN.wav, each trimmed to its speech, for splice.py --replace K=piece_K.wav.
"""
import argparse
import os

import _audio as A

ap = argparse.ArgumentParser()
ap.add_argument("take")
ap.add_argument("--count", type=int, required=True)
ap.add_argument("--out-dir", required=True)
ap.add_argument("--sr", type=int, default=44100)
a = ap.parse_args()

y = A.load(a.take, a.sr)
s0, s1 = A.speech_bounds(y, a.sr)
pauses = [p for p in A.silences(y, a.sr, min_len=0.1) if p[0] > s0 + 0.05 and p[1] < s1 - 0.05]
if len(pauses) < a.count - 1:
    raise SystemExit(f"only {len(pauses)} pauses found, need {a.count - 1}: check the <break> tags in the take")
cuts = sorted(sorted(pauses, key=lambda p: p[1] - p[0], reverse=True)[:a.count - 1])
shortest_cut = min(e - s for s, e in cuts)
next_longest = max([e - s for s, e in pauses if (s, e) not in cuts], default=0)
print(f"cut pauses: shortest {shortest_cut:.2f}s; longest pause left inside pieces {next_longest:.2f}s")
if shortest_cut - next_longest < 0.2:
    print("WARNING: cut and natural pauses are close in length; listen to the pieces before splicing")

os.makedirs(a.out_dir, exist_ok=True)
edges = [s0] + [x for c in cuts for x in c] + [s1]
for i in range(a.count):
    t0, t1 = edges[2 * i], edges[2 * i + 1]
    piece = y[int(t0 * a.sr):int(t1 * a.sr)]
    b0, b1 = A.speech_bounds(piece, a.sr)
    A.save(piece[int(b0 * a.sr):int(b1 * a.sr)], os.path.join(a.out_dir, f"piece_{i + 1:02d}.wav"), a.sr)
    print(f"piece_{i + 1:02d}  {t1 - t0:6.3f}s")
