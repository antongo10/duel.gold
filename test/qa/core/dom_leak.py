"""Scan the DOM of every race game during play for attributes that could reveal the solution."""
import sys, collections
sys.path.insert(0, '/home/claude/duel-gold/test')
from dglib import browser_page, open_harness
FILES = {'sudoku': 'brain.js', 'mines': 'brain.js', 'queens': 'brain.js', 'tiles2048': 'brain.js', 'memory': 'brain.js', 'reaction': 'reflex.js', 'aim': 'reflex.js', 'rush': 'reflex.js', 'darts': 'reflex.js', 'base': 'builder.js', 'city': 'builder.js', 'restaurant': 'builder.js', 'trivia': 'social.js', 'groups': 'social.js'}
for gid, f in FILES.items():
    with browser_page(width=1280) as page:
        open_harness(page, files=[f], game=gid, mode='mix', seed=777, speed=1)
        page.evaluate("__run()"); page.wait_for_timeout(1200)
        attrs = page.evaluate("""() => { const out = {}; for (const el of document.querySelectorAll('#root *')) for (const a of el.attributes) { if (['class','style','viewBox','d','fill','stroke','width','height','x','y','rx','cx','cy','r','type','tabindex','inputmode','aria-hidden'].includes(a.name)) continue; (out[a.name] = out[a.name] || new Set()).add(a.value); } return Object.fromEntries(Object.entries(out).map(([k,v]) => [k, [...v].slice(0,6).concat(v.size>6?['…'+v.size]:[])])); }""")
        hidden = page.evaluate("[...document.querySelectorAll('#root [hidden], #root [style*=\"display:none\"], #root [style*=\"display: none\"]')].map(e=>e.outerHTML.slice(0,120))")
        print(gid, {k: v for k, v in attrs.items() if k.startswith('data-') and k not in ('data-test',)}, 'hidden:', hidden[:2])
