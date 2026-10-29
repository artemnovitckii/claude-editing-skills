#!/usr/bin/env python3
"""behind-the-person: a panel of graphics BEHIND the speaker (the speaker is cut out and sits on top of it),
big words on the chest as they are said, and a profile card that counts up.

    <kit>/.venv/bin/python build.py spec.json

Spec (see SKILL.md for every field):
  video, start, end, out
  panel: {type: grid | bars | image, ...}          the graphic behind the head
  chest: [{text, at}, ...]                          big words; "{count}" in a text counts up to card.count
  card:  {avatar, name, label, count, at, count_at, button, pressed, press_at}   optional
"""
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, count_js, parse_number  # noqa: E402

CAR_ICON = ('<svg class="cico" viewBox="0 0 24 24" width="30" height="30"><rect x="7" y="3" width="14" height="14" rx="2.5" '
            'fill="none" stroke="#fff" stroke-width="2"/><path d="M4 7v11.5A2.5 2.5 0 0 0 6.5 21H17" fill="none" '
            'stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>')


def panel_grid(j, c, p):
    imgs = j.images(p.get('images'))
    if not imgs:
        sys.exit('panel.images is empty')
    tabs = p.get('tabs', ['Posts', 'Reels', 'Tagged'])
    hl = p.get('highlight') or {}
    hi = int(hl.get('index', 0))
    cells = []
    for i in range(12):
        src = imgs[i % len(imgs)]
        strip = [src] + (j.images(hl.get('slides')) if i == hi and hl else [])
        inner = ''.join(f'<img src="{c.asset(s)}">' for s in strip)
        cells.append(f'<div class="cell" id="cell{i}"><div class="strip">{inner}</div>{CAR_ICON if len(strip) > 1 or p.get("icons", True) else ""}</div>')
    head = ''.join(f'<b>{html.escape(t)}</b>' if k == 0 else f'<span>{html.escape(t)}</span>' for k, t in enumerate(tabs))
    label = hl.get('label')
    c.body.append(f'''<div id="ig" class="a"><div class="hd"><div class="igl"></div>{head}</div>
<div id="grid">{''.join(cells)}{'<div id="hl" class="hid"></div>' if hl else ''}{f'<div id="hlc" class="hid">{html.escape(label)}</div>' if label else ''}</div></div>''')
    c.js.append(f'tl.fromTo("#grid",{{y:0}},{{y:{-int(p.get("scroll", 150))},duration:{c.dur:.3f},ease:"none"}},0);')
    if hl:
        col, row = hi % 3, hi // 3
        x, y = col * 287 - 5, row * 357 - 5
        ta = j.t(hl.get('at'), 0.6)
        c.js.append(f'''tl.set("#hl",{{left:{x},top:{y},width:288,height:358,visibility:"visible"}},{ta:.3f});
tl.fromTo("#hl",{{scale:1.15,autoAlpha:0}},{{scale:1,autoAlpha:1,duration:.22,ease:"power2.out"}},{ta:.3f});''')
        swipes = hl.get('swipe_at') or [ta + 0.33 + k * 0.6 for k in range(len(j.images(hl.get('slides'))))]
        for k, s in enumerate(swipes[:len(j.images(hl.get('slides')))]):
            c.js.append(f'tl.to("#cell{hi} .strip",{{x:{-278 * (k + 1)},duration:.32,ease:"power2.inOut"}},{j.t(s):.3f});')
        if label:
            tl_ = j.t(hl.get('label_at'), ta + 1.0)
            c.js.append(f'''tl.set("#hlc",{{left:{x + 21},top:{y + 305},visibility:"visible"}},{tl_:.3f});
tl.fromTo("#hlc",{{scale:.6,autoAlpha:0}},{{scale:1,autoAlpha:1,duration:.22,ease:"back.out(2)"}},{tl_:.3f});''')


