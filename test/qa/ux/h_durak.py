from hand import *
with browser_page(360,780,True) as page:
    boot(page)
    start_via_ui(page,'durak','durak')
    tap_start(page)
    bout0 = None
    log=[]
    for step in range(40):
        page.wait_for_timeout(700)
        if page.query_selector('[data-test=result]'): break
        s = page.evaluate("DGApp.ctx().test.state()")
        if bout0 is None: bout0=s['bout']
        if s['bout']>bout0+1: break
        if s['toMove']!=0: continue
        legal=page.query_selector_all('button.slot.legal')
        btns=[b.get_attribute('data-t') for b in page.query_selector_all('.g-durak-ctl [data-t]')]
        msg=page.inner_text('[data-test=dk-msg]')
        log.append((s['phase'],len(legal),btns,msg[:70]))
        if step==1: shot(page,'hand-durak-turn-360')
        if legal and 'bito' not in btns and 'done' not in btns: legal[0].tap()
        elif 'bito' in btns: page.tap('[data-test=dk-bito]'); shot(page,'hand-durak-bito-360')
        elif 'done' in btns: page.tap('[data-test=dk-done]')
        elif legal: legal[0].tap()
        elif 'take' in btns: page.tap('[data-test=dk-take]'); shot(page,'hand-durak-take-360')
    for l in log: print(l)
    shot(page,'hand-durak-after-bout-360')
    print(status(page), errs(page))
