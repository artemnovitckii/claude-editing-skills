#!/usr/bin/env python3
"""split-screen: visuals in the top half, the speaker in the bottom half, captions on the seam between them.

    <kit>/.venv/bin/python build.py spec.json

Spec (see SKILL.md):
  video, start, end, out
  badge: "Step 1"   headline: "Find a *viral* carousel"      (*word* = orange italic)
  visual: {type: grid-pick | image | checklist, ...}       what explains the point, in a window on the top half
  video_top: -430                                           moves the speaker inside the bottom half (face in frame)
"""
import html
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, groups, rich  # noqa: E402

STAR = ('<svg width="40" height="40" viewBox="0 0 100 100"><g stroke="#fff" stroke-width="11" stroke-linecap="round">'
        + ''.join(f'<line x1="50" y1="50" x2="{50+42*math.cos(a*0.5236):.1f}" y2="{50+42*math.sin(a*0.5236):.1f}"/>' for a in range(12))
        + '</g></svg>')
CURSOR = ('<svg id="cur" class="a" viewBox="0 0 24 24"><path d="M5 2.5v17.2l4.6-4.3 2.9 6.6 3-1.3-2.9-6.5h6.3z" fill="#111" '
          'stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>')
LENS = ('<svg width="26" height="26" viewBox="0 0 24 24" style="margin-right:12px"><circle cx="10.5" cy="10.5" r="6.5" fill="none" '
        'stroke="#777" stroke-width="2.4"/><path d="M15.5 15.5l5 5" stroke="#777" stroke-width="2.4" stroke-linecap="round"/></svg>')


def window(inner, bar_text):
    return (f'<div id="win" class="a"><div class="bar"><div class="dot" style="background:#ff5f57"></div><div class="dot" style="background:#febc2e"></div>'
            f'<div class="dot" style="background:#28c840"></div><div class="sr">{LENS}{html.escape(bar_text)}</div></div>{inner}</div>')


def grid_pick(j, c, v):
    imgs = j.images(v.get('images'))
    if not imgs:
        sys.exit('visual.images is empty')
    n = min(16, max(8, len(imgs)))
    chips = v.get('chips') or []
    cells = ''.join(f'<div class="lc" id="lc{i}"><img src="{c.asset(imgs[i % len(imgs)])}">'
                    + (f'<div class="chip">{html.escape(chips[i % len(chips)])}</div>' if chips else '') + '</div>' for i in range(n))
    pick = int(v.get('pick', 5)) % n
    col, row = pick % 4, pick // 4
    px, py = 26 + col * 204, 100 + row * 252
    pick_at = j.t(v.get('pick_at'), min(c.dur * 0.6, 3.36))
    move_at = max(0.2, pick_at - 0.66)
    scroll = int(v.get('scroll', 150 if row >= 1 else 0))
    c.body.append(window(f'<div id="lib">{cells}</div><div id="pick" class="hid"></div>', v.get('search', 'search')))
    c.js.append(f'''tl.fromTo("#lib",{{y:0}},{{y:{-scroll},duration:{move_at:.3f},ease:"power1.inOut"}},0);
tl.set("#cur",{{x:900,y:1000}},0);
tl.to("#cur",{{x:{110+px+120},y:{410+py-scroll+130},duration:.55,ease:"power2.inOut"}},{move_at:.3f});
tl.to("#cur",{{scale:.82,duration:.07,yoyo:true,repeat:1}},{pick_at-0.08:.3f});
tl.to(".lc:not(#lc{pick})",{{opacity:.35,duration:.25}},{pick_at:.3f});
tl.to("#lc{pick}",{{scale:1.1,duration:.25,ease:"back.out(2)",zIndex:4}},{pick_at:.3f});
tl.set("#pick",{{left:{px-11},top:{py-scroll-11},width:212,height:260,visibility:"visible"}},{pick_at:.3f});
tl.fromTo("#pick",{{autoAlpha:0}},{{autoAlpha:1,duration:.15}},{pick_at:.3f});''')
    if chips:
        c.js.append(f'tl.fromTo(".chip",{{scale:0,autoAlpha:0}},{{scale:1,autoAlpha:1,duration:.2,stagger:.035,ease:"back.out(2.5)"}},{j.t(v.get("chips_at"), 0.6):.3f});')
    if v.get('button'):
        ba = j.t(v.get('button_at'), pick_at + 0.6)
        ca = j.t(v.get('click_at'), ba + 0.45)
        c.body.append(f'<div id="btn" class="a hid">{html.escape(v["button"])}</div>')
        c.js.append(f'''tl.set("#btn",{{visibility:"visible"}},{ba:.3f});
tl.fromTo("#btn",{{y:20,autoAlpha:0,scale:.9}},{{y:0,autoAlpha:1,scale:1,duration:.24,ease:"back.out(2)"}},{ba:.3f});
tl.to("#cur",{{x:640,y:850,duration:.32,ease:"power2.inOut"}},{ba+0.05:.3f});
tl.to("#cur",{{scale:.82,duration:.07,yoyo:true,repeat:1}},{ca:.3f});
tl.to("#btn",{{background:"#D97757",scale:.95,duration:.1,yoyo:true,repeat:1}},{ca:.3f});''')
        fan = j.images(v.get('fan'))[:3]
        fa = j.t(v.get('fan_at'), ca + 0.12)
        for k, s in enumerate(fan):
            c.body.append(f'<div class="sl hid a" id="sl{k}"><img src="{c.asset(s)}"></div>')
            c.js.append(f'tl.set("#sl{k}",{{left:{110+px},top:{410+py-scroll},visibility:"visible",zIndex:5}},{fa:.3f});'
                        f'tl.fromTo("#sl{k}",{{x:0,y:0,rotation:0,autoAlpha:0}},{{x:{434+k*150-col*204},y:{42+scroll-row*252+k*40},'
                        f'rotation:{-8+k*8},autoAlpha:1,duration:.3,ease:"power3.out"}},{fa+k*0.05:.3f});')


