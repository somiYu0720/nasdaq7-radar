/* Price action supplementary panel. No changes to scoring, rankings or collection. */
(function(){
"use strict";
const KEY="kitty_price_action_history_v1";
const MAX=40;
function num(x){const n=Number(x);return Number.isFinite(n)?n:null}
function read(){try{return JSON.parse(localStorage.getItem(KEY))||{}}catch(_){return {}}}
function save(v){try{localStorage.setItem(KEY,JSON.stringify(v))}catch(_){}}
function classify(a){
 if(a.length<5)return "데이터 부족 · 연속 관측 5개 이상 필요";
 const t=a.slice(-5),l=t.map(x=>x.low),h=t.map(x=>x.high),c=t.map(x=>x.close);
 if(t.some(x=>[x.low,x.high,x.close].some(v=>v===null)))return "데이터 부족";
 const lowsUp=l.slice(1).every((v,i)=>v>=l[i]);
 const range1=Math.max(...h.slice(0,3))-Math.min(...l.slice(0,3));
 const range2=Math.max(...h.slice(2))-Math.min(...l.slice(2));
 if(lowsUp&&l[4]>l[0])return "저점 상승 관찰";
 if(range1>0&&range2<range1*.65)return "가격 압축 관찰";
 if(c[4]>Math.max(...h.slice(0,4)))return "최근 관측 고점 돌파 시도";
 if(Math.min(...l.slice(2))>=Math.min(...l.slice(0,3))&&c[4]>=c[2])return "저점 방어 가능성";
 return "뚜렷한 가격 구조 신호 없음";
}
function el(tag,txt){const e=document.createElement(tag);if(txt!==undefined)e.textContent=txt;return e}
let box;
async function refresh(){
 if(!box)return;
 try{
  const r=await fetch("./toss_live.json?price_action="+Date.now(),{cache:"no-store"});
  if(!r.ok)throw Error("HTTP "+r.status);
  const d=await r.json(),history=read();
  const nas=Array.isArray(d.nasdaq7)?d.nasdaq7:[],china=Array.isArray(d.china1)?d.china1:[];
  const combined=[...nas.map(x=>({...x,lane:"NASDAQ 7.0"})),...china.map(x=>({...x,lane:"중국계 1.0"}))];
  const tbody=box.querySelector("tbody");tbody.replaceChildren();
  for(const x of combined){
   const ticker=String(x.ticker||"").toUpperCase();if(!ticker)continue;
   const k=x.lane+":"+ticker,bar=String(x.bar_time||x.quote_time||"");
   const low=num(x.low),high=num(x.high),close=num(x.close??x.price_usd);
   let arr=Array.isArray(history[k])?history[k]:[];
   if(bar&&low!==null&&high!==null&&close!==null&&!arr.some(y=>y.bar===bar)){
    arr.push({bar,low,high,close});arr=arr.sort((a,b)=>Date.parse(a.bar)-Date.parse(b.bar)).slice(-MAX);history[k]=arr;
   }
   const tr=el("tr");
   for(const v of [x.lane,ticker,close===null?"—":close.toFixed(4),classify(arr),arr.length+"개"])tr.appendChild(el("td",v));
   tbody.appendChild(tr);
  }
  save(history);
  box.querySelector(".pa-status").textContent="최근 수집: "+(d.updated_utc||"확인 불가")+" · 브라우저에 관측 기록 저장";
 }catch(e){box.querySelector(".pa-status").textContent="데이터 연결 오류: "+e.message}
}
function init(){
 const main=document.querySelector("main");if(!main)return;
 box=el("section");box.className="panel";box.id="kitty-price-action";
 const title=el("h2","저점·가격 움직임 (보조 분석)");box.appendChild(title);
 const note=el("p","수집된 분봉의 저점·고점·종가를 비교합니다. 브라우저에 누적된 관측만 사용하며, 수집 공백이 있으면 연속 1분봉으로 간주하지 않습니다.");note.className="note";box.appendChild(note);
 const status=el("p","데이터 확인 중");status.className="muted pa-status";box.appendChild(status);
 const scroll=el("div");scroll.className="scroll";
 const table=el("table"),head=el("thead"),tr=el("tr");
 for(const h of ["구분","티커","최근 종가($)","저점·가격 움직임","관측 수"])tr.appendChild(el("th",h));
 head.appendChild(tr);table.appendChild(head);table.appendChild(el("tbody"));scroll.appendChild(table);box.appendChild(scroll);
 main.appendChild(box);refresh();setInterval(()=>{if(!document.hidden)refresh()},60000);
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();