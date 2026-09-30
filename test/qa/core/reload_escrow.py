"""Reload mid-match: escrowed stake vanishes, is never recorded as a loss, and does not count toward the daily loss limit.
Also: closing a FREE match mid-play (reload / DGApp.close) records nothing, so a losing player keeps their rating."""
from qa_common import *
with browser_page() as page:
    boot(page)
    page.evaluate("DGApp.setSpeed(20)")
    page.evaluate("DGApp.set({limits:{loss:1000, remind:0, coolUntil:0}})")
    for k in range(5):
        s0 = page.evaluate("DGApp.state()")
        e = page.evaluate("DGApp.startMatch({game:'rush', format:'1v1', stake:900})")
        if e: print('attempt', k, 'refused:', e); break
        page.wait_for_function("DGApp.current() && DGApp.current().phase === 'ready'")
        page.reload(); page.wait_for_function("window.DG && DG.__appReady === true"); page.evaluate("DGApp.setSpeed(20)")
        s1 = page.evaluate("DGApp.state()")
        print(f'attempt {k}: gold {s0["gold"]} -> {s1["gold"]}, today.net {s1["today"]["net"]}, history {len(s1["history"])}, rec {s1["rec"]}, lossRoom {page.evaluate("DGP.lossRoom()")}')
    # free match rating dodge
    page.evaluate("DGApp.startMatch({game:'chess', format:'1v1', stake:0})")
    page.wait_for_function("DGApp.current() && DGApp.current().phase === 'ready'")
    page.evaluate("document.querySelector('#mStart').click()")
    page.wait_for_function("DGApp.current().phase === 'play'")
    r0 = page.evaluate("DGApp.state().games.chess")
    page.reload(); page.wait_for_function("window.DG && DG.__appReady === true")
    print('free chess abandoned by reload: rating record before/after', r0, page.evaluate("DGApp.state().games.chess"))
