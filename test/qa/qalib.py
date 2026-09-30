"""QA helpers for end-to-end tests in the real app (dist/preview.html)."""
import sys, pathlib, time, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from dglib import browser_page, open_app  # noqa

APP = '/home/claude/duel-gold/dist/preview.html'
SHOTS = pathlib.Path(__file__).resolve().parent / 'shots'

GAMES = {
    'chess': 'versus', 'four': 'versus', 'reversi': 'versus', 'gomoku': 'versus',
    'sudoku': 'race', 'mines': 'race', 'queens': 'race', 'tiles2048': 'race', 'memory': 'race',
    'reaction': 'race', 'aim': 'race', 'rush': 'race', 'darts': 'race', 'hockey': 'versus',
    'base': 'race', 'city': 'race', 'restaurant': 'race',
    'trivia': 'race', 'groups': 'race', 'durak': 'versus', 'liars': 'versus', 'auction': 'versus',
}

# counts keydown listeners on document/window, pending rAF callbacks and live intervals/timeouts
INIT = r"""
(() => {
  const W = window.__qa = { keydown: 0, raf: 0, rafCalls: 0, iv: 0, audio: 0, keyLog: [] };
  const pend = new Set();
  const oA = EventTarget.prototype.addEventListener, oR = EventTarget.prototype.removeEventListener;
  const reg = new WeakMap();
  EventTarget.prototype.addEventListener = function (t, fn, o) {
    if ((t === 'keydown' || t === 'keyup') && (this === document || this === window) && fn) {
      let s = reg.get(this); if (!s) { s = new Set(); reg.set(this, s); }
      const k = t + '|' + (o && o.capture || o === true ? 'c' : '');
      if (!s.has(fn)) { s.add(fn); if (t === 'keydown') W.keydown++; }
    }
    return oA.call(this, t, fn, o);
  };
  EventTarget.prototype.removeEventListener = function (t, fn, o) {
    if ((t === 'keydown' || t === 'keyup') && (this === document || this === window) && fn) {
      const s = reg.get(this); if (s && s.has(fn)) { s.delete(fn); if (t === 'keydown') W.keydown--; }
    }
    return oR.call(this, t, fn, o);
  };
  const oRaf = window.requestAnimationFrame.bind(window), oCaf = window.cancelAnimationFrame.bind(window);
  window.requestAnimationFrame = function (fn) {
    const id = oRaf((t) => { pend.delete(id); W.raf = pend.size; W.rafCalls++; fn(t); });
    pend.add(id); W.raf = pend.size; return id;
  };
  window.cancelAnimationFrame = function (id) { pend.delete(id); W.raf = pend.size; return oCaf(id); };
  const ivs = new Set();
  const oSI = window.setInterval.bind(window), oCI = window.clearInterval.bind(window);
  window.setInterval = function (fn, ms, ...a) { const id = oSI(fn, ms, ...a); ivs.add(id); W.iv = ivs.size; return id; };
  window.clearInterval = function (id) { ivs.delete(id); W.iv = ivs.size; return oCI(id); };
  const oCT = window.clearTimeout.bind(window);
  window.clearTimeout = function (id) { if (ivs.has(id)) { ivs.delete(id); W.iv = ivs.size; } return oCT(id); };
  // audio
  const AC = window.AudioContext || window.webkitAudioContext;
  if (AC) {
    const oOsc = AC.prototype.createOscillator;
    AC.prototype.createOscillator = function () { W.audio++; return oOsc.call(this); };
  }
  // page keydown after game: did a key reach default action?
  document.addEventListener('keydown', (e) => { W.keyLog.push({ k: e.key, dp: e.defaultPrevented, tgt: (e.target && (e.target.id || e.target.tagName)) }); if (W.keyLog.length > 200) W.keyLog.shift(); }, false);
  W.keydown = 0; // don't count our own
})();
"""

def new_page_ctx(width=1280, touch=False, height=900):
    return browser_page(width=width, height=height, touch=touch)

def boot(page, init=True, adult=True):
    if init:
        page.add_init_script(INIT)
    open_app(page, APP)
    page.wait_for_function("window.DG && DG.__appReady === true", timeout=15000)
    if adult:
        if page.locator('#ageAdult').count():
            page.click('#ageAdult')
    page.wait_for_timeout(100)

def errs(page):
    # font requests are aborted by dglib on purpose -> ignore that one resource error
    return [c for c in page._console if c.startswith(('error', 'pageerror')) and 'Failed to load resource' not in c]

def shot(page, name):
    p = SHOTS / (name + '.png')
    page.screenshot(path=str(p))
    return str(p)

def st(page):
    return page.evaluate("DGApp.state()")

def cur(page):
    return page.evaluate("DGApp.current()")

def last(page):
    return page.evaluate("DGApp.last()")

def T(page, expr):
    """evaluate expression with t = ctx.test"""
    return page.evaluate("(() => { const c = DGApp.ctx(); const t = c && c.test; return " + expr + "; })()")

def wait_phase(page, phase, timeout=20):
    page.wait_for_function(f"DGApp.current() && DGApp.current().phase === '{phase}'", timeout=timeout * 1000)

def wait_result(page, timeout=60):
    page.wait_for_function("DGApp.current() && (DGApp.current().phase === 'result' || DGApp.current().phase === 'error')", timeout=timeout * 1000)
    return cur(page)['phase']

def start_via_games_tab(page, gid, fmt='1v1', stake=100, touch=False):
    """Games tab -> Duel on card -> choose format and stake -> Find opponent."""
    tap = (lambda s: page.tap(s)) if touch else (lambda s: page.click(s))
    tap('#tab-games' if page.locator('#tab-games').is_visible() else '#bn-games')
    page.wait_for_selector(f'.gcard[data-game="{gid}"]')
    btn = page.locator(f'.gcard[data-game="{gid}"] [data-duel]')
    btn.scroll_into_view_if_needed()
    btn.tap() if touch else btn.click()
    page.wait_for_selector('[data-test=duel-sheet]')
    f = page.locator(f'#shF-{fmt}')
    if f.get_attribute('aria-pressed') != 'true':
        f.tap() if touch else f.click()
    s = page.locator(f'#shS-{stake}')
    s.tap() if touch else s.click()
    fb = page.locator('#shFind')
    fb.scroll_into_view_if_needed()
    fb.tap() if touch else fb.click()

def through_to_play(page, touch=False, shotname=None):
    page.wait_for_selector('[data-test=matchmaking]', timeout=5000)
    page.wait_for_selector('[data-test=start]:not([disabled])', timeout=10000)
    if shotname:
        shot(page, shotname)
    b = page.locator('[data-test=start]')
    b.scroll_into_view_if_needed()
    b.tap() if touch else b.click()
    wait_phase(page, 'play', 5)
    page.wait_for_function("DGApp.ctx() && DGApp.ctx().test", timeout=8000)
