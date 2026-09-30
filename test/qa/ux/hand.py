from common import *
def start_via_ui(page, gid, name, stake='S-100', fmt=None):
    page.tap('#tab-games') if page.is_visible('#tab-games') else page.tap('#bn-games')
    page.wait_for_timeout(200)
    page.fill('#libSearch', name)
    page.wait_for_timeout(200)
    page.tap(f'[data-duel="{gid}"]')
    page.wait_for_selector('[data-test=duel-sheet]')
    if fmt: page.tap(f'#shF-{fmt}')
    if stake: page.tap(f'#sh{stake}')
    page.wait_for_timeout(100)
    page.tap('#shFind')
    page.wait_for_selector('[data-test=start]', timeout=8000)
def tap_start(page):
    page.tap('[data-test=start]'); page.wait_for_timeout(700)
def status(page): return page.evaluate("document.querySelector('#ovStatus').textContent")
def wait_result(page, t=120000):
    page.wait_for_function("DGApp.current() && DGApp.current().phase==='result'", timeout=t)
def back(page):
    page.tap('#resBack'); page.wait_for_timeout(300)