def panel_bars(j, c, p):
    bars = p.get('bars') or []
    if not bars:
        sys.exit('panel.bars is empty')
    top = max(float(b['value']) for b in bars) or 1
    n = len(bars)
    bw = min(150, (780 - (n - 1) * 26) / n)
    x0 = (900 - (n * bw + (n - 1) * 26)) / 2
    acc = p.get('color', '#4ade80')
    hi = p.get('highlight', n - 1)
    items = []
    for i, b in enumerate(bars):
        h = 520 * float(b['value']) / top
        x = x0 + i * (bw + 26)
        col = acc if i == hi else 'rgba(255,255,255,.22)'
        items.append(f'<div class="bar" id="bar{i}" style="left:{x:.0f}px;width:{bw:.0f}px;height:{h:.0f}px;background:{col}"></div>'
                     f'<div class="bv" id="bv{i}" style="left:{x - 20:.0f}px;width:{bw + 40:.0f}px;bottom:{170 + h + 12:.0f}px">{html.escape(str(b.get("show", b["value"])))}</div>'
                     f'<div class="bl" style="left:{x - 20:.0f}px;width:{bw + 40:.0f}px">{html.escape(str(b.get("label", "")))}</div>')
    c.css.append('''.bar{position:absolute;bottom:170px;border-radius:14px 14px 4px 4px;transform-origin:50% 100%}
.bv{position:absolute;text-align:center;font:800 40px 'Inter';color:#fff}
.bl{position:absolute;bottom:110px;text-align:center;font:600 28px 'Inter';color:#9a9a9a}
#ig .ttl{position:absolute;left:44px;top:40px;font:800 46px/1.1 'Inter';color:#fff;letter-spacing:-.02em}''')
    c.body.append(f'<div id="ig" class="a"><div class="ttl">{html.escape(p.get("title", ""))}</div>{"".join(items)}</div>')
    t0 = j.t(p.get('at'), 0.3)
    for i in range(n):
        c.js.append(f'tl.fromTo("#bar{i}",{{scaleY:0}},{{scaleY:1,duration:.5,ease:"power3.out"}},{t0 + i * 0.12:.3f});'
                    f'tl.fromTo("#bv{i}",{{autoAlpha:0,y:20}},{{autoAlpha:1,y:0,duration:.3}},{t0 + i * 0.12 + 0.3:.3f});')


def panel_image(j, c, p):
    src = j.images(p.get('src'))[0]
    c.css.append('#ig img.shot{position:absolute;left:0;top:0;width:900px;height:auto}')
    c.body.append(f'<div id="ig" class="a"><img class="shot" id="shot" src="{c.asset(src)}"></div>')
    c.js.append(f'tl.fromTo("#shot",{{y:0}},{{y:{-int(p.get("scroll", 200))},duration:{c.dur:.3f},ease:"none"}},0);')


