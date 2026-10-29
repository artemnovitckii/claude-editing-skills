#!/usr/bin/env python3
"""Shared kit for the editing skills: clip prep, word timings, captions, HyperFrames comps, render and checks.

    python kit/reel.py words <video> [--start S] [--end E]   # word timings, local to S (transcribes on first use)
    python kit/reel.py frame <video> <t> <out.jpg>           # one 9:16 frame with a y ruler, to find eyes and chin
    python kit/reel.py sheet <video.mp4> <out.jpg> [n]       # contact sheet with the Instagram safe zone drawn

Every skill's build.py is `Job(spec) -> Comp -> finish()`: the spec is a JSON file the skill's SKILL.md describes,
with paths relative to the spec file and times either in seconds (local to "start") or a spoken word to anchor on
("carousel", "carousel#2" for its second time, "carousel+0.2" for a little after it).
"""
import argparse
import glob
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
FPS = 30
W, H = 1080, 1920
HYPERFRAMES = 'hyperframes@0.8.34'
SAFE_TOP, SAFE_BOTTOM, SAFE_SIDE = 220, 1500, 100      # Instagram covers the top ~220 px and the bottom ~420 px
FRAME_VF = f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1'

BASE_CSS = """
@font-face{font-family:'Inter';font-weight:400;src:url(fonts/inter-400-normal.woff2) format('woff2')}
@font-face{font-family:'Inter';font-weight:500;src:url(fonts/inter-500-normal.woff2) format('woff2')}
@font-face{font-family:'Inter';font-weight:600;src:url(fonts/inter-600-normal.woff2) format('woff2')}
@font-face{font-family:'Inter';font-weight:700;src:url(fonts/inter-700-normal.woff2) format('woff2')}
@font-face{font-family:'Inter';font-weight:800;src:url(fonts/inter-800-normal.woff2) format('woff2')}
@font-face{font-family:'Archivo Black';src:url(fonts/archivo-black-400-normal.woff2) format('woff2')}
@font-face{font-family:'DM Serif Display';font-style:italic;src:url(fonts/dm-serif-display-400-italic.woff2) format('woff2')}
@font-face{font-family:'Instrument Serif';src:url(fonts/InstrumentSerif-400-normal.woff2) format('woff2')}
@font-face{font-family:'Instrument Serif';font-style:italic;src:url(fonts/InstrumentSerif-400-italic.woff2) format('woff2')}
@font-face{font-family:'Pixelify Sans';font-weight:500;src:url(fonts/PixelifySans-500-normal.woff2) format('woff2')}
@font-face{font-family:'Pixelify Sans';font-weight:700;src:url(fonts/PixelifySans-700-normal.woff2) format('woff2')}
@font-face{font-family:'TikTok Sans';font-weight:100 900;src:url(fonts/TikTokSans.ttf) format('truetype')}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1920px;overflow:hidden;background:#000}
#root{position:relative;width:1080px;height:1920px;overflow:hidden;font-family:'Inter',sans-serif}
video{display:block;object-fit:fill}
.a{position:absolute}
.hid{visibility:hidden}
img{display:block}
"""


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def duration(path):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                          '-of', 'default=nw=1:nk=1', str(path)]))


def bare(w):
    """a word as captions show it: lowercase, no punctuation (numbers keep their commas)"""
    keep = ''.join(c for c in w.lower() if c.isalnum() or c in "'’,-").strip('-')
    return keep.replace(',', '') if not keep.replace(',', '').isdigit() else keep


def rich(s):
    """escape, then *word* -> <em>word</em> and newlines -> <br>"""
    s = html.escape(str(s))
    s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s, flags=re.S)
    return s.replace('\n', '<br>')


