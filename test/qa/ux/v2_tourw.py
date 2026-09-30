from common import *
with browser_page(360,780,True) as page:
    boot(page)
    page.evaluate("DGApp.startMatch({game:'four',format:'tournament',stake:100})")
    page.wait_for_selector('[data-test=start]:not([disabled])')
    print(page.evaluate("[document.querySelector('#ovStage').scrollWidth, document.querySelector('#ovScroll').clientWidth, document.querySelector('#ov').scrollWidth, document.querySelector('#ovSub').scrollWidth]"))
    print(page.evaluate("""(()=>{const o=[];document.querySelectorAll('#ov *').forEach(e=>{const r=e.getBoundingClientRect();if(r.right>361&&r.width>0)o.push([e.id||e.className.toString().slice(0,30),Math.round(r.right),Math.round(r.width)])});return o.slice(0,10)})()"""))
