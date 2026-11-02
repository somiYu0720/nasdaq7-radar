/* Evidence-first expandable TOP10 diagnostics. No fabricated values. */
(()=>{'use strict';const tbody=document.getElementById('rankRows');if(!tbody)return;
const el=(tag,text)=>{const n=document.createElement(tag);n.textContent=text;return n};
const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null};
const fmt=n=>n==null?'미확인':n.toLocaleString('ko-KR');
let active='',generation=0;
const cached={};
async function getJSON(path){const r=await fetch(path+'?t='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('fetch');return r.json()}
function list(d){return Array.isArray(d.rows)?d.rows:[...(d.nasdaq7||[]),...(d.china1||[])];}
function add(panel,name,value,source){const box=el('div','');box.className='radar-detail-item';box.append(el('strong',name),el('p',value));if(source)box.append(el('small',source));panel.append(box)}
function clear(){tbody.querySelectorAll('.radar-detail-row').forEach(x=>x.remove());tbody.querySelectorAll('tr[aria-expanded]').forEach(x=>x.setAttribute('aria-expanded','false'))}
async function open(row){const cells=row.cells;if(!cells||cells.length<8)return;const ticker=(cells[1].textContent||'').trim().match(/[A-Z][A-Z0-9.]{0,9}/)?.[0];if(!ticker)return;
if(active===ticker&&row.nextElementSibling?.classList.contains('radar-detail-row')){clear();active='';return}
clear();active=ticker;const request=++generation;row.setAttribute('aria-expanded','true');const tr=el('tr','');tr.className='radar-detail-row';const td=el('td','');td.colSpan=cells.length;const panel=el('div','');panel.className='radar-detail-panel';panel.append(el('h3',ticker+' · 데이터 기반 진단'));td.append(panel);tr.append(td);row.after(tr);
panel.append(el('p','데이터 확인 중…'));
try{
const d=await getJSON('./toss_live.json');if(request!==generation||active!==ticker)return;panel.replaceChildren(el('h3',ticker+' · 데이터 기반 진단'));
const x=list(d).find(v=>v.ticker===ticker);const grid=el('div','');grid.className='radar-detail-grid';panel.append(grid);
const stamp=Date.parse(d.updated_utc||'');const bar=Date.parse(x?.bar_time||'');const fresh=Number.isFinite(stamp)&&Date.now()-stamp>=-120000&&Date.now()-stamp<300000&&Number.isFinite(bar)&&Math.abs(stamp-bar)<300000;
add(grid,'포착 점수',cells[7].textContent.trim(),'기존 TOP10 산정 점수 · 상승 확률 아님');
add(grid,'1분 거래량',x&&fresh?fmt(num(x.minute_volume))+'주':'수집 시각 경과 또는 데이터 없음',fresh?'Toss 1분봉 · '+new Date(bar).toLocaleString('ko-KR'):'실시간 미확인');
add(grid,'가격',x&&fresh&&num(x.price_usd??x.price)!=null?'$'+num(x.price_usd??x.price).toFixed(4):'가격 데이터 대기');
const acc=cells[5]?.textContent.trim()||'';add(grid,'거래량 가속',acc.includes('계산대기')?'비교봉 부족':acc,'현재 TOP10 계산 결과 · 연속 1분봉 확보 필요');
const low=num(x?.low),high=num(x?.high),close=num(x?.close);add(grid,'저점 방어',fresh&&low!=null&&high!=null&&close!=null&&high>low?'현재 1분봉 종가 위치 '+((close-low)/(high-low)*100).toFixed(0)+'% · 연속 저점 방어는 미검증':'연속 캔들 검증 대기','단일 봉만으로 매집 확정 불가');
add(grid,'숏커버','공매도 잔고·대차 비용 데이터 대기','가격·거래량만으로 숏커버 확정 불가');
add(grid,'이벤트·SEC','최신 종목별 공식 공시 검증 대기','확정 일정 및 원문 미연결');
add(grid,'공급·희석','최신 SEC 공급 물량 검증 대기','미확인을 저위험으로 표시하지 않음');
add(grid,'진입·손익비','지지선·손절·목표가 데이터 대기','검증 전 임의 가격 산출 금지');
panel.append(el('p','1차 관찰 후보 · 미검증 항목은 매수 신호가 아님.'));
}catch(e){if(request===generation&&active===ticker){panel.replaceChildren(el('h3',ticker+' · 데이터 기반 진단'),el('p','데이터 연결 실패 · 실시간 검증 불가'));}}
}
tbody.addEventListener('click',e=>{if(e.target.closest('.radar-detail-row')||e.target.closest('a,button,input,select'))return;const row=e.target.closest('tr');if(row?.parentElement===tbody)open(row)});
})();