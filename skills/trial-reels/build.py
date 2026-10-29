#!/usr/bin/env python3
"""trial-reels: the same clip as 3 visually distinct reels, to post as Instagram trial reels and see which look wins.

    <kit>/.venv/bin/python build.py spec.json        -> <out>-1.mp4, <out>-2.mp4, <out>-3.mp4

  1  Title + karaoke:  big yellow title at the top, Clean Karaoke captions (grey to white, one line)
  2  Post header:      a white post card (avatar, name, the hook as a headline), punch-in zooms, bold uppercase captions
  3  Pixel frame:      dark grid backdrop, a big pixel-font stat, the clip in an orange frame, pixel captions

Spec (see SKILL.md):
  video, start, end, out
  v1: {title: ["carousels are an", "*instagram*", "*cheat code*"]}           *line* = bigger
  v2: {avatar, name, sub, headline, keys: [...], punches: [1.16, "views"]}
  v3: {stat: "2×", line: "the views of reels", pulse_at: "twice"}
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, bare, karaoke, rich, word_caps  # noqa: E402

FULL = 'position:absolute;left:0;top:0;width:1080px;height:1920px'


def v1(j, s):
    c = Comp(j, 'v1')
    c.css.append('''
#yt{left:0;width:1080px;top:238px;text-align:center;font:900 84px/1.02 'TikTok Sans','Archivo Black';color:#FCF000;
  text-shadow:0 5px 0 rgba(0,0,0,.55),0 0 18px rgba(0,0,0,.4);text-transform:uppercase;letter-spacing:-.01em}
#yt em{font-style:normal;font-size:118px}
''')
    c.body.append(c.video(j.clip, FULL, 'bg'))
    c.body.append(f'<div id="yt" class="a">{"<br>".join(rich(l) for l in s.get("title", []))}</div>')
    karaoke(c, j.words, s.get('caption_top', 1400), 'kc')
    c.js.append('tl.fromTo("#yt",{scale:.8,autoAlpha:0},{scale:1,autoAlpha:1,duration:.25,ease:"back.out(2)"},0);')
    return c


def v2(j, s):
    c = Comp(j, 'v2')
    c.css.append(f'''
#vw{{left:0;top:0;width:1080px;height:1920px;transform-origin:540px 820px}}
#hd{{left:110px;top:236px;width:860px;padding:30px 36px;border-radius:30px;background:#fff;box-shadow:0 16px 40px rgba(0,0,0,.35)}}
#hd .u{{display:flex;align-items:center;gap:16px;margin-bottom:16px}}
#hd .u img{{width:64px;height:64px;border-radius:50%;object-fit:cover}}
#hd .u b{{font:800 30px/1.1 'Inter';color:#111}}#hd .u span{{font:500 25px 'Inter';color:#777;display:block}}
#hd .q{{font:700 50px/1.14 'Inter';color:#111;letter-spacing:-.02em}}
.hz{{position:absolute;left:0;width:1080px;top:{s.get("caption_top", 1260)}px;text-align:center;visibility:hidden;font:900 86px/1 'Archivo Black';color:#fff;
  text-transform:uppercase;letter-spacing:-.01em;-webkit-text-stroke:6px #000;paint-order:stroke fill;text-shadow:0 8px 0 rgba(0,0,0,.5)}}
.hz .k{{color:#FFE14D}}
''')
    c.body.append('<div id="vw" class="a">' + c.video(j.clip, FULL, 'bg') + '</div>')
    av = j.images(s['avatar'])[0] if s.get('avatar') else None
    img = f'<img src="{c.asset(av)}">' if av else ''
    c.body.append(f'<div id="hd" class="a"><div class="u">{img}<div><b>{html.escape(s.get("name", ""))}</b>'
                  f'<span>{html.escape(s.get("sub", ""))}</span></div></div><div class="q">{html.escape(s.get("headline", ""))}</div></div>')
    keys = s.get('keys', [])
    word_caps(c, j.words, 'hz', '', maxw=2, maxc=18, keys=keys, pop=(1.25, 0.12))
    punches = s.get('punches')
    if punches is None:      # default: punch in on the first key words, at least 1.5 s apart
        kb, punches, last = {bare(k) for k in keys}, [], -9
        for w, t, _ in j.words:
            if bare(w) in kb and t - last >= 1.5 and t < c.dur - 0.6:
                punches.append(t)
                last = t
            if len(punches) == 3:
                break
    c.js.append('tl.fromTo("#hd",{y:-40,autoAlpha:0},{y:0,autoAlpha:1,duration:.3,ease:"back.out(1.6)"},0);'
                'tl.set("#vw",{scale:1.16},0);')
    # a slow drift in, then each punch: snap in on the word, ease back out (one tween at a time, never overlapping)
    free = 0.0
    for p in sorted(j.t(p) for p in punches):
        if p < free + 0.3 or p > c.dur - 0.3:
            continue
        back = min(c.dur - 0.5, p + 0.8)
        c.js.append(f'tl.to("#vw",{{scale:1.22,duration:{p - free - 0.02:.3f},ease:"none"}},{free:.3f});'
                    f'tl.to("#vw",{{scale:1.33,duration:.12,ease:"power2.out"}},{p:.3f});'
                    f'tl.to("#vw",{{scale:1.2,duration:.5,ease:"power2.inOut"}},{back:.3f});')
        free = back + 0.5
    return c


def v3(j, s):
    c = Comp(j, 'v3')
    SC = 0.78
    VW, VH = 1080 * SC, 1920 * SC
    c.css.append(f'''
#bk{{left:0;top:0;width:1080px;height:1920px;background:#121110}}
#bk:before{{content:'';position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.035) 2px,transparent 2px),
  linear-gradient(90deg,rgba(255,255,255,.035) 2px,transparent 2px);background-size:40px 40px}}
#fr{{left:{(1080-VW)/2:.0f}px;top:410px;width:{VW:.0f}px;height:{1898-410}px;border-radius:40px;overflow:hidden;
  box-shadow:0 0 0 3px #D97757,0 30px 80px rgba(0,0,0,.6)}}
#px{{left:0;width:1080px;top:170px;text-align:center;font:700 190px/0.9 'Pixelify Sans';color:#FF8A4C;letter-spacing:.01em}}
#px small{{display:block;font:500 52px/1.1 'Pixelify Sans';color:#f3efe8;margin-top:4px;letter-spacing:.02em}}
#tag{{left:{(1080-VW)/2+28:.0f}px;top:438px;padding:8px 16px;border-radius:10px;background:rgba(0,0,0,.6);font:500 30px 'Pixelify Sans';color:#FF8A4C}}
.pk span.p{{text-shadow:0 3px 10px rgba(0,0,0,.7)}}
''')
    c.body.append('<div id="bk" class="a"></div>')
    c.body.append('<div id="fr" class="a">' + c.video(j.clip, f'position:absolute;left:0;top:{(1898-410)-VH:.0f}px;width:{VW:.0f}px;height:{VH:.0f}px', 'bg') + '</div>')
    c.body.append(f'<div id="px" class="a"><span id="pxn">{html.escape(s.get("stat", ""))}</span><small>{html.escape(s.get("line", ""))}</small></div>')
    c.body.append('<div id="tag" class="a">● REC</div>')
    karaoke(c, j.words, s.get('caption_top', 1330), 'pk', maxc=20, size=54, plate=False, font="500 {s}px/1 'Pixelify Sans'",
            grey='rgba(255,255,255,.35)', white='#fff')
    blinks = max(1, int(c.dur / 0.25))
    c.js.append(f'''tl.fromTo("#px",{{autoAlpha:0,y:-16}},{{autoAlpha:1,y:0,duration:.24,ease:"steps(4)"}},0);
tl.fromTo("#fr",{{y:60,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.35,ease:"power3.out"}},0);
tl.to("#tag",{{autoAlpha:.2,duration:.01,repeat:{blinks if blinks % 2 else blinks - 1},yoyo:true,repeatDelay:.24}},0);''')
    if s.get('pulse_at') is not None:
        c.js.append(f'tl.fromTo("#pxn",{{scale:1}},{{scale:1.18,duration:.1,yoyo:true,repeat:1,ease:"steps(2)"}},{j.t(s["pulse_at"]):.3f});')
    return c


def main(spec):
    j = Job(spec, 'trial-reels')
    outs = []
    for n, make in enumerate((v1, v2, v3), 1):
        s = j.get(f'v{n}') or {}
        out = j.out.with_name(f'{j.out.stem}-{n}.mp4')
        outs.append(j.finish(make(j, s), out))
    print('\nthree trial reels:\n' + '\n'.join(f'  {o}' for o in outs))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
