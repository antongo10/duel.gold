"""Leaks after 50 back-to-back matches: live intervals/timeouts/rAF, document/window listeners, ResizeObservers,
AudioContexts, DOM nodes. Every game is started, played briefly, then ended (ctx.end), forfeited (abort) or closed."""
import random
from qa_common import *
WRAP = r"""(() => {
  const Q = window.__leak = { iv: new Map(), to: new Map(), raf: new Set(), ro: 0, roLive: new Set(), ls: new Map(), ac: 0 };
  const sI = setInterval, cI = clearInterval, sT = setTimeout, cT = clearTimeout, rA = requestAnimationFrame, cA = cancelAnimationFrame;
  const stack = () => (new Error().stack || '').split('\n').slice(2, 4).join(' | ').replace(/file:\/\/\S+preview\.html/g, '');
  window.setInterval = function (fn, ms, ...a) { const id = sI(fn, ms, ...a); Q.iv.set(id, stack()); return id; };
  window.clearInterval = function (id) { Q.iv.delete(id); Q.to.delete(id); return cI(id); };
  window.setTimeout = function (fn, ms, ...a) { const id = sT(function () { Q.to.delete(id); return fn.apply(this, arguments); }, ms, ...a); Q.to.set(id, stack()); return id; };
  window.clearTimeout = function (id) { Q.to.delete(id); Q.iv.delete(id); return cT(id); };
  window.requestAnimationFrame = function (fn) { const id = rA((t) => { Q.raf.delete(id); fn(t); }); Q.raf.add(id); return id; };
  window.cancelAnimationFrame = function (id) { Q.raf.delete(id); return cA(id); };
  const RO = window.ResizeObserver;
  window.ResizeObserver = class extends RO { constructor(cb) { super(cb); Q.ro++; this.__n = 0; }
    observe(t) { this.__n++; Q.roLive.add(this); return super.observe(t); } disconnect() { Q.roLive.delete(this); return super.disconnect(); } };
  const aE = EventTarget.prototype.addEventListener, rE = EventTarget.prototype.removeEventListener;
  EventTarget.prototype.addEventListener = function (t, fn, o) { if (this === window || this === document) { const k = (this === window ? 'w:' : 'd:') + t; Q.ls.set(k, (Q.ls.get(k) || 0) + 1); } return aE.call(this, t, fn, o); };
  EventTarget.prototype.removeEventListener = function (t, fn, o) { if (this === window || this === document) { const k = (this === window ? 'w:' : 'd:') + t; Q.ls.set(k, (Q.ls.get(k) || 0) - 1); } return rE.call(this, t, fn, o); };
  const AC = window.AudioContext; if (AC) window.AudioContext = class extends AC { constructor(...a) { super(...a); Q.ac++; } };
})();"""
SNAP = """(() => { const Q = window.__leak; const live = [...Q.roLive].filter(r => r.__n).length;
  const byStack = {}; for (const s of Q.to.values()) byStack[s] = (byStack[s]||0)+1; for (const s of Q.iv.values()) byStack['IV '+s] = (byStack['IV '+s]||0)+1;
  return { iv: Q.iv.size, to: Q.to.size, raf: Q.raf.size, roLive: live, roMade: Q.ro, ls: Object.fromEntries(Q.ls), ac: Q.ac, dom: document.getElementsByTagName('*').length,
    heap: performance.memory ? Math.round(performance.memory.usedJSHeapSize/1e6) : null, stacks: byStack, styles: document.head.querySelectorAll('style').length }; })()"""
random.seed(3)
with browser_page() as page:
    boot(page, init=[WRAP])
    page.evaluate("DGApp.setSpeed(10)")
    page.wait_for_timeout(1500)
    base = page.evaluate(SNAP)
    print('baseline', {k: v for k, v in base.items() if k != 'stacks'})
    games = page.evaluate("DG.games.map(g=>g.id)")
    snaps = []
    for i in range(50):
        gid = games[i % len(games)]
        fmt = '1v1'
        page.evaluate("(g)=>DGApp.startMatch({game:g, format:'1v1', stake:10})", gid)
        page.wait_for_function("DGApp.current() && DGApp.current().phase === 'ready'", timeout=20000)
        page.evaluate("document.querySelector('#mStart').click()")
        page.wait_for_function("DGApp.current().phase === 'play' || DGApp.current().phase === 'error'")
        page.wait_for_timeout(700)
        how = ['end', 'forfeit', 'close'][i % 3]
        if how == 'end':
            kind = page.evaluate("(g)=>DG.getGame(g).kind", gid)
            page.evaluate("DGApp.ctx().end(" + ("{score:1}" if kind == 'race' else "{outcome:'loss', myScore:0, oppScore:1}") + ")")
            page.wait_for_function("['result','error'].includes(DGApp.current().phase)")
            page.evaluate("DGApp.close()")
        elif how == 'forfeit':
            page.evaluate("DGApp.forfeit()"); page.evaluate("DGApp.close()")
        else:
            page.evaluate("DGApp.close()")
        if i % 10 == 9:
            page.wait_for_timeout(1500)
            s = page.evaluate(SNAP); snaps.append(s)
            print(f'after {i+1:2d}: iv {s["iv"]} to {s["to"]} raf {s["raf"]} RO live {s["roLive"]}/{s["roMade"]} dom {s["dom"]} heap {s["heap"]}MB styles {s["styles"]} audioCtx {s["ac"]} listeners ' + str({k: v for k, v in s['ls'].items() if v}))
    page.wait_for_timeout(3000)
    s = page.evaluate(SNAP)
    print('final stacks of live timers:')
    for k, v in sorted(s['stacks'].items(), key=lambda x: -x[1])[:8]: print('  ', v, k[:230])
    print('console errors:', errs(page)[:3])