# ---------------------------------------------------------------- the job: spec + clip + words
class Job:
    def __init__(self, spec_path, skill):
        self.spec_file = Path(spec_path).resolve()
        self.s = json.loads(self.spec_file.read_text())
        self.base = self.spec_file.parent
        self.skill = skill
        self.video = self.path(self.s['video'])
        if not self.video.exists():
            sys.exit(f'video not found: {self.video}')
        self.start = float(self.s.get('start', 0))
        self.end = float(self.s.get('end') or duration(self.video))
        self.out = self.path(self.s.get('out') or f'{self.video.stem}.{skill}.mp4')
        self.out.parent.mkdir(parents=True, exist_ok=True)
        self.work = self.out.parent / '.work' / self.out.stem
        self.work.mkdir(parents=True, exist_ok=True)
        self.clip = prep_clip(self.video, self.start, self.end, self.work)
        self.dur = math.floor(duration(self.clip) * FPS - 1) / FPS
        tr = self.s.get('transcript')
        self.words = load_words(self.video, self.start, self.end, self.path(tr) if tr else None)

    def get(self, key, default=None):
        return self.s.get(key, default)

    def path(self, v):
        p = Path(os.path.expanduser(str(v)))
        return p if p.is_absolute() else (self.base / p).resolve()

    def images(self, v):
        """a list of paths, or one glob ("covers/*.jpg"), -> sorted list of existing paths"""
        if not v:
            return []
        items = v if isinstance(v, list) else [v]
        out = []
        for it in items:
            p = str(self.path(it))
            hits = sorted(glob.glob(p)) if any(ch in p for ch in '*?[') else [p]
            for h in hits:
                if not Path(h).exists():
                    sys.exit(f'image not found: {h}')
                out.append(Path(h))
        return out

    def t(self, v, default=None):
        """seconds (local to start), or a spoken word to anchor on: "word", "word#2", "word+0.2", "two words" """
        if v is None:
            if default is None:
                raise ValueError('a time is missing')
            return float(default)
        if isinstance(v, (int, float)):
            return float(v)
        m = re.match(r'^(.+?)(?:#(\d+))?([+-]\d*\.?\d+)?$', str(v).strip())
        target = [bare(x) for x in m.group(1).split()]
        nth = int(m.group(2) or 1)
        shift = float(m.group(3) or 0)
        seen = 0
        bw = [bare(w) for w, _, _ in self.words]
        for i in range(len(bw)):
            if bw[i:i + len(target)] == target:
                seen += 1
                if seen == nth:
                    return round(max(0.0, self.words[i][1] + shift), 3)
        said = ' '.join(f'{w}@{t:.2f}' for w, t, _ in self.words)
        raise ValueError(f'"{v}" is not said in this clip. Words: {said}')

    def cutout(self, model=None):
        out = self.work / 'cutout.webm'
        stamp = self.work / 'cutout.ok'
        if out.exists() and stamp.exists() and stamp.read_text() == str(self.clip.stat().st_mtime):
            return out
        sys.path.insert(0, str(KIT))
        from cutout import cutout
        cutout(self.clip, out, model or self.get('cutout_model', 'mobilenetv3'))
        stamp.write_text(str(self.clip.stat().st_mtime))
        return out

    def finish(self, comp, out=None):
        out = Path(out or self.out)
        comp.write()
        comp.render(out)
        sh = out.with_name(out.stem + '.sheet.jpg')
        sheet(out, sh)
        print(f'\nDONE  {out}\ncheck {sh}  (red = covered by the Instagram UI)')
        return out


def prep_clip(video, start, end, work):
    """the segment as a 1080x1920, 30 fps, frame-accurate clip (cached)"""
    out = work / 'clip.mp4'
    key = json.dumps([str(video), os.path.getmtime(video), start, end])
    stamp = work / 'clip.key'
    if out.exists() and stamp.exists() and stamp.read_text() == key:
        return out
    run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{start:.3f}', '-i', video, '-t', f'{end - start:.3f}',
         '-vf', f'{FRAME_VF},fps={FPS}', '-c:v', 'libx264', '-preset', 'fast', '-crf', '14', '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out])
    stamp.write_text(key)
    return out


def load_words(video, start, end, transcript=None):
    """[(word, local_start, local_end)] for the words said between start and end"""
    tp = transcript or Path(video).with_name(Path(video).stem + '.transcript.json')
    if not Path(tp).exists():
        sys.path.insert(0, str(KIT))
        from transcribe import transcribe
        print('transcribing (one time)...', flush=True)
        transcribe(video, tp)
    d = json.loads(Path(tp).read_text())
    ws = d.get('words') or [w for s in d.get('segments', []) for w in s.get('words', [])]
    out = []
    for w in ws:
        if start - 0.05 <= w['start'] < end - 0.08:
            out.append((w['word'].strip(), round(max(w['start'], start) - start, 3), round(min(w['end'], end) - start, 3)))
    return out


