import sys, pathlib, json, time
sys.path.insert(0, '/home/claude/duel-gold/test')
from dglib import browser_page, open_app
APP = '/home/claude/duel-gold/dist/preview.html'
SHOTS = pathlib.Path('/home/claude/duel-gold/test/qa/ux/shots')
SIZES = {'360': (360, 780, True), '768': (768, 1024, False), '1440': (1440, 900, False)}

def boot(page, age='adult', gold=None):
    open_app(page, APP)
    page.wait_for_function("window.DG && DG.__appReady", timeout=15000)
    if age:
        page.click('#ageAdult' if age == 'adult' else '#ageMinor')
    if gold is not None:
        page.evaluate(f"DGApp.set({{gold:{gold}}})")

def shot(page, name, full=False):
    p = SHOTS / f"{name}.png"
    if full and page.evaluate("!document.querySelector('#ov').hidden"):
        # expand overlay scroller to capture everything
        page.evaluate("(()=>{const o=document.querySelector('#ov');window.__ovst=o.getAttribute('style')||'';const h=document.querySelector('#ovBar').offsetHeight+document.querySelector('#ovSub').offsetHeight+document.querySelector('#ovScroll').scrollHeight+20;o.style.position='absolute';o.style.height=h+'px';o.style.bottom='auto';document.querySelector('#ovScroll').style.overflow='visible';document.querySelector('#ovScroll').style.maxHeight='none';window.__ovh=h})()")
        h = page.evaluate("window.__ovh")
        vp = page.viewport_size
        page.set_viewport_size({'width': vp['width'], 'height': int(h)})
        page.wait_for_timeout(150)
        page.screenshot(path=str(p))
        page.set_viewport_size(vp)
        page.evaluate("(()=>{const o=document.querySelector('#ov');o.setAttribute('style',window.__ovst);const s=document.querySelector('#ovScroll');s.style.overflow='';s.style.maxHeight=''})()")
        return str(p)
    page.screenshot(path=str(p), full_page=full)
    return str(p)

def hscroll(page):
    return page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")

def small_targets(page, root='body', minpx=36):
    return page.evaluate("""([root,minpx])=>{const out=[];document.querySelectorAll(root+' button, '+root+' a, '+root+' input, '+root+' select, '+root+' [role=button]').forEach(e=>{const r=e.getBoundingClientRect();if(r.width===0||r.height===0)return;const st=getComputedStyle(e);if(st.visibility==='hidden')return;if(r.width<minpx||r.height<minpx)out.push([(e.id||e.className||e.tagName).toString().slice(0,40),(e.textContent||e.getAttribute('aria-label')||'').trim().slice(0,24),Math.round(r.width),Math.round(r.height)])});return out}""", [root, minpx])

def overflowing(page, root='body'):
    # elements whose content is wider than box (text clipping) or extend past viewport
    return page.evaluate("""(root)=>{const W=window.innerWidth;const out=[];document.querySelectorAll(root+' *').forEach(e=>{const r=e.getBoundingClientRect();if(r.width===0)return;const st=getComputedStyle(e);if(st.display==='none'||st.visibility==='hidden')return;if(r.right>W+1&&!e.closest('.dg-scroll-x')&&!e.closest('[style*=overflow]'))out.push(['past-vp',(e.id||e.className||e.tagName).toString().slice(0,40),(e.textContent||'').trim().slice(0,30),Math.round(r.right)]);if((st.overflow==='hidden'||st.textOverflow==='ellipsis'||st.overflowX==='hidden')&&e.scrollWidth>e.clientWidth+1&&e.children.length<3)out.push(['clipped',(e.id||e.className||e.tagName).toString().slice(0,40),(e.textContent||'').trim().slice(0,30),e.scrollWidth,e.clientWidth])});return out.slice(0,40)}""", root)

def errs(page):
    return [c for c in page._console if c.startswith(('error', 'pageerror'))]
