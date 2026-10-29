---
name: storyline-narration-fix
description: Fix a word or phrase in an Articulate Storyline 360 AI voice-over (or any narration MP3/WAV) without redoing the timing. Regenerates only the changed sentence in the same voice (via the ElevenLabs connector, or a take the user exports from Storyline), then splices it back so the file keeps exactly the same length, the same number of pauses and the same pause durations, with matched tone and loudness and no glitches. Also re-voices a whole narration while copying a reference's pause timing. Use this whenever someone has a Storyline/e-learning narration and says things like "change this word in the audio", "fix a mispronounced word", "replace orange with black", "same voice, same silences", "keep the timing", "don't break my slide sync", or wants ElevenLabs text-to-speech to follow a reference recording's pauses, even if Storyline or ElevenLabs isn't named.
---

# Storyline narration fix

Changing one or two words in a Storyline narration normally means regenerating the line and then re-adjusting
pauses by hand until it lines up with the slide animations again. This skill removes that work.

Goal: the original narration with only the changed words re-voiced, in the same voice, with **identical total length,
pause count and pause durations**, matched tone and loudness, and no audible joins or glitches.

Default to the **splice**: regenerate only the sentence(s) that change and keep everything else as the original audio.
It is the cheapest option and the untouched parts stay perfect. Full re-voice is the exception (see the end).

Scripts live in `scripts/` next to this file. Run them with `python scripts/<name>.py ...` (Python 3 + numpy, and
ffmpeg/ffprobe on PATH). Don't use `python -I`, which hides their shared `_audio.py` helper. They decode through ffmpeg
pipes, so long paths are fine for them; on Windows keep any temp files you write yourself in a short folder such as
`%TEMP%\snf\<job>`, because the 260-character path limit can silently break saving in deep folders.

## 1. Check the setup (free)

- `ffmpeg`, `ffprobe` and `python -c "import numpy"` work. If not, tell the user what to install
  (e.g. `winget install Gyan.FFmpeg` / `brew install ffmpeg`, and `pip install numpy`).
- For generating new audio through Claude: the ElevenLabs connector's tools (`creative_generate_speech`,
  `creative_transcribe_audio`, `creative_list_voices`, ...) are available; load them with ToolSearch. If the user has no
  ElevenLabs connection, use **bring-your-own-take mode** (step 6b): everything else still works.

## 2. Measure the original (free)

```
python scripts/measure_pauses.py "ORIGINAL.mp3" --json "<temp>/ref.json"
```
Prints format/bitrate, loudness, every pause and the numbered spoken segments. Show the user the pause table: it is
the timing contract the result must meet.

## 3. Find the words to change

Match the changed words to the numbered segment that contains them.
- **Cheapest:** if the user knows roughly when the word is spoken ("around 0:09") or which sentence it is, pick the
  segment from the table. No transcription needed.
- **Otherwise transcribe** with ElevenLabs Scribe (about 330 credits per minute of audio), which returns per-word
  start/end times. See "Getting a local file into ElevenLabs" below.

Write the new text for **that whole segment**, word for word with the change applied, so it fits the slot naturally.
Several changes means several segments.

## 4. Identify the voice (ask the user)

Ask which voice the narration was made with and where in Storyline it came from. The answer decides everything:

**a) A Storyline AI voice** (Insert > Audio > AI Audio, or AI Assistant > Generate AI Audio). Storyline's AI voices are
ElevenLabs voices, so the exact same voice exists in ElevenLabs. Look it up in this table (checked Oct 2026):

| Storyline AI voice | ElevenLabs voice ID | | Storyline AI voice | ElevenLabs voice ID |
|---|---|---|---|---|
| Adam | `pNInz6obpgDQGcFmaJgB` | | Harry | `SOYHLrjzK2X1ezoPC6cr` |
| Alice | `Xb7hH8MSUJpSbSDYk0k2` | | Jessica | `cgSgspJ2msm6clMCkdW9` |
| Bella | `hpp4J3VqNfWAUOO0d1Us` | | Laura | `FGY2WhTYpPnrIDTdsKH5` |
| Bill | `pqHfZKP75CvOlQylNhV4` | | Liam | `TX3LPaxmHKxFdv7VOQHJ` |
| Brian | `nPczCjzI2devNBz1zQrb` | | Lily | `pFZP5JQG7iQjIQuC4Bku` |
| Callum | `N2lVS1w4EtoT3dr4eOWO` | | Matilda | `XrExE9yKIg1WjnnlVkGX` |
| Charlie | `IKne3meq5aSn9XLyUdCD` | | River | `SAz9YHcvj6GT2YYXdXww` |
| Chris | `iP95p4xoKVk53GoZ742B` | | Roger | `CwhRBWXzGAHq8TQ4Fs17` |
| Daniel | `onwK4e9ZLuTAKqWW03F9` | | Sarah | `EXAVITQu4vr4xnSDxMaL` |
| Eric | `cjVigY5qzO86Huf0OWal` | | Will | `bIHbv24MWmeRgasZH58o` |
| George | `JBFqnCBsd6RMkjVDRZzb` | | | |

If a name isn't in the table (Articulate adds and retires voices), search `creative_list_voices` by name and prefer
the result with `category: premade`. Matilda was verified against a real Storyline narration (median pitch within
1 Hz). For the others, the name and description match; if the user is unsure, run the pitch test in (c).

**b) A voice from Storyline's Voice Library or "My Voices".** These are ElevenLabs Voice Library voices. Search
`creative_list_voices` by the name shown in Storyline and confirm the description matches before using it.

**c) Not sure which voice.** Generate one short test sentence (~70 credits) with the most likely candidate and compare:
`python scripts/pitch_check.py "ORIGINAL.mp3@START-END" test.mp3`. Same narrator: median pitch within ~5 Hz and a similar
middle range. Brightness differences don't matter; step 7 fixes them.

