# Storyline Narration Fix

A [Claude](https://claude.com) skill that fixes a word in an Articulate Storyline 360 voice-over **without breaking
your timing**.

You know the routine: the AI narration is perfect except for one word. You regenerate the line, and now every pause
has shifted, so you're back in the audio editor nudging silences until the slide animations line up again.

With this skill you hand Claude the audio and say *"change orange to black"*. Claude:

1. measures every pause in your original narration,
2. finds the sentence with the word (by time or by transcribing it),
3. regenerates **only that sentence** in the same voice,
4. fits it into the exact same time slot (no time-stretching, so no warble or glitches),
5. matches the tone and loudness, and fixes a too-loud first word,
6. checks that the length and every pause still match the original.

**Example result:** a 67.24-second narration with 16 pauses. After the fix it is still 67.24 s, every pause is within
0.006 s of the original, and only the changed sentence is new audio.

## Which voices work

| Your Storyline voice | What happens |
|---|---|
| **AI voices** (Insert > Audio > AI Audio): Adam, Alice, Bella, Bill, Brian, Callum, Charlie, Chris, Daniel, Eric, George, Harry, Jessica, Laura, Liam, Lily, Matilda, River, Roger, Sarah, Will | Storyline's AI voices are ElevenLabs voices, so Claude regenerates the sentence in the same voice through ElevenLabs. |
| **Voice Library / My Voices** voices | Claude finds the same voice in ElevenLabs' Voice Library by name. |
| **Classic voices** (Text-to-Speech > Standard or Neural: Joanna, Matthew, Amy, Emma, Russell, ...) | These voices aren't in ElevenLabs. Regenerate the corrected sentence in Storyline, export it, and Claude splices it in with the exact timing. |

Heads-up: "Brian" is in both lists. The AI Brian is American, the classic Brian is British.

## What you need

- The **Claude desktop app** (Code tab) or **Claude Code**. The skill runs small Python scripts on your computer, so it
  doesn't work in the plain claude.ai web chat.
- **Python 3** with **numpy** (`pip install numpy`).
- **ffmpeg** (Windows: `winget install Gyan.FFmpeg` · macOS: `brew install ffmpeg` · Linux: your package manager).
- Optional: an **ElevenLabs** account (the cheapest paid plan is enough) connected to Claude through the ElevenLabs
  connector. Without it, you can still bring a re-recorded sentence yourself and let the skill do the timing.

## Install

Clone or download this repository into your Claude skills folder:

```bash
git clone https://github.com/nailussurur/storyline-narration-fix ~/.claude/skills/storyline-narration-fix
```

On Windows the folder is `C:\Users\<you>\.claude\skills\storyline-narration-fix`. Alternatively, install the
`storyline-narration-fix.skill` file from the
[Releases page](https://github.com/nailussurur/storyline-narration-fix/releases).

## Use

Start a session in the Claude desktop app or Claude Code and say something like:

> Here's my Storyline narration: `C:\...\slide4.mp3`. Change "orange" to "black". It's the Matilda AI voice.

Claude asks before spending any ElevenLabs credits and shows the price first.

## Cost (ElevenLabs credits, approximate)

| Step | Credits |
|---|---|
| Regenerating one sentence | ~70 |
| Transcribing (only if you don't know when the word is spoken) | ~330 per minute of audio |
| Measuring, fitting, matching, verifying | free (runs on your computer) |

## Good to know

- **Listen to the result.** The skill checks timing, loudness and tone with meters, but no meter can prove a sentence
  has no subtle glitch. You also get the untouched generated sentence, so you can tell where a problem came from.
- **Don't clone a Storyline narrator.** ElevenLabs blocks clones of voices that aren't yours, and the built-in voice is
  the same voice anyway.
- **Use the same model as Storyline.** Storyline lets you pick V4, V3, Multilingual v2 or Flash v2.5. Tell Claude which
  one you used so the new sentence sounds the same.

## Files

- `SKILL.md`: the instructions Claude follows.
- `scripts/`: the audio tools (`measure_pauses.py`, `splice.py`, `fitgaps.py`, `tone_check.py`, `word_levels.py`,
  `pitch_check.py`, `split_take.py`).

## License

MIT. Not affiliated with Articulate or ElevenLabs. Use voices in line with Articulate's and ElevenLabs' terms.