# ---------------------------------------------------------------- the composition
class Comp:
    def __init__(self, job, name='main', voice=True, dur=None):
        self.job, self.dur = job, dur or job.dur
        self.dir = job.work / f'comp_{name}'
        self.css, self.body, self.js = [BASE_CSS], [], []
        self.track = 0
        self.files = {}
        if voice:
            self.body.append(f'<audio id="voice" src="{self.asset(job.clip)}" data-start="0" data-media-start="0" '
                             f'data-duration="{self.dur:.3f}" data-track-index="{self.nt()}" data-volume="1"></audio>')

    def nt(self):
        self.track += 1
        return self.track

    def asset(self, path):
        """register a file and return its path inside the comp"""
        path = Path(path).resolve()
        if path not in self.files:
            self.files[path] = f'assets/{len(self.files):02d}_{re.sub(r"[^A-Za-z0-9._-]", "_", path.name)}'
        return self.files[path]

    def video(self, path, style, vid, start=0, media_start=0, dur=None, cls=''):
        dur = self.dur - start if dur is None else dur
        return (f'<video id="{vid}" class="{cls}" src="{self.asset(path)}" muted playsinline data-start="{start:.3f}" '
                f'data-media-start="{media_start:.3f}" data-duration="{dur:.3f}" data-track-index="{self.nt()}" '
                f'style="{style}"></video>')

    def write(self):
        gsap = KIT / 'vendor' / 'gsap.min.js'
        if not gsap.exists():
            sys.exit(f'missing {gsap}: run kit/setup.sh once')
        if self.dir.exists():
            shutil.rmtree(self.dir)
        (self.dir / 'assets').mkdir(parents=True)
        shutil.copytree(KIT / 'fonts', self.dir / 'fonts')
        (self.dir / 'vendor').mkdir()
        shutil.copy(gsap, self.dir / 'vendor' / 'gsap.min.js')
        for src, rel in self.files.items():
            try:
                os.link(src, self.dir / rel)
            except OSError:
                shutil.copy(src, self.dir / rel)
        (self.dir / 'hyperframes.json').write_text(json.dumps({'$schema': 'https://hyperframes.heygen.com/schema/hyperframes.json',
                                                               'media': {'autoProxy': True}}, indent=2))
        (self.dir / 'index.html').write_text(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>{''.join(self.css)}</style></head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{self.dur:.3f}" data-fps="{FPS}" data-width="{W}" data-height="{H}">
{chr(10).join(self.body)}
<script src="vendor/gsap.min.js"></script>
<script>
(function () {{
const gsap = window.gsap;
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(self.js)}
tl.set({{}}, {{}}, {self.dur:.3f});
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
}})();
</script>
</div>
</body>
</html>''')

    def render(self, out):
        out = Path(out)
        if out.exists():
            out.unlink()
        print(f'rendering {out.name} ...', flush=True)
        r = subprocess.run(['npx', '--yes', HYPERFRAMES, 'render', str(self.dir), '-o', str(out), '--fps', str(FPS), '-q', 'high'],
                           capture_output=True, text=True)
        if not out.exists():
            sys.exit(f'render failed:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}')
        print('\n'.join(l for l in r.stdout.splitlines() if 'rendered in' in l or '✗' in l))


# ---------------------------------------------------------------- captions
def chunks(ws, maxc=22, maxw=4):
    """greedy one-line chunks: at most maxc characters and maxw words, broken at punctuation"""
    out, cur = [], []
    for w, t, *_ in ws:
        b = bare(w)
        if not b:
            continue
        if cur and (len(' '.join(x for x, _ in cur + [(b, 0)])) > maxc or len(cur) >= maxw):
            out.append(cur)
            cur = []
        cur.append((b, t))
        if w.endswith(('.', ',', '?', '!')) and len(cur) >= 2:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def karaoke(c, ws, top, cid='kc', maxc=22, size=56, plate=True, font="700 {s}px/1 'Inter'", grey='#6f6f6f',
            white='#fff', upper=False, lead=0.04, end=None):
    """Clean Karaoke: one line, lowercase, no punctuation, each word turns from grey to white as it is said"""
    end = c.dur if end is None else end
    cs = chunks(ws, maxc)
    c.css.append(f'''.{cid}{{position:absolute;left:0;width:1080px;top:{top}px;text-align:center;visibility:hidden}}
