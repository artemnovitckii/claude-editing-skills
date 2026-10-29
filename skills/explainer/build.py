#!/usr/bin/env python3
"""explainer: the speaker sits low in a rounded panel on a light backdrop, the head breaking out over its top edge,
and the top of the frame explains the point with visuals (a before/after comparison or a short list).

    <kit>/.venv/bin/python build.py spec.json

Spec (see SKILL.md):
  video, start, end, out
  title: "Steal what *works*"                        (*word* = serif italic accent)
  eye_y: 750                                         speaker's eye line in the 1080x1920 frame (the panel's top edge)
  visual: {type: compare | list, ...}
  keys: ["viral", "recreate"]                        caption words set in the serif italic
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, cover_html, rich, word_caps  # noqa: E402

ACC = '#C15F3C'


def text_card(big, small, dark):
    bg, fg, sub = ('#1d1b18', '#fff', 'rgba(255,255,255,.6)') if dark else ('#fff', '#111', '#7a7368')
    return (f'<div class="tcard" style="background:{bg};color:{fg}"><div class="tb">{rich(big)}</div>'
            f'<div class="ts" style="color:{sub}">{html.escape(small)}</div></div>')


def compare(j, c, v):
    L, R = v.get('left') or {}, v.get('right') or {}
    limgs = j.images(L.get('images'))
    if limgs:
        strip = ''.join(f'<img src="{c.asset(s)}">' for s in limgs[:3])
    elif L.get('big'):
        strip = text_card(L['big'], L.get('small', ''), dark=False)
    else:
        sys.exit('visual.left needs images, or big (+ small) for a text card')
    if R.get('big') and not R.get('image'):
        right = text_card(R['big'], R.get('small', ''), dark=True)
    elif R.get('text'):
        right = cover_html(c, 270, (j.images(R.get('image')) or [None])[0], R['text'], R.get('cta', 'SWIPE →'))
    elif R.get('image'):
        right = f'<img src="{c.asset(j.images(R.get("image"))[0])}" style="width:270px;height:338px;object-fit:cover;border-radius:12px">'
    else:
        sys.exit('visual.right needs image, image + text, or big (+ small) for a text card')
    chip = f'<div id="vch" class="hid">{html.escape(L["chip"])}</div>' if L.get('chip') else ''
    c.body.append(f'''<div class="lab" id="lab0" style="left:110px;top:340px">{html.escape(L.get("label", "Before"))}</div>
<div class="lab" id="lab1" style="left:700px;top:340px;color:{ACC}">{html.escape(R.get("label", "After"))}</div>
<div class="cv" id="lc" style="left:110px;top:385px"><div class="strip">{strip}</div>{chip}</div>
<div id="rc0" class="a hid">?</div>
<div id="rc" class="a">{right}</div>
<svg id="arw" class="a" viewBox="0 0 320 120"><path id="arp" d="M14 64 C 100 -12, 220 -12, 304 60" fill="none" stroke="{ACC}" stroke-width="7"
 stroke-linecap="round" stroke-dasharray="420" stroke-dashoffset="420"/><path id="arh" d="M296.0 31.1 L304 60 L274.2 56.6" fill="none" stroke="{ACC}"
 stroke-width="7" stroke-linecap="round" stroke-linejoin="round" opacity="0"/></svg>''')
    la = j.t(L.get('at'), 0.3)
    ra = j.t(R.get('at'), c.dur * 0.55)
    aa = j.t(v.get('arrow_at'), ra + 0.6)
    rv = j.t(R.get('reveal_at'), aa + 0.28)
    c.js.append(f'tl.fromTo(["#lab0","#lc"],{{y:30,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.32,stagger:.05,ease:"power3.out"}},{la:.3f});')
    if chip:
        ch = j.t(L.get('chip_at'), la + 0.8)
        c.js.append(f'tl.set("#vch",{{visibility:"visible"}},{ch:.3f});'
                    f'tl.fromTo("#vch",{{scale:.4,autoAlpha:0}},{{scale:1,autoAlpha:1,duration:.22,ease:"back.out(2.5)"}},{ch:.3f});')
    for k, s in enumerate((L.get('swipe_at') or [])[:max(0, len(limgs[:3]) - 1)]):
        c.js.append(f'tl.to("#lc .strip",{{x:{-270 * (k + 1)},duration:.3,ease:"power2.inOut"}},{j.t(s):.3f});')
    c.js.append(f'''tl.set("#rc0",{{visibility:"visible"}},{ra:.3f});
tl.fromTo(["#lab1","#rc0"],{{y:30,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.3,stagger:.05,ease:"power3.out"}},{ra:.3f});
tl.fromTo("#lab0",{{color:"#7a7368"}},{{color:"#111",duration:.2}},{ra:.3f});
tl.to("#arp",{{strokeDashoffset:0,duration:.38,ease:"power2.inOut"}},{aa:.3f});
tl.to("#arh",{{opacity:1,duration:.08}},{aa+0.34:.3f});
tl.to("#rc",{{clipPath:"inset(0 0% 0 0)",duration:.34,ease:"power3.out"}},{rv:.3f});
tl.fromTo("#rc",{{scale:1.06}},{{scale:1,duration:.4,ease:"power3.out"}},{rv:.3f});''')


def listing(j, c, v):
    items = v.get('items') or []
    rows = ''.join(f'<div class="li" id="li{i}"><b>{i + 1}</b><span>{rich(it["text"])}</span></div>' for i, it in enumerate(items))
    rh = min(118, 420 // max(1, len(items)))
    c.css.append(f'''#lst{{left:120px;top:{330 + (430 - rh * len(items)) // 2}px;width:840px}}
.li{{display:flex;align-items:center;gap:26px;height:{rh}px;font:700 50px/1.05 'Inter';color:#111;letter-spacing:-.02em}}
.li b{{width:72px;height:72px;border-radius:20px;background:{ACC};color:#fff;display:grid;place-items:center;font:800 38px 'Inter';flex:none}}
.li em{{font:italic 400 60px 'DM Serif Display';color:{ACC};letter-spacing:0}}''')
    c.body.append(f'<div id="lst" class="a">{rows}</div>')
    for i, it in enumerate(items):
        t = j.t(it.get('at'), 0.4 + i * 0.7)
        c.js.append(f'tl.fromTo("#li{i}",{{x:-40,autoAlpha:0}},{{x:0,autoAlpha:1,duration:.32,ease:"back.out(1.6)"}},{t:.3f});')


def main(spec):
    j = Job(spec, 'explainer')
    c = Comp(j)
    SC, VX, VY = 0.82, 97, 316
    VW, VH = 1080 * SC, 1920 * SC
    PT = VY + float(j.get('eye_y', 750)) * SC        # the panel's top edge sits on the eye line, so the head breaks out
    PB = 1830
    cap = j.get('caption_top', 1420)
    c.css.append(f'''
#bk{{left:0;top:0;width:1080px;height:1920px;background:radial-gradient(ellipse at 50% 30%,#f6f4f0 0%,#e9e6e0 70%,#dedad3 100%)}}
#ttl{{left:0;width:1080px;top:206px;text-align:center;font:800 88px/1 'Inter';color:#111;letter-spacing:-.035em}}
#ttl span{{display:inline-block}}
#ttl em{{font:italic 400 100px/1 'DM Serif Display';color:{ACC};letter-spacing:-.01em}}
#pan{{left:{VX}px;top:{PT:.0f}px;width:{VW:.0f}px;height:{PB-PT:.0f}px;border-radius:56px;overflow:hidden;box-shadow:0 30px 70px rgba(40,30,20,.28)}}
#pop{{left:{VX}px;top:{VY}px;width:{VW:.0f}px;height:{PT-VY:.0f}px;overflow:hidden}}
.lab{{position:absolute;font:800 25px 'Inter';letter-spacing:.12em;text-transform:uppercase;color:#7a7368;white-space:nowrap}}
.cv{{position:absolute;width:270px;height:338px;border-radius:12px;overflow:hidden;box-shadow:0 18px 40px rgba(40,30,20,.25)}}
#lc .strip{{display:flex}}#lc img{{width:270px;height:338px;object-fit:cover;flex:none}}
#vch{{position:absolute;left:12px;top:12px;padding:6px 13px;border-radius:10px;background:#16a34a;color:#fff;font:800 24px 'Inter'}}
#rc0{{left:700px;top:385px;width:270px;height:338px;border-radius:12px;border:4px dashed #b8b0a3;display:grid;place-items:center;
  font:800 80px 'Inter';color:#c9c2b6}}
#rc{{left:700px;top:385px;clip-path:inset(0 100% 0 0)}}
#arw{{left:380px;top:470px;width:320px;height:120px;overflow:visible}}
.kx{{position:absolute;left:0;width:1080px;top:{cap}px;text-align:center;visibility:hidden;font:800 70px/1 'Inter';color:#fff;
  letter-spacing:-.02em;text-shadow:0 3px 6px rgba(0,0,0,.55),0 6px 26px rgba(0,0,0,.6)}}
.kx em{{font:italic 400 84px/1 'DM Serif Display';color:#fff;letter-spacing:0}}
.tcard{{width:270px;height:338px;border-radius:12px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;
  padding:24px;text-align:center}}
.tcard .tb{{font:800 64px/1 'Inter';letter-spacing:-.03em}}
.tcard .tb em{{font:italic 400 76px/1 'DM Serif Display';color:{ACC}}}
.tcard .ts{{font:600 24px/1.25 'Inter'}}
''')
    c.body.append('<div id="bk" class="a"></div>')
    words = rich(j.get('title', '')).split(' ')
    c.body.append(f'<div id="ttl" class="a">{" ".join(f"<span>{w}</span>" for w in words)}</div>')
    v = j.get('visual') or {}
    {'compare': compare, 'list': listing}[v.get('type', 'compare')](j, c, v)
    cut = j.cutout()
    c.body.append('<div id="pan" class="a">' + c.video(j.clip, f'position:absolute;left:0;top:{VY-PT:.0f}px;width:{VW:.0f}px;height:{VH:.0f}px', 'bg') + '</div>')
    c.body.append('<div id="pop" class="a">' + c.video(cut, f'position:absolute;left:0;top:0;width:{VW:.0f}px;height:{VH:.0f}px', 'cut') + '</div>')
    word_caps(c, j.words, 'kx', '', maxw=3, maxc=16, keys=j.get('keys', []), key_tag='em', pop=(0.94, 0.16))
    c.js.append('tl.fromTo("#ttl span",{y:40,autoAlpha:0},{y:0,autoAlpha:1,duration:.3,stagger:.07,ease:"power3.out"},0);')
    j.finish(c)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
