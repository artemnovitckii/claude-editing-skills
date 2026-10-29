#!/usr/bin/env python3
"""storytelling: three simple image cards across the top, a black-box title and a small white subtitle under them,
all landing together, over one continuous take with simple TikTok-style captions.

    <kit>/.venv/bin/python build.py spec.json

Spec (see SKILL.md):
  video, start, end, out
  cards: [3 x {type: image | cover | stat | comments | text, ...}]
  title: ["I made this carousel", "in a few minutes"]     one black box per line
  subtitle: "and it's doing extremely well"
  zoom: 1.30                                              punch-in on the take (1 = none)
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, count_js, cover_html, parse_number, word_caps  # noqa: E402

DOTS = ['#f87171', '#60a5fa', '#fbbf24', '#4ade80', '#a78bfa']


def card(j, c, i, k, x):
    t = k.get('type', 'image')
    st = f'left:{x}px'
    if t == 'image':
        src = j.images(k.get('src'))[0]
        return f'<div class="sc" id="c{i}" style="{st}"><img src="{c.asset(src)}" style="width:296px;height:296px;object-fit:cover"></div>'
    if t == 'cover':
        img = (j.images(k.get('image')) or [None])[0]
        c.js.append(f'tl.fromTo("#c{i} .cover",{{y:0}},{{y:-60,duration:{c.dur - 0.1:.3f},ease:"none"}},0.1);')
        return f'<div class="sc" id="c{i}" style="{st}">{cover_html(c, 296, img, k.get("text", ""), k.get("cta", "SWIPE →"))}</div>'
    if t == 'stat':
        val = str(k.get('value', ''))
        num = parse_number(val)
        ring = float(k.get('ring', 0.75))
        if num:
            c.js.append(count_js([f'n{i}'], num[0], j.t(k.get('at'), 0.15), dur=float(k.get('count_for', 1.6)), fmt=num[1]))
        c.js.append(f'tl.to("#rg{i}",{{strokeDashoffset:{490 * (1 - ring):.0f},duration:{float(k.get("count_for", 1.6))},ease:"power1.out"}},{j.t(k.get("at"), 0.15):.3f});')
        return (f'<div class="sc" id="c{i}" style="{st}"><div class="lb">{html.escape(k.get("label", ""))}</div>'
                f'<svg width="180" height="180" viewBox="0 0 180 180"><circle cx="90" cy="90" r="78" fill="none" stroke="#eee" stroke-width="12"/>'
                f'<circle id="rg{i}" cx="90" cy="90" r="78" fill="none" stroke="#D97757" stroke-width="12" stroke-linecap="round" '
                f'stroke-dasharray="490" stroke-dashoffset="490" transform="rotate(-90 90 90)"/></svg>'
                f'<div class="n" id="n{i}">{"0" if num else html.escape(val)}</div><div class="u">{html.escape(k.get("unit", ""))}</div></div>')
    if t == 'comments':
        rows = ''.join(f'<div class="cr"><i style="background:{DOTS[q % len(DOTS)]}"></i><div><div class="h">{html.escape(h)} · 1m</div>'
                       f'<div class="t">{html.escape(tx)}</div></div></div>' for q, (h, tx) in enumerate(k.get('rows', [])[:4]))
        return f'<div class="sc cm" id="c{i}" style="{st}"><div class="hd">{html.escape(k.get("title", "Comments"))}</div>{rows}</div>'
    if t == 'text':
        return (f'<div class="sc tx" id="c{i}" style="{st}"><div class="big">{html.escape(k.get("big", ""))}</div>'
                f'<div class="sm">{html.escape(k.get("small", ""))}</div></div>')
    sys.exit(f'card type {t} is not one of image, cover, stat, comments, text')


def main(spec):
    j = Job(spec, 'storytelling')
    c = Comp(j)
    S = float(j.get('zoom', 1.30))
    cap = j.get('caption_top', 1385)
    c.css.append(f'''
.sc{{position:absolute;top:212px;width:296px;height:296px;border-radius:28px;background:#fff;overflow:hidden;box-shadow:0 20px 44px rgba(0,0,0,.38)}}
.sc .lb{{position:absolute;left:0;right:0;top:40px;text-align:center;font:700 26px 'Inter';color:#8a8a8a;letter-spacing:.04em}}
.sc svg{{position:absolute;left:58px;top:82px}}
.sc .n{{position:absolute;left:0;right:0;top:132px;text-align:center;font:800 56px/1 'Inter';color:#111;letter-spacing:-.02em}}
.sc .u{{position:absolute;left:0;right:0;top:192px;text-align:center;font:600 22px 'Inter';color:#8a8a8a}}
.cm .hd{{padding:22px 22px 8px;text-align:center;font:700 24px 'Inter';color:#111}}
.cr{{display:flex;align-items:center;gap:12px;padding:8px 18px}}
.cr i{{width:40px;height:40px;border-radius:50%;flex:none}}
.cr .h{{font:500 16px/1.1 'Inter';color:#8a8a8a}}
.cr .t{{font:800 23px/1.1 'Inter';color:#111;letter-spacing:.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px}}
.tx{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:20px;text-align:center}}
.tx .big{{font:800 84px/1 'Inter';color:#111;letter-spacing:-.03em}}
.tx .sm{{font:600 24px/1.2 'Inter';color:#8a8a8a}}
.tb{{position:absolute;left:0;width:1080px;text-align:center}}
.tb span{{display:inline-block;background:#000;color:#fff;font:800 72px/1 'Inter';letter-spacing:-.03em;padding:12px 26px 16px;border-radius:16px}}
#sub span{{background:#fff;color:#111;font:700 42px/1 'Inter';letter-spacing:-.01em;padding:9px 18px 12px;border-radius:10px}}
.tk{{position:absolute;left:0;width:1080px;top:{cap}px;text-align:center;visibility:hidden;font:700 74px/1.05 'TikTok Sans';color:#fff;
  letter-spacing:-.01em;-webkit-text-stroke:8px #000;paint-order:stroke fill;text-shadow:0 5px 12px rgba(0,0,0,.35)}}
''')
    c.body.append(c.video(j.clip, f'position:absolute;left:{-(1080*S-1080)/2:.0f}px;top:0;width:{1080*S:.0f}px;height:{1920*S:.0f}px', 'bg'))
    cards = (j.get('cards') or [])[:3]
    if len(cards) != 3:
        sys.exit('storytelling needs exactly 3 cards')
    ids = []
    for i, k in enumerate(cards):
        c.body.append(card(j, c, i, k, [78, 392, 706][i]))
        ids.append(f'#c{i}')
    y = 528
    for n, line in enumerate(j.get('title') or []):
        c.body.append(f'<div class="tb" id="t{n}" style="top:{y}px"><span>{html.escape(line)}</span></div>')
        ids.append(f'#t{n}')
        y += 100
    if j.get('subtitle'):
        c.body.append(f'<div class="tb" id="sub" style="top:{y + 12}px"><span>{html.escape(j.get("subtitle"))}</span></div>')
        ids.append('#sub')
    # everything lands together (one beat, not one at a time)
    c.js.insert(0, f'tl.fromTo({ids},{{scale:.7,autoAlpha:0,y:24}},{{scale:1,autoAlpha:1,y:0,duration:.32,ease:"back.out(1.8)"}},0.02);'.replace("'", '"'))
    word_caps(c, j.words, 'tk', '', maxw=3, maxc=15)
    j.finish(c)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
