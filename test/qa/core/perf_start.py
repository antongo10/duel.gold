"""Repeat start-blocking measurement (4x throttle, fresh page per case, 3 reps) for the worst cases."""
from qa_common import *
LT = "window.__lt=[]; new PerformanceObserver(l=>{for(const e of l.getEntries()) window.__lt.push(Math.round(e.duration));}).observe({type:'longtask'});"
for gid, fmt in [('restaurant', 'ffa'), ('restaurant', 'tournament'), ('sudoku', 'tournament'), ('queens', 'ffa'), ('base', 'ffa')]:
    res = []
    for rep in range(3):
        with browser_page() as page:
            boot(page, init=[LT]); page.context.new_cdp_session(page).send('Emulation.setCPUThrottlingRate', {'rate': 4})
            page.evaluate("DGApp.set({games: {%s: {r: 1900, w:0,l:0,d:0,best:null,beat:0}}})" % gid)
            page.wait_for_timeout(500); page.evaluate("window.__lt.length=0")
            page.evaluate("(o)=>DGApp.startMatch(o)", {'game': gid, 'format': fmt, 'stake': 0})
            page.wait_for_function("DGApp.current() && DGApp.current().phase === 'ready'", timeout=30000); page.wait_for_timeout(300)
            a = max(page.evaluate("window.__lt") or [0])
            b = 0
            if fmt == 'tournament':
                page.evaluate("document.querySelector('#mStart').click()"); page.wait_for_function("DGApp.current().phase==='play'")
                page.evaluate("window.__lt.length=0; DGApp.ctx().end({score:-1})")
                page.wait_for_function("DGApp.current().phase==='result'", timeout=30000); page.wait_for_timeout(300)
                b = max(page.evaluate("window.__lt") or [0])
            res.append((a, b))
    print(gid, fmt, 'worst task at start / after QF loss (ms):', res)
