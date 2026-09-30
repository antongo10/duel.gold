"""Close overlay during matchmaking with stake == whole balance."""
from qa_common import *
with browser_page() as page:
    boot(page)
    for fmt in ['1v1','2v2','ffa','tournament','mix']:
        for k in range(4):
            g0 = page.evaluate("DGApp.state().gold")
            e = page.evaluate("(o)=>DGApp.startMatch(o)", {'game': 'any', 'format': fmt, 'stake': g0})
            ph = page.evaluate("DGApp.current() && DGApp.current().phase")
            page.evaluate("DGApp.close()")
            g1 = page.evaluate("DGApp.state().gold")
            print(fmt, 'err', repr(e), 'phase', ph, g0, '->', g1, 'OK' if g0 == g1 else 'FAIL')
