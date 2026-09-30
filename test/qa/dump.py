from qalib import *
import json
with new_page_ctx(1280) as page:
    boot(page)
    d = page.evaluate("DG.games.map(g => ({id:g.id, kind:g.kind, cat:g.category, formats:g.formats, spect: typeof g.spectate==='function', rules:g.rules}))")
    for g in d:
        print(g['id'], g['kind'], g['cat'], g['formats'], 'spect' if g['spect'] else '')
        for r in g['rules']:
            if any(w in r.lower() for w in ['key','space','arrow','digit','enter','1–','1-4']): print('    KEY:', r)
    print(len(d))