def main(spec):
    j = Job(spec, 'behind-the-person')
    c = Comp(j)
    p = j.get('panel') or {}
    top, ph = j.get('panel_top', 150), j.get('panel_height', 870)
    chest_top, card_top = j.get('chest_top', 1105), j.get('card_top', 1235)
    c.css.append(f'''
#ig{{left:90px;top:{top}px;width:900px;height:{ph}px;border-radius:44px;background:#0d0d0e;overflow:hidden;
  box-shadow:0 40px 90px rgba(0,0,0,.55),inset 0 0 0 1.5px rgba(255,255,255,.09)}}
#ig .hd{{position:absolute;left:0;top:0;width:900px;height:112px;display:flex;align-items:center;gap:46px;padding:0 40px;
  font:600 38px 'Inter';color:#8d8d8d;z-index:2;background:#0d0d0e}}
#ig .hd b{{color:#fff;font-weight:700;position:relative}}
#ig .hd b:after{{content:'';position:absolute;left:0;right:0;bottom:-30px;height:4px;background:#fff;border-radius:2px}}
.igl{{width:54px;height:54px;border-radius:16px;background:radial-gradient(circle at 30% 107%,#fdf497 0%,#fd5949 45%,#d6249f 60%,#285AEB 90%);
  position:relative;flex:none}}
.igl:before{{content:'';position:absolute;inset:11px;border:4.5px solid #fff;border-radius:12px}}
.igl:after{{content:'';position:absolute;left:19px;top:19px;width:16px;height:16px;border:4.5px solid #fff;border-radius:50%;box-sizing:border-box}}
#grid{{position:absolute;left:24px;top:124px;width:852px;display:grid;grid-template-columns:repeat(3,278px);gap:9px}}
.cell{{position:relative;width:278px;height:348px;overflow:hidden;border-radius:6px;background:#222}}
.cell .strip{{display:flex;height:348px}}
.cell img{{width:278px;height:348px;object-fit:cover;flex:none}}
.cell .cico{{position:absolute;right:12px;top:12px;filter:drop-shadow(0 1px 3px rgba(0,0,0,.5))}}
#hl{{position:absolute;border:5px solid #fff;border-radius:10px;box-shadow:0 0 0 3px rgba(0,0,0,.4),0 0 40px rgba(255,255,255,.35)}}
#hlc{{position:absolute;padding:6px 14px;border-radius:30px;background:#fff;color:#111;font:800 26px 'Inter'}}
.big{{position:absolute;left:0;width:1080px;top:{chest_top}px;text-align:center;font:800 84px/1 'Inter';color:#fff;letter-spacing:-.02em;
  text-shadow:0 4px 24px rgba(0,0,0,.55);visibility:hidden}}
#pc{{left:170px;top:{card_top}px;width:740px;height:150px;border-radius:30px;background:rgba(16,16,18,.9);
  box-shadow:0 20px 50px rgba(0,0,0,.45),inset 0 0 0 1.5px rgba(255,255,255,.1);display:flex;align-items:center;gap:24px;padding:0 26px;visibility:hidden}}
#pc img{{width:100px;height:100px;border-radius:50%;object-fit:cover}}
#pc .nm{{font:700 38px/1.1 'Inter';color:#fff}}
#pc .sb{{font:500 27px/1.3 'Inter';color:#9a9a9a}}
#pc .sb b{{color:#4ade80;font-weight:700}}
#pc .fb{{margin-left:auto;padding:16px 30px;border-radius:40px;background:#0095f6;color:#fff;font:700 30px 'Inter'}}
''')
    c.body.append(c.video(j.clip, 'position:absolute;left:0;top:0;width:1080px;height:1920px', 'bg'))
    {'grid': panel_grid, 'bars': panel_bars, 'image': panel_image}[p.get('type', 'grid')](j, c, p)
    c.js.append('tl.fromTo("#ig",{y:60,autoAlpha:0,scale:.96},{y:0,autoAlpha:1,scale:1,duration:.42,ease:"power3.out"},0);')
    c.body.append(c.video(j.cutout(), 'position:absolute;left:0;top:0;width:1080px;height:1920px', 'cut'))

    card = j.get('card')
    count = parse_number(card.get('count')) if card and card.get('count') is not None else None
    count_ids = []
    chest = j.get('chest') or []
    times = [j.t(w.get('at')) for w in chest]
    for i, w in enumerate(chest):
        a = times[i]
        b = times[i + 1] if i + 1 < len(chest) else c.dur
        txt = html.escape(w['text'])
        if '{count}' in w['text']:
            txt = txt.replace('{count}', f'<span id="cnt{i}">0</span>')
            count_ids.append((f'cnt{i}', a, b))
        c.body.append(f'<div class="big" id="bw{i}">{txt}</div>')
        c.js.append(f'tl.set("#bw{i}",{{visibility:"visible"}},{a:.3f});tl.set("#bw{i}",{{visibility:"hidden"}},{b:.3f});'
                    f'tl.fromTo("#bw{i}",{{scale:.86,y:10}},{{scale:1,y:0,duration:.16,ease:"back.out(2)"}},{a:.3f});')
    if card:
        lab = html.escape(card.get('label', 'new followers'))
        num = '<b id="pcn">+0</b> ' if count else ''
        c.body.append(f'<div id="pc" class="a"><img src="{c.asset(j.images(card["avatar"])[0])}"><div><div class="nm">{html.escape(card["name"])}</div>'
                      f'<div class="sb">{num}{lab}</div></div><div class="fb" id="fb">{html.escape(card.get("button", "Follow"))}</div></div>')
        ca = j.t(card.get('at'), 0.4)
        c.js.append(f'tl.fromTo("#pc",{{autoAlpha:0,y:30,scale:.94}},{{autoAlpha:1,y:0,scale:1,duration:.3,ease:"back.out(1.6)"}},{ca:.3f});')
        if card.get('pressed'):
            pa = j.t(card.get('press_at'), c.dur - 0.8)
            c.js.append(f'tl.set("#fb",{{textContent:{json.dumps(card["pressed"])},background:"#2c2c2e"}},{pa:.3f});'
                        f'tl.fromTo("#fb",{{scale:.9}},{{scale:1,duration:.18,ease:"back.out(3)"}},{pa:.3f});')
    if count:
        to, fmt = count
        at = j.t(card.get('count_at'), count_ids[0][1] if count_ids else 1.0)
        ids = [i for i, _, _ in count_ids] + ['pcn']
        c.js.append(count_js(ids[:-1], to, at, fmt=fmt) if count_ids else '')
        c.js.append(count_js(['pcn'], to, at, fmt=fmt, prefix='+'))
    j.finish(c)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
