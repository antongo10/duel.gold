"""Close during matchmaking at speed 40: read phase and close atomically in one evaluate to avoid harness races."""
from qa_common import *
with browser_page() as page:
    boot(page); page.evaluate("DGApp.setSpeed(40)")
    bad = 0; phases = {}
    for i in range(60):
        r = page.evaluate("""() => { const g0 = DGApp.state().gold; DGApp.startMatch({game:'any', format:['1v1','ffa','tournament','mix','2v2'][Math.floor(Math.random()*5)], stake:50});
            const ph = DGApp.current().phase; DGApp.close(); const g1 = DGApp.state().gold; return {ph, d: g1 - g0}; }""")
        phases[r['ph']] = phases.get(r['ph'], 0) + 1
        if r['ph'] == 'mm' and r['d'] != 0: bad += 1; print('BUG', r)
    print('phases', phases, 'bad', bad, errs(page)[:2])
