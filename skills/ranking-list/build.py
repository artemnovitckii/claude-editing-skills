#!/usr/bin/env python3
"""ranking-list: a tier list (S to F) on the speaker's chest. Each item pops up on the chest when it is named,
then drops into its row when the speaker gives the verdict. Captions sit just under the chin.

    <kit>/.venv/bin/python build.py spec.json

Spec (see SKILL.md):
  video, start, end, out
  title: "BEST CONTENT\\nFORMATS"            orange skewed title at the top
  items: [{name, tier, pop, drop, images | icon, color}, ...]
  table_top, item_top, caption_top         y positions (1080x1920): table and items on the chest, caption under the chin
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, SAFE_BOTTOM, karaoke, rich  # noqa: E402

TIERS = [('S', '#FF7F7F'), ('A', '#FFBF7F'), ('B', '#FFDF7F'), ('C', '#BFFF7F'), ('D', '#7FBFFF'), ('E', '#8F8FFF'), ('F', '#FF7FFF')]
ICONS = {
    'play': '<div class="rl"></div>',
    'none': '',
}


def main(spec):
    j = Job(spec, 'ranking-list')
    c = Comp(j)
    tiers = [tuple(t) for t in j.get('tiers', TIERS)]
    names = [t for t, _ in tiers]
    TX, TW, RH = 140, 800, 62
    TY = j.get('table_top', 1100)
    IY = j.get('item_top', TY + 30)
    CY = j.get('caption_top', TY - 78)
    c.css.append(f'''
#ttl{{left:0;width:1080px;top:236px;text-align:center;font:italic 800 80px/1.02 'Inter';color:{j.get("title_color", "#F7931E")};letter-spacing:-.01em;
  text-shadow:0 0 22px rgba(247,147,30,.35),0 3px 10px rgba(0,0,0,.4);transform:skewX(-6deg)}}
#tb{{left:{TX}px;top:{TY}px;width:{TW}px;height:{RH*len(tiers)+10}px;background:#000;padding:5px;border-radius:4px;
  box-shadow:0 30px 70px rgba(0,0,0,.5)}}
.row{{position:relative;height:{RH}px;display:flex;border-bottom:3px solid #000}}
.row .lb{{width:76px;height:{RH-3}px;display:grid;place-items:center;font:800 36px 'Inter';color:#111}}
.row .rb{{flex:1;background:#1c1c1e}}
.row .fl{{position:absolute;left:76px;right:0;top:0;bottom:3px;background:rgba(255,255,255,.18);opacity:0}}
.itm{{position:absolute;left:250px;top:{IY}px;width:580px;height:340px;border-radius:6px;overflow:hidden;visibility:hidden;
  transform-origin:0 0;box-shadow:0 0 0 4px rgba(255,255,255,.85),0 20px 50px rgba(0,0,0,.5)}}
.itm .nm{{position:absolute;left:0;right:0;bottom:34px;text-align:center;font:72px/1 'Archivo Black';color:#FFD93B;
  letter-spacing:.01em;text-shadow:0 4px 0 rgba(0,0,0,.35)}}
.itm img.one{{position:absolute;left:0;top:0;width:580px;height:340px;object-fit:cover}}
.itm img.one+.nm{{background:linear-gradient(180deg,transparent,rgba(0,0,0,.7));padding:40px 0 0;bottom:0;height:150px}}
.fan{{position:absolute;top:34px;width:118px;height:148px;border-radius:7px;overflow:hidden;box-shadow:0 6px 18px rgba(0,0,0,.5)}}
.fan img{{width:118px;height:148px;object-fit:cover}}
.rl{{position:absolute;left:236px;top:40px;width:108px;height:150px;border-radius:24px;border:7px solid #fff}}
.rl:after{{content:'';position:absolute;left:36px;top:46px;border-left:36px solid #fff;border-top:22px solid transparent;border-bottom:22px solid transparent}}
.rc span.p{{text-shadow:0 3px 14px rgba(0,0,0,.75);padding:0}}
''')
    c.body.append(c.video(j.clip, 'position:absolute;left:0;top:0;width:1080px;height:1920px', 'bg'))
    c.body.append(f'<div id="ttl" class="a">{rich(j.get("title", ""))}</div>')
    rows = ''.join(f'<div class="row" id="row{t}"><div class="lb" style="background:{col}">{html.escape(t)}</div><div class="rb"></div>'
                   f'<div class="fl"></div></div>' for t, col in tiers)
    c.body.append(f'<div id="tb" class="a">{rows}</div>')
    c.js.append('''tl.fromTo("#ttl",{y:-30,autoAlpha:0},{y:0,autoAlpha:1,duration:.3,ease:"power3.out"},0);
tl.fromTo("#tb",{y:40,autoAlpha:0},{y:0,autoAlpha:1,duration:.3,ease:"power3.out"},0);''')

    used = {}
    for n, it in enumerate(j.get('items') or []):
        tier = it['tier']
        if tier not in names:
            sys.exit(f'item {it["name"]}: tier {tier} is not one of {names}')
        k = used.get(tier, 0)
        used[tier] = k + 1
        imgs = j.images(it.get('images'))
        col = it.get('color', ['#1d4fb8', '#7a2fb0', '#0f766e', '#b45309', '#be123c'][n % 5])
        if len(imgs) >= 2:
            vis = ''.join(f'<div class="fan" style="left:{150+q*95}px;transform:rotate({(q-1)*9}deg) translateY({abs(q-1)*10}px)">'
                          f'<img src="{c.asset(s)}"></div>' for q, s in enumerate(imgs[:3]))
        elif len(imgs) == 1:
            vis = f'<img class="one" src="{c.asset(imgs[0])}">'
        else:
            vis = ICONS.get(it.get('icon', 'none'), '')
        # on a close-up the chest sits low: shrink the card so it never dips into Instagram's bottom UI
        f = max(0.6, min(1.0, (SAFE_BOTTOM - IY) / 340))
        left = 250 + 580 * (1 - f) / 2
        c.body.append(f'<div class="itm" id="it{n}" style="left:{left:.0f}px;background:radial-gradient(ellipse at 50% 30%,{col} 0%,#0b0b14 100%)">'
                      f'{vis}<div class="nm">{html.escape(it["name"])}</div></div>')
        i = names.index(tier)
        sx, sy, sc = TX + 5 + 76 + 8 + k * 128, TY + 5 + i * RH + 6, (RH - 15) / 340
        pop = j.t(it.get('pop'), 0.06)
        drop = j.t(it.get('drop'), pop + 1.1)
        c.js.append(f'''tl.set("#it{n}",{{visibility:"visible"}},{pop:.3f});
tl.fromTo("#it{n}",{{scale:{.5*f:.3f},x:{145*f:.1f},y:{85*f:.1f},autoAlpha:0}},{{scale:{f:.3f},x:0,y:0,autoAlpha:1,duration:.26,ease:"back.out(1.7)",transformOrigin:"0 0"}},{pop:.3f});
tl.to("#it{n}",{{x:{sx-left:.1f},y:{sy-IY},scale:{sc:.4f},duration:.34,ease:"power3.in",transformOrigin:"0 0"}},{drop:.3f});
tl.fromTo("#row{tier} .fl",{{opacity:.9}},{{opacity:0,duration:.5}},{drop + 0.34:.3f});''')
    # spoken-word caption just under the chin, on top of everything
    karaoke(c, j.words, CY, 'rc', maxc=16, size=50, plate=False, grey='#ffffff', white='#ffffff')
    j.finish(c)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
