/* Separate read-only analysis panel. Does not change live collector or TOP10 scoring. */
(function(){
  const panel=document.createElement('section');
  panel.id='radar-analysis-upload';
  panel.style.cssText='margin:18px 12px;padding:16px;border:1px solid #315572;border-radius:16px;background:#0c1b2d;color:#d8efff;font-family:inherit';
  const title=document.createElement('h3');title.textContent='📋 GPT 레이더 분석 업로드 · NASDAQ 7.0 / 중국계 1.0';title.style.cssText='margin:0 0 8px;font-size:17px';panel.append(title);
  const note=document.createElement('p');note.style.cssText='font-size:12px;opacity:.8;line-height:1.6';panel.append(note);
  const content=document.createElement('div');panel.append(content);
  function renderList(name,arr){
    const h=document.createElement('h4');h.textContent=name+' · '+arr.length+'종목';h.style.cssText='margin:14px 0 7px;color:#80e4ec';content.append(h);
    const table=document.createElement('table');table.style.cssText='width:100%;border-collapse:collapse;font-size:13px;text-align:left';
    const head=document.createElement('tr');['순위','티커','수집 1분 거래량'].forEach(v=>{const th=document.createElement('th');th.textContent=v;th.style.cssText='padding:7px;border-bottom:1px solid #315572';head.append(th)});table.append(head);
    arr.forEach(x=>{const tr=document.createElement('tr');[x.rank,x.ticker,Number(x.minute_volume).toLocaleString('ko-KR')].forEach(v=>{const td=document.createElement('td');td.textContent=String(v);td.style.cssText='padding:7px;border-bottom:1px solid #22394c';tr.append(td)});table.append(tr)});content.append(table);
  }
  async function refresh(){
    try{const r=await fetch('./radar_analysis_2026-10-27.json?t='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);const d=await r.json();content.replaceChildren();note.textContent='분석 스냅샷: '+new Date(d.generated_at).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'})+' · 과거 분석 자료 (실시간 순위 아님) · 뉴스/SEC 및 가속 검증 전 · 기존 실시간 TOP10과 별도';renderList('NASDAQ 7.0',d.nasdaq7||[]);renderList('중국계 1.0',d.china1||[])}catch(e){note.textContent='분석 파일을 불러오지 못했습니다: '+e.message}
  }
  document.body.append(panel);refresh();
})();
