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

  async function renderOtherCategories(){
    const block=document.createElement('div');block.id='radar-other-categories';content.append(block);
    try{
      const [wr,tr]=await Promise.all([fetch('./watchlist.json?t='+Date.now(),{cache:'no-store'}),fetch('./toss_live.json?t='+Date.now(),{cache:'no-store'})]);
      if(!wr.ok||!tr.ok)throw Error('자료 수집 대기');
      const watch=(await wr.json()).categories||{},toss=await tr.json();
      const data=[...(toss.nasdaq7||[]),...(toss.china1||[])],byTicker=new Map();
      data.forEach(x=>{if(x&&x.ticker){const old=byTicker.get(x.ticker);if(!old||Date.parse(x.candle_time||0)>Date.parse(old.candle_time||0))byTicker.set(x.ticker,x)}});
      const names={volume:'거래량 선행',oversold:'과매도',event:'이벤트 임박',funding:'자금조달',reignite:'재점화',favorite:'관심종목'};
      const caveat=document.createElement('p');caveat.style.cssText='font-size:12px;opacity:.85;line-height:1.6';caveat.textContent='아래는 기존 카테고리 감시목록과 토스 최근 분봉의 교차조회입니다. 거래량은 급증 배수가 아니며 과매도 원인·이벤트 일정·희석·재점화 여부는 미검증입니다. 실시간 TOP10 점수에 반영하지 않습니다.';block.append(caveat);
      Object.entries(names).forEach(([key,label])=>{
        const symbols=Array.isArray(watch[key])?watch[key]:[];
        const rows=symbols.map(ticker=>({ticker,x:byTicker.get(ticker)})).filter(o=>o.x).map(o=>({...o,ms:Date.parse(o.x.candle_time||o.x.quote_time||''),volume:Number(o.x.minute_volume)}));
        const cutoff=Date.parse(toss.updated_utc||'')-600000;
        const fresh=rows.filter(o=>Number.isFinite(o.ms)&&o.ms>=cutoff&&Number.isFinite(o.volume)).sort((a,b)=>b.volume-a.volume);
        const heading=document.createElement('h4');heading.style.cssText='margin:16px 0 6px;color:#80e4ec';heading.textContent=label+' · 감시 '+symbols.length+'종목 · 최근 분봉 '+fresh.length+'종목';block.append(heading);
        const summary=document.createElement('p');summary.style.cssText='font-size:12px;opacity:.8;margin:0 0 6px';summary.textContent=key==='oversold'?'급락 원인 및 RSI 미검증':key==='event'?'확정 일정 및 이벤트 강도 미검증':key==='funding'?'SEC 원문·즉시 매도 가능 공급 미검증':key==='reignite'?'과거 대비 재점화 가속 미검증':'거래량 가속 배수 및 가격 변화 미검증';block.append(summary);
        if(!fresh.length){const p=document.createElement('p');p.textContent='최근 10분 이내 분봉 확인 종목 없음';p.style.cssText='font-size:12px;opacity:.7';block.append(p);return}
        const table=document.createElement('table');table.style.cssText='width:100%;border-collapse:collapse;font-size:13px;text-align:left';
        const head=document.createElement('tr');['티커','최근 1분 거래량','분봉 시각(KST)'].forEach(t=>{const th=document.createElement('th');th.textContent=t;th.style.cssText='padding:6px;border-bottom:1px solid #315572';head.append(th)});table.append(head);
        fresh.slice(0,10).forEach(o=>{const tr=document.createElement('tr');[o.ticker,o.volume.toLocaleString('ko-KR'),new Date(o.ms).toLocaleTimeString('ko-KR',{timeZone:'Asia/Seoul',hour:'2-digit',minute:'2-digit'})].forEach(v=>{const td=document.createElement('td');td.textContent=v;td.style.cssText='padding:6px;border-bottom:1px solid #22394c';tr.append(td)});table.append(tr)});block.append(table);
      });
    }catch(e){block.textContent='추가 카테고리 자료 연결 대기: '+e.message}
  }
  async function refresh(){
    try{const r=await fetch('./radar_analysis_2026-10-27.json?t='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);const d=await r.json();content.replaceChildren();note.textContent='분석 스냅샷: '+new Date(d.generated_at).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'})+' · 과거 분석 자료 (실시간 순위 아님) · 뉴스/SEC 및 가속 검증 전 · 기존 실시간 TOP10과 별도';renderList('NASDAQ 7.0',d.nasdaq7||[]);renderList('중국계 1.0',d.china1||[]);await renderOtherCategories()}catch(e){note.textContent='분석 파일을 불러오지 못했습니다: '+e.message}
  }
  document.body.append(panel);refresh();
})();
