"""Close overlay during matchmaking must refund the escrowed stake."""
from qa_common import *
with browser_page() as page:
    boot(page)
    fails = 0
    for i, (fmt, stake) in enumerate([(f, s) for f in ['1v1','2v2','ffa','tournament','mix'] for s in [10, 100, 1000]] * 2):
        g0 = page.evaluate("DGApp.state().gold")
        e = page.evaluate("(o)=>DGApp.startMatch(o)", {'game': 'any', 'format': fmt, 'stake': stake})
        ph = page.evaluate("DGApp.current().phase")
        page.evaluate("DGApp.close()")
        g1 = page.evaluate("DGApp.state().gold")
        if g1 != g0:
            fails += 1; print('FAIL', fmt, stake, 'phase', ph, g0, '->', g1)
    print('fails', fails)
    # instrument: which path?
    page.evaluate("""() => { const M = DGP.match; window.__trace=[]; }""")
