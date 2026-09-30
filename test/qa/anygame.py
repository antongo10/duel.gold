import json
from qalib import *
with new_page_ctx(1280) as page:
    boot(page)
    meta = {g['id']: g for g in page.evaluate("DG.games.map(g => ({id:g.id, kind:g.kind, cat:g.category, formats:g.formats}))")}
    cats = sorted({g['cat'] for g in meta.values()})
    picks = ['any', 'surprise', 'favs'] + ['cat:' + c for c in cats]
    page.evaluate("DGApp.set({favs:['sudoku','chess','hockey']})")
    fmts = ['1v1', '2v2', 'ffa', 'tournament', 'mix']
    bad = []; summary = {}
    g0 = st(page)['gold']
    for pick in picks:
        for f in fmts:
            seen = set(); errs_ = set()
            for i in range(25 if pick in ('any', 'surprise') else 10):
                e = page.evaluate(f"DGApp.startMatch({{game:'{pick}', format:'{f}', stake:100}})")
                if e: errs_.add(e); break
                c = cur(page)
                for gid in c['games']:
                    seen.add(gid)
                    m = meta[gid]
                    compat = (f in m['formats']) and (f != 'mix' or m['kind'] == 'race')
                    if not compat or (pick.startswith('cat:') and m['cat'] != pick[4:]) or (pick == 'favs' and gid not in ('sudoku', 'chess', 'hockey')):
                        bad.append((pick, f, gid))
                if f == 'mix' and len(set(c['games'])) != 3: bad.append((pick, f, 'dup', c['games']))
                page.evaluate("DGApp.close()")
            # UI: is format chip disabled consistently?
            summary[(pick, f)] = (sorted(seen), sorted(errs_))
    for k, v in summary.items(): print(k, v)
    print('BAD', bad)
    print('gold restored', st(page)['gold'] == g0, st(page)['gold'], g0, 'history', len(st(page)['history']))
    # UI chip disabled state vs pool for each pick
    page.click('#tab-home')
    mism = []
    for pick in picks:
        page.click(f'[data-pick="{pick}"]')
        for f in fmts:
            dis = page.is_disabled(f'#dnF-{f}')
            pool = page.evaluate(f"DGP.poolFor('{pick}','{f}').length")
            if dis != (pool == 0): mism.append((pick, f, dis, pool))
    print('chip mismatches', mism)
    print(errs(page))
