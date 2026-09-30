import json
from qalib import *
from finish import FIN
ids = list(GAMES)
SNAP = "(() => ({rafCalls: __qa.rafCalls, pend: __qa.raf, iv: __qa.iv, kd: __qa.keydown}))()"
with new_page_ctx(1280) as page:
    # also count ResizeObservers still observing
    page.add_init_script("""(() => { const RO = window.ResizeObserver; let live = 0; window.__ro = () => live;
      window.ResizeObserver = class extends RO { constructor(cb){ super(cb); this.__on = false; } observe(t,o){ if(!this.__on){this.__on=true; live++;} return super.observe(t,o);} disconnect(){ if(this.__on){this.__on=false; live--;} return super.disconnect(); } }; })()""")
    boot(page)
    page.evaluate("DGApp.setSpeed(3)")
    page.wait_for_timeout(500)
    s0 = page.evaluate(SNAP); ro0 = page.evaluate("__ro()")
    t0 = page.evaluate("performance.now()")
    peak_kd = 0
    for i in range(30):
        gid = ids[i % len(ids)]
        page.evaluate(f"DGApp.startMatch({{game:'{gid}', format:'1v1', stake:10}})")
        page.wait_for_selector('[data-test=start]:not([disabled])', timeout=10000); page.click('[data-test=start]')
        page.wait_for_function("DGApp.ctx() && DGApp.ctx().test", timeout=8000)
        page.wait_for_timeout(400)
        peak_kd = max(peak_kd, page.evaluate("__qa.keydown"))
        if i % 3 == 0:
            FIN[gid](page); wait_result(page, 90)
            # use Rematch button path sometimes, then forfeit on the rules card
            page.click('[data-test=rematch]'); page.wait_for_selector('[data-test=start]:not([disabled])'); page.evaluate("DGApp.forfeit()")
        else:
            page.evaluate("DGApp.forfeit()")
        page.click('[data-test=back]')
    page.wait_for_timeout(1500)
    s1 = page.evaluate(SNAP)
    a = page.evaluate("__qa.rafCalls"); page.wait_for_timeout(2000); b = page.evaluate("__qa.rafCalls")
    print('before', s0, 'ro', ro0)
    print('after 30', s1, 'ro', page.evaluate("__ro()"), 'peak keydown during a match', peak_kd)
    print('idle rAF callbacks in 2 s after all matches:', b - a)
    print('toasts in DOM', page.evaluate("document.querySelectorAll('.toast').length"), 'style tags', page.evaluate("document.querySelectorAll('style').length"), 'nodes', page.evaluate("document.getElementsByTagName('*').length"))
    print('errors', errs(page))
