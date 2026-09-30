import json, time, sys
from qalib import *
width = int(sys.argv[1]) if len(sys.argv) > 1 else 1280
touch = width < 500
SP = ['chess', 'four', 'reversi', 'gomoku', 'hockey', 'durak', 'liars', 'auction']
with new_page_ctx(width, touch=touch) as page:
    boot(page)
    # 1) via Watch tab UI: click first few cards
    page.evaluate("DGApp.setSpeed(20)")
    page.click('#tab-watch' if not touch else '#bn-watch')
    page.wait_for_selector('[data-watch-go]')
    cards = page.evaluate("[...document.querySelectorAll('.wcard')].map(c => [c.dataset.watch, c.querySelector('.dg-eyebrow').textContent, c.querySelector('[data-watch-go]').disabled])")
    print('watch cards', cards)
    b = page.locator('[data-watch-go]').first; b.scroll_into_view_if_needed(); b.tap() if touch else b.click()
    page.wait_for_selector('[data-test=watch-result]', timeout=180000)
    print('UI watch first card ->', last(page))
    shot(page, f'watch-ui-{width}')
    page.click('#watchBack')
    # 2) every spectate game + race timelines via watchGame hook, run to completion
    for gid in list(GAMES):
        sp = 10 if gid in SP else 6
        page.evaluate(f"DGApp.setSpeed({sp})")
        e0 = len(errs(page)); t0 = time.time()
        r = page.evaluate(f"DGApp.watchGame('{gid}')")
        mode = page.evaluate("document.querySelector('[data-test=spectate]') ? 'spectate' : document.querySelector('[data-test=watch-race]') ? 'race' : 'other'")
        try:
            page.wait_for_selector('[data-test=watch-result], [data-test=error]', timeout=240000)
            L = last(page)
        except Exception as ex:
            L = {'TIMEOUT': True, 'status': page.text_content('#ovStatus')}
            shot(page, f'watch-timeout-{gid}')
        if gid in ('chess', 'durak', 'hockey', 'reversi'): shot(page, f'watch-{gid}-{width}')
        txt = page.inner_text('[data-test=watch-result]') if page.locator('[data-test=watch-result]').count() else page.inner_text('#ovStage')[:200]
        print(gid, mode, 'expected', 'spectate' if gid in SP else 'race', L, round(time.time() - t0, 1), 's', txt.replace('\n', ' | '), errs(page)[e0:])
        page.evaluate("DGApp.close()")
        page.wait_for_timeout(100)
    print('errors', errs(page))
