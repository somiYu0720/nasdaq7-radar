/* Research-only score labels. Never changes ranking or numeric production scores. */
(()=>{'use strict';
const body=document.getElementById('rankRows');if(!body)return;
let result=null;
async function refresh(){try{const r=await fetch('./backtest_results.json?t='+Date.now(),{cache:'no-store'});result=r.ok?await r.json():null}catch{result=null}decorate()}
function decorate(){for(const tr of body.querySelectorAll(':scope > tr')){const cells=tr.cells;if(cells.length<9)continue;const ticker=cells[1].textContent.trim().toUpperCase(),score=cells[7];let label=score.querySelector('.research-score');if(!label){label=document.createElement('small');label.className='research-score';label.style.cssText='display:block;color:#9db2ca;font-size:11px;font-weight:400;white-space:normal;margin-top:3px';score.append(label)}
const item=result?.by_ticker?.[ticker];const valid=item&&item.status==='VALIDATED'&&Number.isFinite(item.score)&&Number.isInteger(item.sample_count)&&item.sample_count>=30;
label.textContent=valid?'백테스트 '+Math.max(0,Math.min(100,Math.round(item.score)))+'점 · 표본 '+item.sample_count+'건':'백테스트 검증 대기';
label.title=valid?'별도 검증된 과거 패턴 점수 · 기존 순위 영향 없음':'연속 분봉과 독립 검증 표본 확보 전까지 점수 미표시';
}}
new MutationObserver(()=>decorate()).observe(body,{childList:true});
refresh();setInterval(refresh,60000);
})();