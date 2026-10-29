#!/usr/bin/env python3
"""Transcribe a clip with Groq Whisper, keeping word-level timestamps.

    python kit/transcribe.py <video> [--out file.json] [--language en]

Writes <video dir>/<stem>.transcript.json (Groq's verbose_json: segments + words, times in seconds from the
start of the video). Needs GROQ_API_KEY (free at console.groq.com). Long videos are sent in 10-minute chunks.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

MODEL = 'whisper-large-v3'
CHUNK = 600
# a messy priming prompt keeps Whisper verbatim (repeats and fillers stay, so the word times stay honest)
PROMPT = 'Um, so, uh, the the thing is, wait, okay. So, like, verbatim.'


def duration(video):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                          '-of', 'default=nw=1:nk=1', str(video)]))


def audio(video, dst, start, dur):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(start), '-i', str(video), '-t', str(dur),
                    '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'flac', str(dst)], check=True)


def call(client, path, language):
    kw = dict(file=(path.name, path.read_bytes()), model=MODEL, response_format='verbose_json',
              timestamp_granularities=['word', 'segment'], temperature=0.0, prompt=PROMPT)
    if language:
        kw['language'] = language
    r = client.audio.transcriptions.create(**kw)
    return r.model_dump() if hasattr(r, 'model_dump') else dict(r)


def transcribe(video, out=None, language=None):
    from groq import Groq
    if not os.environ.get('GROQ_API_KEY'):
        sys.exit('GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys and export it.')
    video = Path(video).resolve()
    out = Path(out) if out else video.with_name(video.stem + '.transcript.json')
    client = Groq()
    total = duration(video)
    words, segments, text = [], [], []
    with tempfile.TemporaryDirectory() as tmp:
        t = 0.0
        while t < total - 0.05:
            dur = min(CHUNK, total - t)
            a = Path(tmp) / f'chunk{int(t)}.flac'
            audio(video, a, t, dur)
            r = call(client, a, language)
            for w in r.get('words') or []:
                words.append(dict(word=w['word'], start=round(w['start'] + t, 3), end=round(w['end'] + t, 3)))
            for s in r.get('segments') or []:
                segments.append(dict(start=round(s['start'] + t, 3), end=round(s['end'] + t, 3), text=s['text']))
            text.append(r.get('text', ''))
            t += dur
    data = dict(text=' '.join(x.strip() for x in text), segments=segments, words=words, duration=total, model=MODEL)
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--out')
    ap.add_argument('--language')
    a = ap.parse_args()
    p = transcribe(a.video, a.out, a.language)
    d = json.loads(p.read_text())
    print(f'wrote {p}  ({len(d["words"])} words)')
    for s in d['segments']:
        print(f'{s["start"]:7.2f}-{s["end"]:7.2f}  {s["text"].strip()}')
