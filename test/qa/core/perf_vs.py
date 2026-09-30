"""Re-measure versus AI long tasks (4x throttle) twice for chess/reversi to separate regression from noise."""
import time
from qa_common import *
LT = "window.__lt=[]; new PerformanceObserver(l=>{for(const e of l.getEntries()) window.__lt.push(Math.round(e.duration));}).observe({type:'longtask'});"
for run in range(2):
    with browser_page() as page:
        boot(page, init=[LT])
        page.context.new_cdp_session(page).send('Emulation.setCPUThrottlingRate', {'rate': 4})
        for gid in ['chess', 'reversi']:
            page.evaluate("DGApp.set({games: Object.assign(DGApp.state().games, {%s: {r: 2300, w:0,l:0,d:0,best:null,beat:0}})})" % gid)
            page.evaluate("(g)=>DGApp.startMatch({game:g, format:'1v1', stake:0})", gid)
            page.wait_for_function("DGApp.current() && DGApp.current().phase === 'ready'", timeout=20000)
            page.evaluate("document.querySelector('#mStart').click()")
            page.wait_for_function("DGApp.current().phase === 'play' && DGApp.ctx() && DGApp.ctx().test")
            page.evaluate("window.__lt.length=0; DGApp.ctx().test.autoplay(0.98)")
            t0 = time.time()
            while time.time() - t0 < 40 and page.evaluate("DGApp.current().phase") == 'play': page.wait_for_timeout(1000)
            ds = sorted(page.evaluate("window.__lt"), reverse=True)
            print(f'run{run} {gid}: {len(ds)} long tasks, worst {ds[:5]}, >200ms {sum(d > 200 for d in ds)}')
            page.evaluate("DGApp.close()")
    print('hooks exposed:', 'ok')