**d) A classic Storyline voice** (Text-to-Speech > Standard or Neural: Joanna, Matthew, Amy, Emma, Kendra, Russell, the
British "Brian", ...). These come from a different provider and do **not** exist in ElevenLabs. Don't substitute a
lookalike; use bring-your-own-take mode (step 6b) with the corrected sentence generated in Storyline itself.
Note that "Brian" exists in both lists: the AI Brian is American, the classic Brian is British. Ask if unsure.

**Never clone the narrator.** A clone of a voice that isn't the user's own (e.g. a Storyline narrator) gets blocked
by ElevenLabs ("may violate our Terms of Service and requires verification") and cannot be verified. The premade or
library voice is the same voice anyway.

Also ask which **model** Storyline used (V4 is Storyline's default; V3, Multilingual v2 and Flash v2.5 are options),
and use the same one, since models sound different. If the user doesn't know, start with `eleven_multilingual_v2`
(the most consistent model) and let the pitch/tone checks and their ears decide.

## 5. Price it and ask

Before every paid generation, call it with `estimate_only: true` and tell the user the cost in credits (and dollars if
returned). Wait for a yes. Never retry a generation without asking, since each call is charged again.

## 6. Get the new take

**6a) Through ElevenLabs.** `creative_generate_speech` with the voice ID from step 4, the model from step 4,
`generations_count: 1`, and the segment text as the prompt. Write numbers and codes the way the narrator says them
(e.g. "D R one zero two"). Then `creative_get_generations` → `full_res_url` and download it into its own folder.

**6b) Bring your own take.** The user regenerates just the corrected sentence wherever the voice lives (e.g. Storyline's
text-to-speech) and exports it as an audio file (in Storyline, e.g. from the Media Library). Use that file in step 7
exactly like an ElevenLabs take. No ElevenLabs credits needed.

## 7. Splice, match and verify (free)

```
python scripts/splice.py --ref "ORIGINAL.mp3" --replace 3="<temp>/new.mp3" --out "<output folder>/Name - fixed" --report "<temp>/report.json"
```
For each replaced segment it trims the take to its speech, copies the original's frequency ceiling (e.g. nothing
above 11 kHz), matches tone band by band and loudness, fits the take into the exact slot by adjusting the gaps
between words, eases a too-loud first word, fades the joins, writes WAV plus MP3 at the original's bitrate, and
verifies duration, pause count and pause lengths.

Lessons built into it:
- **No time-stretching.** Stretching a sentence by even 5% (rubberband or atempo) made it sound warbly and glitchy.
  The length comes from the gaps between words instead.
- **No stacked low-pass filters.** They dulled consonant clarity. One clean resample copies the original's ceiling.
- **First word check.** A regenerated sentence often starts louder than the original ("and" jumped by 5 dB).

If fitting fails ("generate a new take instead of stretching"), the take is too far off the slot length: ask for a new
take rather than stretching.

Check the printout: `verify ... OK` (duration identical, every pause within 0.02 s), the first-word line, and the
tone line. For a closer look: `scripts/word_levels.py START END original out` (word-by-word loudness) and
`scripts/tone_check.py "original@S-E" "out@S-E"` (tone per frequency band).

## 8. Deliver

Give the user the finished MP3 (plus WAV), the new sentence on its own, and the **untouched downloaded take** named
"... - raw take.mp3". If they hear a problem, the raw file shows whether it came from the voice generator (get a new
take) or from processing (fix locally, free).

Report briefly: what changed and where (seconds), the verification numbers, and credits spent. Ask them to listen
around the changed segment: meters cannot prove the absence of subtle glitches, so don't claim it sounds clean.

## Getting a local file into ElevenLabs (for transcription)

The connector cannot read a local file, and its in-chat upload picker may not render in the Claude desktop app. What
works:
1. `creative_create_flow` (name it after the job).
2. `creative_transcribe_audio` with that `flow_id` and no `connect_from`: this creates an empty audio node.
3. Tell the user: ElevenLabs website → left sidebar **Flows** → open the flow → drag the file onto
   **"Audio (waiting for upload)"**.
4. When they confirm, `creative_get_flow` to get the node id, then `creative_transcribe_audio` with
   `connect_from=[that node]`.
5. If the result view doesn't render, read it with `creative_get_flow_run_status` (returns `transcripts` with
   per-word start/end).

## Full re-voice mode (only when asked)

To re-voice a whole narration while keeping the original timing: generate all segments in one take with a clear pause
between consecutive segments (`<break time="1.0s" />` on Multilingual v2 / Flash / Turbo; v3/v4 ignore break tags, so
try `[long pause]` there, which is less exact and untested with this workflow), then:
```
python scripts/split_take.py take.mp3 --count <segments> --out-dir "<temp>/pieces"
python scripts/splice.py --ref ORIGINAL.mp3 --replace 1=<temp>/pieces/piece_01.wav --replace 2=... --out ...
```
This also reproduces pauses longer than 3 s, which ElevenLabs' break tags can't make. If `split_take` warns that cut
and natural pauses are close in length, listen to the pieces before splicing.

## Reference

| Topic | Fact |
|---|---|
| Credits (approx.) | Transcription ~330/min · Multilingual v2 ~1 per character · one-sentence take ~70 · a 70 s script ~1,000 |
| Pause tags | `<break time="x.xs" />`, max 3 s, Multilingual v2 / Flash / Turbo only |
| Voice Changer | Keeps timing exactly but cannot change words; only useful when the words stay the same |
| Connector views | Speech and upload views may not render in the desktop app: read results with run status / get_generations |
