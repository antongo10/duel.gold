"""Performance at 4x CPU throttle: long tasks when starting FFA / tournament for heavy race games, versus AI move
times at max skill, frame times of hockey / aim / base during play."""
import json, time
from qa_common import *
LT = r"""(() => { window.__lt = []; try { new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lt.push([Math.round(e.startTime), Math.round(e.duration)]); }).observe({type:'longtask', buffered:true}); } catch(e) {}
  window.__frames = []; let last = 0; const loop = (t) => { if (last) window.__frames.push(t - last); last = t; requestAnimationFrame(loop); }; requestAnimationFrame(loop); })();"""

def throttle(page, r=4):
    cdp = page.context.new_cdp_session(page); cdp.send('Emulation.setCPUThrottlingRate', {'rate': r}); return cdp

def lt_between(page, fn):
    page.evaluate("window.__lt.length = 0")
    fn()
    page.wait_for_timeout(400)
    return page.evaluate("window.__lt.slice()")

with browser_page() as page:
    boot(page, init=[LT])
    throttle(page)
    print('== start matches (4x throttle): long tasks [start, ms]')
    for gid in ['base', 'city', 'restaurant', 'queens', 'sudoku']:
        for fmt in ['ffa', 'tournament', '2v2']:
            page.evaluate("DGApp.set({games: Object.assign(DGApp.state().games, {%s: {r: 1900, w:0,l:0,d:0,best:null,beat:0}})})" % gid)
            page.evaluate("window.__lt.length = 0")
            page.evaluate("(o)=>DGApp.startMatch(o)", {'game': gid, 'format': fmt, 'stake': 0})
            page.wait_for_function("DGApp.current() && ['ready','error'].includes(DGApp.current().phase)", timeout=30000)
            page.wait_for_timeout(300)
            lt1 = page.evaluate("window.__lt.slice()")
            page.evaluate("window.__lt.length = 0")
            # tournament: finish my QF with a loss to trigger simulated rest-of-bracket
            extra = ''
            if fmt == 'tournament':
                page.evaluate("document.querySelector('#mStart').click()")
                page.wait_for_function("DGApp.current().phase === 'play'")
                page.evaluate("window.__lt.length = 0")
                page.evaluate("DGApp.ctx().end({score: -1})")
                page.wait_for_function("DGApp.current().phase === 'result'", timeout=30000)
                page.wait_for_timeout(300)
                extra = f" | QF loss -> simulate bracket: {page.evaluate('window.__lt.slice()')}"
            print(f'  {gid:10s} {fmt:10s} start: {lt1} max={max([d for _, d in lt1], default=0)}ms{extra}')
            page.evaluate("DGApp.close()")
    print('== versus AI at max skill (opp skill 0.98), human autoplay 0.98')
    page.evaluate("DGApp.setSpeed(1)")
    for gid in ['chess', 'reversi', 'gomoku', 'four', 'durak']:
        page.evaluate("DGApp.set({games: Object.assign(DGApp.state().games, {%s: {r: 2300, w:0,l:0,d:0,best:null,beat:0}})})" % gid)
        page.evaluate("(g)=>DGApp.startMatch({game:g, format:'1v1', stake:0})", gid)
        page.wait_for_function("DGApp.current() && DGApp.current().phase === 'ready'", timeout=20000)
        page.evaluate("document.querySelector('#mStart').click()")
        page.wait_for_function("DGApp.current().phase === 'play' && DGApp.ctx() && DGApp.ctx().test")
        page.evaluate("window.__lt.length = 0")
        page.evaluate("DGApp.ctx().test.autoplay(0.98)")
        t0 = time.time()
        while time.time() - t0 < 45:
            page.wait_for_timeout(1000)
            if page.evaluate("DGApp.current().phase") != 'play': break
        lt = page.evaluate("window.__lt.slice()")
        ds = sorted([d for _, d in lt], reverse=True)
        opp = page.evaluate("DGApp.current().opps[0]")
        print(f'  {gid:8s} opp skill {opp["skill"]:.2f}: {len(lt)} long tasks in {time.time()-t0:.0f}s, worst {ds[:6]} ms, >200ms: {sum(1 for d in ds if d > 200)}, phase {page.evaluate("DGApp.current().phase")}')
        page.evaluate("DGApp.close()")
    print('== frame times during play (4x throttle)')
    for gid in ['hockey', 'aim', 'base']:
        page.evaluate("(g)=>DGApp.startMatch({game:g, format:'1v1', stake:0})", gid)
        page.wait_for_function("DGApp.current() && DGApp.current().phase === 'ready'", timeout=20000)
        page.evaluate("document.querySelector('#mStart').click()")
        page.wait_for_function("DGApp.current().phase === 'play' && DGApp.ctx() && DGApp.ctx().test")
        if gid == 'base':
            page.evaluate("DGApp.ctx().test.placeAI(0.9); DGApp.ctx().test.skipToDefence()")
        if gid == 'hockey':
            page.evaluate("DGApp.ctx().test.autoplay(0.8)")
        page.wait_for_timeout(500)
        page.evaluate("window.__frames.length = 0; window.__lt.length = 0")
        page.wait_for_timeout(6000)
        fr = page.evaluate("window.__frames.slice()")
        lt = page.evaluate("window.__lt.slice()")
        fr.sort()
        n = len(fr)
        print(f'  {gid:7s} frames {n} in 6s, median {fr[n//2]:.1f}ms, p95 {fr[int(n*0.95)]:.1f}ms, max {fr[-1]:.1f}ms, >33ms {sum(1 for f in fr if f > 33)}, long tasks {len(lt)} worst {max([d for _, d in lt], default=0)}ms')
        page.evaluate("DGApp.close()")
    print('errors', errs(page)[:3])