.{cid} span.p{{display:inline-block;padding:14px 24px 16px;border-radius:16px;{'background:rgba(0,0,0,.88);' if plate else ''}
font:{font.format(s=size)};letter-spacing:-.01em;white-space:nowrap;{'text-transform:uppercase;' if upper else ''}}}
.{cid} span.w{{color:{grey}}}''')
    for i, ch in enumerate(cs):
        t0 = max(0, ch[0][1] - lead)
        t1 = cs[i + 1][0][1] - lead if i + 1 < len(cs) else end
        spans = ' '.join(f'<span class="w" id="{cid}{i}_{j}">{html.escape(w)}</span>' for j, (w, _) in enumerate(ch))
        c.body.append(f'<div class="{cid}" id="{cid}{i}"><span class="p">{spans}</span></div>')
        c.js.append(f'tl.set("#{cid}{i}",{{visibility:"visible"}},{t0:.3f});tl.set("#{cid}{i}",{{visibility:"hidden"}},{t1:.3f});')
        for j, (w, t) in enumerate(ch):
            c.js.append(f'tl.set("#{cid}{i}_{j}",{{color:"{white}"}},{max(t0, t - 0.02):.3f});')


def groups(ws, maxw=3, maxc=15):
    """short caption groups (TikTok style): 1-3 words, at most maxc characters, broken at punctuation"""
    out, cur = [], []
    for w, t, *_ in ws:
        b = bare(w)
        if not b:
            continue
        if cur and (len(cur) >= maxw or len(' '.join(x for x, _ in cur + [(b, 0)])) > maxc):
            out.append(cur)
            cur = []
        cur.append((b, t))
        if w.endswith(('.', ',', '?', '!')):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def word_caps(c, ws, cid, css, maxw=3, maxc=15, keys=(), key_tag='span class="k"', pop=None, lead=0.04, karaoke_dim=None):
    """one div per caption group, shown from its first word to the next group. keys = words to mark (class k or <em>).
    pop = (from_scale, duration) for a small pop on each group. karaoke_dim = colour for words not said yet."""
    keys = {bare(k) for k in keys}
    c.css.append(css)
    gs = groups(ws, maxw, maxc)
    close = key_tag.split()[0]
    for i, g in enumerate(gs):
        t0 = max(0, g[0][1] - lead)
        t1 = gs[i + 1][0][1] - lead if i + 1 < len(gs) else c.dur
        parts = []
        for j, (w, t) in enumerate(g):
            txt = html.escape(w)
            if w in keys:
                txt = f'<{key_tag}>{txt}</{close}>'
            parts.append(f'<span class="w" id="{cid}{i}_{j}">{txt}</span>' if karaoke_dim else txt)
            if karaoke_dim:
                c.js.append(f'tl.set("#{cid}{i}_{j}",{{color:"#fff"}},{max(t0, t - 0.02):.3f});')
        c.body.append(f'<div class="{cid}" id="{cid}{i}">{" ".join(parts)}</div>')
        c.js.append(f'tl.set("#{cid}{i}",{{visibility:"visible"}},{t0:.3f});tl.set("#{cid}{i}",{{visibility:"hidden"}},{t1:.3f});')
        if pop:
            c.js.append(f'tl.fromTo("#{cid}{i}",{{scale:{pop[0]}}},{{scale:1,duration:{pop[1]},ease:"back.out(2)"}},{t0:.3f});')
    if karaoke_dim:
        c.css.append(f'.{cid} span.w{{color:{karaoke_dim}}}')


# ---------------------------------------------------------------- shared pieces
def cover_html(c, w, image=None, text='', cta='SWIPE →', cls='cover', extra=''):
    """a carousel-cover card, 4:5: photo, dark fade, big uppercase text (*word* turns yellow), small CTA"""
    s = w / 280
    bg = f'url({c.asset(image)}) center/cover' if image else 'linear-gradient(160deg,#2b2b2e,#111)'
    t = rich(text).replace('<em>', '<span style="color:#FFD400">').replace('</em>', '</span>')
    return f'''<div class="{cls}" {extra} style="width:{w}px;height:{w*1.25:.0f}px;position:relative;overflow:hidden;border-radius:{10*s:.0f}px;
