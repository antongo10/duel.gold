from common import *
with browser_page(360,780,True) as page:
    boot(page)
    page.evaluate("DGApp.go('profile')"); page.wait_for_timeout(300)
    print(page.evaluate("""()=>{const v=document.querySelector('#view-profile');const out=[];let e=v;out.push(['view',v.getBoundingClientRect().width, getComputedStyle(v.parentElement).display]);
    document.querySelectorAll('#view-profile > *').forEach(c=>out.push([c.className,Math.round(c.getBoundingClientRect().width),c.scrollWidth]));
    const m=document.querySelector('#main');out.push(['main',m.getBoundingClientRect().width,m.scrollWidth,getComputedStyle(m).display, getComputedStyle(m).gridTemplateColumns]);
    const t=document.querySelector('#gameTable');out.push(['table',t.getBoundingClientRect().width]);
    return out}"""))
    print(page.evaluate("[document.documentElement.scrollWidth, document.body.scrollWidth, document.querySelector('#app').scrollWidth]"))