def image(j, c, v):
    src = j.images(v.get('src'))[0]
    c.css.append('#win img.shot{position:absolute;left:0;top:78px;width:860px;height:auto}')
    c.body.append(window(f'<img class="shot" id="shot" src="{c.asset(src)}">', v.get('bar', '')))
    c.js.append(f'tl.fromTo("#shot",{{y:0}},{{y:{-int(v.get("scroll", 120))},duration:{c.dur:.3f},ease:"power1.inOut"}},0);'
                'gsap.set("#cur",{autoAlpha:0});')


def checklist(j, c, v):
    items = v.get('items') or []
    rows = ''.join(f'<div class="ck" id="ck{i}"><div class="bx"><svg viewBox="0 0 24 24" width="34" height="34"><path d="M5 12.5l4.5 4.5L19 7.5" '
                   f'fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></svg></div>'
                   f'<span>{rich(it["text"])}</span></div>' for i, it in enumerate(items))
    c.css.append('''#ckl{position:absolute;left:40px;top:110px;right:40px}
.ck{display:flex;align-items:center;gap:22px;height:96px;font:600 40px/1.1 'Inter';color:#1d1b18;letter-spacing:-.01em}
.ck em{font:italic 400 48px 'Instrument Serif';color:#C15F3C}
.ck .bx{width:58px;height:58px;border-radius:16px;border:4px solid #d8d2c8;display:grid;place-items:center;flex:none}
.ck .bx svg{opacity:0}''')
    c.body.append(window(f'<div id="ckl">{rows}</div>', v.get('bar', 'checklist')))
    c.js.append('gsap.set("#cur",{autoAlpha:0});')
    for i, it in enumerate(items):
        t = j.t(it.get('at'), 0.4 + i * 0.6)
        c.js.append(f'tl.fromTo("#ck{i}",{{x:-30,autoAlpha:0}},{{x:0,autoAlpha:1,duration:.3,ease:"power3.out"}},{max(0, t-0.35):.3f});'
                    f'tl.to("#ck{i} .bx",{{background:"#D97757",borderColor:"#D97757",duration:.15}},{t:.3f});'
                    f'tl.to("#ck{i} .bx svg",{{opacity:1,duration:.1}},{t:.3f});'
                    f'tl.fromTo("#ck{i} .bx",{{scale:1.25}},{{scale:1,duration:.25,ease:"back.out(3)"}},{t:.3f});')