background:#222 {bg}">
<div class="a" style="inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 30%,rgba(0,0,0,.72) 100%)"></div>
<div class="a" style="left:{14*s:.0f}px;right:{14*s:.0f}px;bottom:{38*s:.0f}px;font:{29*s:.1f}px/0.98 'Archivo Black';color:#fff;
text-transform:uppercase;letter-spacing:-.01em;text-align:center;text-shadow:0 {2*s:.0f}px {8*s:.0f}px rgba(0,0,0,.45)">{t}</div>
<div class="a" style="left:0;right:0;bottom:{14*s:.0f}px;text-align:center;font:700 {10*s:.1f}px 'Inter';color:#fff;letter-spacing:.12em">{html.escape(cta)}</div>
</div>'''


def count_js(target_ids, to, at, dur=0.62, fmt='comma', prefix=''):
    """count a number up from 0 into one or more elements (fmt: comma | time | plain)"""
    if fmt == 'time':
        f = "Math.floor(s/60)+':'+String(s%60).padStart(2,'0')"
    elif fmt == 'comma':
        f = "s.toLocaleString('en-US')"
    else:
        f = 'String(s)'
    sets = ''.join(f"document.getElementById('{i}').textContent={json.dumps(prefix)}+{f};" for i in target_ids)
    v = 'cnt' + target_ids[0].replace('-', '_')
    return (f'const {v}={{v:0}};tl.to({v},{{v:{to},duration:{dur},ease:"power2.out",onUpdate:()=>{{const s=Math.round({v}.v);'
            f'{sets}}}}},{at:.3f});')


def parse_number(v):
    """"10,000" -> (10000, 'comma'); "4:12" -> (252, 'time'); "12" -> (12, 'plain'); otherwise None"""
    v = str(v).strip()
    if re.fullmatch(r'\d+:\d\d', v):
        m, s = v.split(':')
        return int(m) * 60 + int(s), 'time'
    if re.fullmatch(r'\d{1,3}(,\d{3})+', v):
        return int(v.replace(',', '')), 'comma'
    if re.fullmatch(r'\d+', v):
        return int(v), 'comma' if len(v) > 3 else 'plain'
    return None


# ---------------------------------------------------------------- checks
def frame(video, t, out):
    """one 9:16 frame with a ruler every 100 px (1080x1920 coordinates) to read where the eyes and chin are"""
    from PIL import Image, ImageDraw, ImageFont
    tmp = Path(out).with_suffix('.raw.png')
    run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', video, '-frames:v', '1', '-vf', FRAME_VF, tmp])
    im = Image.open(tmp).convert('RGB')
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.load_default(size=40)
    except TypeError:
        font = ImageFont.load_default()
    for y in range(100, H, 100):
        d.line((0, y, W if y % 500 == 0 else 70, y), fill=(255, 40, 40), width=3 if y % 500 else 4)
        d.text((80, y - 22), str(y), fill=(255, 40, 40), font=font, stroke_width=3, stroke_fill=(0, 0, 0))
    im.resize((540, 960)).save(out, quality=90)
    tmp.unlink()


def sheet(video, out, n=8):
    """contact sheet of a finished video; the parts Instagram covers are tinted red"""
    from PIL import Image, ImageDraw
    d = duration(video)
    tw, th = 270, 480
    im = Image.new('RGB', (tw * n, th + 30), 'black')
    dr = ImageDraw.Draw(im)
    tmp = Path(out).with_suffix('.f.png')
    for i in range(n):
        t = d * (i + 0.5) / n
        run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', video, '-frames:v', '1', '-vf', f'scale={tw}:{th}', tmp])
        f = Image.open(tmp).convert('RGBA')
        ov = Image.new('RGBA', f.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        k = tw / W
        for box in ((0, 0, tw, SAFE_TOP * k), (0, SAFE_BOTTOM * k, tw, th), (0, 0, SAFE_SIDE * k, th), (tw - SAFE_SIDE * k, 0, tw, th)):
            od.rectangle(box, fill=(255, 0, 0, 46))
        im.paste(Image.alpha_composite(f, ov).convert('RGB'), (i * tw, 30))
        dr.text((i * tw + 6, 8), f'{t:.2f}s', fill=(255, 220, 0))
    im.save(out, quality=88)
    tmp.unlink()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    a = sp.add_parser('words')
    a.add_argument('video')
    a.add_argument('--start', type=float, default=0)
    a.add_argument('--end', type=float)
    a.add_argument('--transcript')
    b = sp.add_parser('frame')
    b.add_argument('video')
    b.add_argument('t', type=float)
    b.add_argument('out')
    s = sp.add_parser('sheet')
    s.add_argument('video')
    s.add_argument('out')
    s.add_argument('n', type=int, nargs='?', default=8)
    x = ap.parse_args()
    if x.cmd == 'words':
        end = x.end or duration(x.video)
        ws = load_words(x.video, x.start, end, x.transcript)
        line = []
        for w, t, _ in ws:
            line.append(f'{w}@{t:.2f}')
            if w.endswith(('.', '?', '!')):
                print(' '.join(line))
                line = []
        if line:
            print(' '.join(line))
    elif x.cmd == 'frame':
        frame(x.video, x.t, x.out)
        print('wrote', x.out)
    else:
        sheet(x.video, x.out, x.n)
        print('wrote', x.out)


if __name__ == '__main__':
    main()
