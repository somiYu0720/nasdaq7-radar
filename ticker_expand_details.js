/* TOP10 ticker expandable diagnostic panel; isolated from ranking and collection logic. */
(()=>{'use strict';
const tbody=document.getElementById('rankRows');if(!tbody)return;
const fields=['가격·거래량','저점 방어','숏커버','이벤트·SEC','공급·희석','진입·손익비'];
const clean=v=>String(v||'').trim().toUpperCase();
const mk=(tag,txt)=>{const e=document.createElement(tag);e.textContent=txt;return e};
const status=(label,value)=>{const p=mk('p','');const b=mk('strong',label+'  ');p.append(b,document.createTextNode(value));return p};
let selected='';
function close(){tbody.querySelectorAll('tr.radar-detail-row').forEach(e=>e.remove());tbody.querySelectorAll('[aria-expanded]').forEach(e=>e.setAttribute('aria-expanded','false'));}
function open(row){
 const cells=row.cells;if(!cells||cells.length<5)return;
 const ticker=clean(cells[1].textContent).match(/[A-Z][A-Z0-9.]{0,9}/)?.[0];if(!ticker)return;
 if(selected===ticker&&row.nextElementSibling?.classList.contains('radar-detail-row')){close();selected='';return;}
 close();selected=ticker;row.setAttribute('aria-expanded','true');
 const detail=document.createElement('tr');detail.className='radar-detail-row';const td=document.createElement('td');td.colSpan=cells.length;
 const panel=document.createElement('div');panel.className='radar-detail-panel';panel.append(mk('h3',ticker+' · 조기포착 정밀 진단'));
 panel.append(status('포착 점수',cells[7]?.textContent?.trim()||'미확인'));
 panel.append(status('1분 거래량',cells[4]?.textContent?.trim()||'미확인'));
 panel.append(status('거래량 가속',cells[5]?.textContent?.trim()||'계산대기'));
 panel.append(status('가격 변화',cells[6]?.textContent?.trim()||'미확인'));
 const grid=document.createElement('div');grid.className='radar-detail-grid';
 const descriptions=[
 '거래량 증가만으로 매집 확정 불가. RVOL 3배 이상·5~15분 가속·가격 반응 확인 필요.',
 '저점이 높아지는지, 하락 중 거래량이 감소하는지 확인. 실시간 캔들 미검증.',
 '가격 방어와 거래량 재가속이 동반될 때 가능성 관찰. 최신 공매도 잔고·대차 비용 미검증.',
 '공식 발표일·원문·확정 여부 확인 필요. 기대 이벤트와 확정 이벤트 구분.',
 'ATM·워런트·전환·재판매·상장유지 위험은 2차 SEC 검증. 미확인을 안전으로 간주 금지.',
 '실시간 현재가·지지선·변동성 확인 전 진입가/손절가/목표가 산출 보류.'
 ];
 fields.forEach((f,i)=>{const box=document.createElement('div');box.className='radar-detail-item';box.append(mk('strong',f),mk('p',descriptions[i]));grid.append(box)});panel.append(grid);
 panel.append(mk('p','판정: 1차 관찰 후보 · V20 SEC 및 실시간 데이터 검증 전 매수 신호 아님.'));
 td.append(panel);detail.append(td);row.after(detail);
}
tbody.addEventListener('click',e=>{if(e.target.closest('.radar-detail-row')||e.target.closest('a,button,input,select'))return;const row=e.target.closest('tr');if(row&&row.parentElement===tbody)open(row)});
const obs=new MutationObserver(()=>{if(selected&&!tbody.querySelector('.radar-detail-row'))selected='';});obs.observe(tbody,{childList:true});
})();