def main(spec):
    j = Job(spec, 'split-screen')
    c = Comp(j)
    cap_top = j.get('caption_top', 918)
    c.css.append(f'''
#top{{left:0;top:0;width:1080px;height:960px;overflow:hidden;background:#F4F1EA}}
#top:before{{content:'';position:absolute;inset:0;background-image:radial-gradient(rgba(0,0,0,.08) 1.6px,transparent 1.7px);background-size:36px 36px}}
#badge{{left:0;width:1080px;top:206px;text-align:center}}
#badge span{{display:inline-flex;align-items:center;gap:12px;padding:12px 26px 12px 20px;border-radius:16px;background:#D97757;color:#fff;
  font:500 44px/1 'Instrument Serif';box-shadow:0 10px 24px rgba(217,119,87,.35)}}
#h1{{left:0;width:1080px;top:276px;text-align:center;font:400 96px/1 'Instrument Serif';color:#1d1b18;letter-spacing:-.01em}}
#h1 em{{font-style:italic;color:#C15F3C}}
#win{{left:110px;top:410px;width:860px;height:520px;border-radius:30px;background:#fff;overflow:hidden;
  box-shadow:0 30px 70px rgba(60,40,20,.18),0 0 0 1px rgba(0,0,0,.06)}}
#win .bar{{position:absolute;left:0;top:0;right:0;height:78px;display:flex;align-items:center;gap:10px;padding:0 26px;
  border-bottom:1px solid #eee;background:#fff;z-index:3}}
#win .dot{{width:16px;height:16px;border-radius:50%}}
#win .sr{{margin-left:20px;flex:1;height:46px;border-radius:23px;background:#f2f0ec;display:flex;align-items:center;padding:0 22px;
  font:500 26px 'Inter';color:#555;white-space:nowrap;overflow:hidden}}
#lib{{position:absolute;left:26px;top:100px;display:grid;grid-template-columns:repeat(4,190px);gap:14px}}
.lc{{position:relative;width:190px;height:238px;border-radius:10px;overflow:hidden;background:#ddd;transform-origin:50% 50%}}
.lc img{{width:190px;height:238px;object-fit:cover}}
.chip{{position:absolute;left:10px;bottom:10px;padding:5px 11px;border-radius:9px;background:#16a34a;color:#fff;font:800 22px 'Inter';
  box-shadow:0 3px 8px rgba(0,0,0,.25)}}
#pick{{position:absolute;border:5px solid #D97757;border-radius:14px;box-shadow:0 18px 40px rgba(0,0,0,.3)}}
#btn{{left:330px;top:820px;padding:20px 34px;border-radius:40px;background:#1d1b18;color:#fff;font:700 32px 'Inter';white-space:nowrap;
  box-shadow:0 14px 34px rgba(0,0,0,.3);z-index:6}}
.sl{{position:absolute;width:150px;height:188px;border-radius:10px;overflow:hidden;box-shadow:0 10px 26px rgba(0,0,0,.28);z-index:5}}
.sl img{{width:150px;height:188px;object-fit:cover}}
#cur{{left:0;top:0;width:46px;height:46px;z-index:9;filter:drop-shadow(0 3px 5px rgba(0,0,0,.35))}}
#bot{{left:0;top:960px;width:1080px;height:960px;overflow:hidden;background:#000}}
.sc{{position:absolute;left:0;width:1080px;top:{cap_top}px;text-align:center;visibility:hidden;z-index:20}}
.sc span.p{{display:inline-block;padding:18px 34px 20px;border-radius:24px;background:#151515;font:800 66px/1 'Inter';
  letter-spacing:.01em;text-transform:uppercase;white-space:nowrap;box-shadow:0 12px 30px rgba(0,0,0,.4)}}
.sc span.w{{color:rgba(255,255,255,.42)}}
''')
    v = j.get('visual') or {}
    c.body.append('<div id="top" class="a">')
    if j.get('badge'):
        c.body.append(f'<div id="badge" class="a"><span>{STAR}{html.escape(j.get("badge"))}</span></div>')
    c.body.append(f'<div id="h1" class="a">{rich(j.get("headline", ""))}</div>')
    {'grid-pick': grid_pick, 'image': image, 'checklist': checklist}[v.get('type', 'grid-pick')](j, c, v)
    c.body.append(CURSOR + '</div>')
    c.body.append('<div id="bot" class="a">' + c.video(j.clip, f'position:absolute;left:0;top:{j.get("video_top", -430)}px;width:1080px;height:1920px', 'bg') + '</div>')
    c.js.append('''tl.fromTo("#win",{y:50,autoAlpha:0},{y:0,autoAlpha:1,duration:.4,ease:"power3.out"},0);
tl.fromTo(["#badge","#h1"],{y:20,autoAlpha:0},{y:0,autoAlpha:1,duration:.35,stagger:.08,ease:"power3.out"},0);''')
    # seam caption: uppercase pill, each word brightens as it is said
    gs = groups(j.words, maxw=4, maxc=16)
    for i, g in enumerate(gs):
        t0 = max(0, g[0][1] - 0.04)
        t1 = gs[i + 1][0][1] - 0.04 if i + 1 < len(gs) else c.dur
        sp = ' '.join(f'<span class="w" id="sc{i}_{k}">{html.escape(w)}</span>' for k, (w, _) in enumerate(g))
        c.body.append(f'<div class="sc" id="sc{i}"><span class="p">{sp}</span></div>')
        c.js.append(f'tl.set("#sc{i}",{{visibility:"visible"}},{t0:.3f});tl.set("#sc{i}",{{visibility:"hidden"}},{t1:.3f});'
                    f'tl.fromTo("#sc{i} .p",{{scale:.92}},{{scale:1,duration:.12,ease:"back.out(2)"}},{t0:.3f});')
        for k, (w, t) in enumerate(g):
            c.js.append(f'tl.set("#sc{i}_{k}",{{color:"#fff"}},{max(t0, t - 0.02):.3f});')
    j.finish(c)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
