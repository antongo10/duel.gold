from common import *
with browser_page(360,780,True) as page:
    boot(page)
    page.evaluate("DGApp.go('profile')"); page.wait_for_timeout(300)
    print(page.evaluate("""()=>{const out=[];document.querySelectorAll('#view-profile *').forEach(e=>{const r=e.getBoundingClientRect(); if(r.right>345 && r.width<340 && r.width>0) out.push([e.tagName, e.className.toString().slice(0,30), (e.textContent||'').slice(0,30), Math.round(r.width), Math.round(r.right)])});return out.slice(0,15)}"""))
    # check which has min-content > 328
    print(page.evaluate("""()=>{const v=document.querySelector('#view-profile');v.style.gridTemplateColumns='minmax(0,1fr)';return [...v.children].map(c=>[c.className,Math.round(c.getBoundingClientRect().width)])}"""))
