from common import *
with browser_page(360,780,True) as page:
    boot(page)
    page.evaluate("DGApp.startMatch({game:'four',format:'tournament',stake:100})")
    page.wait_for_selector('[data-test=start]:not([disabled])')
    print(page.evaluate("""(()=>{const o=[];document.querySelectorAll('#ovStage *').forEach(e=>{const r=e.getBoundingClientRect();if(r.width>330)o.push([e.tagName,e.className.toString().slice(0,30),Math.round(r.width),getComputedStyle(e).display,getComputedStyle(e).gridTemplateColumns])});return o.slice(0,12)})()"""))
    print(page.evaluate("getComputedStyle(document.querySelector('#ov')).display+' '+getComputedStyle(document.querySelector('#ov')).gridTemplateColumns"))
    for g,f in [('rush','tournament'),('four','1v1'),('rush','mix')]:
        page.evaluate("DGApp.close()")
        page.evaluate(f"DGApp.startMatch({{game:'{g}',format:'{f}',stake:100}})"); page.wait_for_selector('[data-test=start]:not([disabled])')
        print(g,f,page.evaluate("document.querySelector('#ov').scrollWidth"))
