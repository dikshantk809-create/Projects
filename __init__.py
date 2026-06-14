<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MilkMate AI</title>
<style>
  :root{
    --ink:#1a1207; --paper:#fbf7ef; --card:#ffffff; --line:#e8dcc8;
    --cream:#f3ead8; --gold:#c8920f; --gold-deep:#a3760a;
    --green:#2f7a4d; --red:#b3402f; --muted:#8a7a5e;
    --shadow:0 1px 3px rgba(60,40,10,.08),0 8px 24px rgba(60,40,10,.06);
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
    background:var(--paper);color:var(--ink);line-height:1.5;-webkit-font-smoothing:antialiased}
  .wrap{max-width:1080px;margin:0 auto;padding:0 18px}
  /* header */
  header{background:linear-gradient(180deg,#fffdf8,#fbf7ef);border-bottom:1px solid var(--line);
    position:sticky;top:0;z-index:20}
  .bar{display:flex;align-items:center;gap:14px;padding:14px 0}
  .logo{display:flex;align-items:center;gap:10px;font-weight:800;font-size:20px;letter-spacing:-.02em}
  .drop{width:30px;height:30px;border-radius:50% 50% 50% 4px;
    background:radial-gradient(circle at 32% 30%,#fff,var(--gold) 75%);
    box-shadow:inset 0 -3px 6px rgba(0,0,0,.12)}
  .logo small{font-weight:600;font-size:11px;color:var(--gold-deep);
    background:var(--cream);padding:2px 7px;border-radius:20px;letter-spacing:.04em}
  nav{margin-left:auto;display:flex;gap:4px;background:var(--cream);padding:4px;border-radius:12px}
  nav button{font:inherit;font-weight:600;font-size:13px;border:0;background:transparent;
    color:var(--muted);padding:8px 16px;border-radius:9px;cursor:pointer;transition:.15s}
  nav button.on{background:var(--card);color:var(--ink);box-shadow:var(--shadow)}
  /* layout */
  .view{display:none;padding:26px 0 60px;animation:rise .3s ease}
  .view.on{display:block}
  @keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  h2{font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
    color:var(--gold-deep);margin-bottom:14px}
  .grid{display:grid;gap:16px}
  .kpis{grid-template-columns:repeat(4,1fr)}
  .card{background:var(--card);border:1px solid var(--line);border-radius:16px;
    padding:18px;box-shadow:var(--shadow)}
  .kpi .n{font-size:30px;font-weight:800;letter-spacing:-.02em;line-height:1}
  .kpi .l{font-size:12px;color:var(--muted);margin-top:6px;font-weight:600}
  .kpi .n.g{color:var(--green)} .kpi .n.r{color:var(--red)}
  .two{grid-template-columns:1.3fr 1fr;align-items:start}
  /* form */
  label{display:block;font-size:12px;font-weight:700;color:var(--muted);margin:0 0 5px}
  input,select{width:100%;font:inherit;padding:11px 12px;border:1px solid var(--line);
    border-radius:10px;background:#fffdf9;color:var(--ink)}
  input:focus,select:focus{outline:2px solid var(--gold);border-color:transparent}
  .row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
  .btn{font:inherit;font-weight:700;border:0;border-radius:11px;padding:12px 18px;cursor:pointer;
    background:var(--gold);color:#3a2700;transition:.15s;width:100%}
  .btn:hover{background:var(--gold-deep);color:#fff}
  .btn.ghost{background:var(--cream);color:var(--ink)}
  /* whatsapp */
  .wa{background:#0b1f17;border-radius:16px;padding:16px;color:#dceee2}
  .wa h3{font-size:13px;margin-bottom:12px;color:#7fd9a3;letter-spacing:.04em}
  .chat{display:flex;flex-direction:column;gap:8px;max-height:240px;overflow:auto;margin-bottom:12px}
  .msg{max-width:82%;padding:8px 12px;border-radius:12px;font-size:13px;line-height:1.4}
  .msg.in{align-self:flex-end;background:#1f6b45;border-bottom-right-radius:3px}
  .msg.out{align-self:flex-start;background:#15352a;border-bottom-left-radius:3px;white-space:pre-line}
  .waform{display:flex;gap:8px}
  .waform input{background:#15352a;border-color:#27513f;color:#fff}
  .waform .btn{width:auto;background:#25d366;color:#062b18}
  /* calendar */
  .cal{display:grid;grid-template-columns:repeat(7,1fr);gap:6px}
  .dow{font-size:11px;font-weight:700;color:var(--muted);text-align:center;padding:4px 0}
  .day{aspect-ratio:1;border:1px solid var(--line);border-radius:10px;padding:5px 6px;
    font-size:11px;display:flex;flex-direction:column;background:#fffdf9}
  .day.empty{border:0;background:transparent}
  .day .d{font-weight:700;color:var(--muted)}
  .day.has{background:linear-gradient(180deg,#fff,#fcf6e9);border-color:var(--gold)}
  .day .q{margin-top:auto;font-weight:800;font-size:12px}
  .day .a{font-size:10px;color:var(--green);font-weight:700}
  /* bills table */
  table{width:100%;border-collapse:collapse;font-size:14px}
  th{text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;
    color:var(--muted);padding:10px 12px;border-bottom:2px solid var(--line)}
  td{padding:12px;border-bottom:1px solid var(--line)}
  tr:last-child td{border-bottom:0}
  .pill{font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px}
  .pill.pending{background:#fbe9c4;color:#8a5a05}
  .pill.paid{background:#d6efdf;color:var(--green)}
  .link{color:var(--gold-deep);font-weight:700;cursor:pointer;border:0;background:0;font:inherit}
  /* ai */
  .ai-chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}
  .chip{font:inherit;font-size:12px;font-weight:600;border:1px solid var(--line);
    background:#fffdf9;padding:7px 13px;border-radius:20px;cursor:pointer}
  .chip:hover{border-color:var(--gold);background:var(--cream)}
  .ai-log{display:flex;flex-direction:column;gap:10px;min-height:60px}
  .ai-q{align-self:flex-end;background:var(--gold);color:#3a2700;padding:8px 13px;
    border-radius:12px;font-size:13px;font-weight:600;max-width:75%}
  .ai-a{align-self:flex-start;background:var(--cream);padding:10px 13px;border-radius:12px;
    font-size:13px;max-width:80%;white-space:pre-line}
  .toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%) translateY(80px);
    background:var(--ink);color:#fff;padding:12px 20px;border-radius:12px;font-weight:600;
    font-size:14px;box-shadow:var(--shadow);transition:.3s;z-index:50}
  .toast.show{transform:translateX(-50%)}
  .mt{margin-top:16px}
  @media(max-width:760px){.kpis{grid-template-columns:1fr 1fr}.two{grid-template-columns:1fr}
    nav button{padding:8px 11px}.logo small{display:none}}
</style>
</head>
<body>
<header><div class="wrap bar">
  <div class="logo"><span class="drop"></span>MilkMate <small>AI</small></div>
  <nav>
    <button class="on" data-v="seller">Seller</button>
    <button data-v="customer">Customer</button>
    <button data-v="ai">AI Assistant</button>
  </nav>
</div></header>

<main class="wrap">
  <!-- SELLER -->
  <section class="view on" id="seller">
    <h2>Dashboard — Sharma Dairy</h2>
    <div class="grid kpis">
      <div class="card kpi"><div class="n" id="k-cust">0</div><div class="l">Customers</div></div>
      <div class="card kpi"><div class="n g" id="k-rev">₹0</div><div class="l">Total billed</div></div>
      <div class="card kpi"><div class="n r" id="k-pend">₹0</div><div class="l">Pending</div></div>
      <div class="card kpi"><div class="n" id="k-milk">0L</div><div class="l">Milk delivered</div></div>
    </div>

    <div class="grid two mt">
      <div class="card">
        <h2>Add milk entry</h2>
        <div class="row">
          <div><label>Customer</label><select id="f-cust"></select></div>
          <div><label>Date</label><input type="date" id="f-date"></div>
        </div>
        <div class="row">
          <div><label>Morning (L)</label><input type="number" id="f-m" value="1" step="0.5" min="0"></div>
          <div><label>Evening (L)</label><input type="number" id="f-e" value="1" step="0.5" min="0"></div>
        </div>
        <div class="row">
          <div><label>Rate (₹/L)</label><input type="number" id="f-rate" value="60"></div>
          <div style="display:flex;align-items:flex-end"><button class="btn" onclick="addManual()">Save entry</button></div>
        </div>
      </div>

      <div class="wa">
        <h3>📱 WhatsApp — type like a seller would</h3>
        <div class="chat" id="wa-chat"></div>
        <div class="waform">
          <input id="wa-in" placeholder="e.g. Dikshant Morning 1L Evening 1L" onkeydown="if(event.key==='Enter')waSend()">
          <button class="btn" onclick="waSend()">Send</button>
        </div>
      </div>
    </div>

    <div class="card mt">
      <h2>Customers</h2>
      <table><thead><tr><th>Name</th><th>Rate</th><th>This month</th><th>Bill</th><th>Status</th></tr></thead>
      <tbody id="cust-rows"></tbody></table>
    </div>
  </section>

  <!-- CUSTOMER -->
  <section class="view" id="customer">
    <h2>Customer Portal — <span id="c-name">Dikshant</span></h2>
    <div class="grid kpis">
      <div class="card kpi"><div class="n" id="c-today">0L</div><div class="l">Today's milk</div></div>
      <div class="card kpi"><div class="n g" id="c-todayamt">₹0</div><div class="l">Today's amount</div></div>
      <div class="card kpi"><div class="n" id="c-month">0L</div><div class="l">This month</div></div>
      <div class="card kpi"><div class="n r" id="c-bill">₹0</div><div class="l">Current bill</div></div>
    </div>

    <div class="card mt">
      <h2 style="display:flex;justify-content:space-between;align-items:center">
        <span id="cal-label">June 2026</span>
        <button class="link" onclick="downloadInvoice()">⬇ Download invoice</button>
      </h2>
      <div class="cal" id="cal"></div>
    </div>

    <div class="card mt">
      <h2>Monthly records — stored forever, never merged</h2>
      <table><thead><tr><th>Month</th><th>Litres</th><th>Amount</th><th>Status</th><th></th></tr></thead>
      <tbody id="month-rows"></tbody></table>
    </div>
  </section>

  <!-- AI -->
  <section class="view" id="ai">
    <h2>AI Assistant — ask about your account</h2>
    <div class="card">
      <div class="ai-chips" id="ai-chips"></div>
      <div class="ai-log" id="ai-log"></div>
    </div>
  </section>
</main>

<div class="toast" id="toast"></div>

<script>
/* ---------- The billing engine, in the browser (same logic as billing.py) ---------- */
const MONTHS=["Jan","Feb","Mar","Apr","May","June","July","Aug","Sep","Oct","Nov","Dec"];
const today = {y:2026,m:6,d:14};         // demo "today"
let customers = [
  {id:1,name:"Dikshant",rate:60},
  {id:2,name:"Priya",rate:55},
  {id:3,name:"Ramesh",rate:60},
];
let entries = [];   // {custId, y, m, d, morning, evening, rate}
let paidMonths = {}; // key `${id}-${y}-${m}` -> true

function entryTotal(e){return (e.morning+e.evening);}
function entryAmt(e){return Math.round(entryTotal(e)*e.rate*100)/100;}

function upsert(custId,y,m,d,morning,evening,rate){
  let e = entries.find(x=>x.custId===custId&&x.y===y&&x.m===m&&x.d===d);
  if(e){e.morning=morning;e.evening=evening;e.rate=rate;}
  else entries.push({custId,y,m,d,morning,evening,rate});
}
function monthBill(custId,y,m){
  const es=entries.filter(e=>e.custId===custId&&e.y===y&&e.m===m);
  const qty=es.reduce((s,e)=>s+entryTotal(e),0);
  const amt=es.reduce((s,e)=>s+entryAmt(e),0);
  const paid=paidMonths[`${custId}-${y}-${m}`];
  return {qty:Math.round(qty*100)/100,amt:Math.round(amt*100)/100,
          status:paid?"paid":"pending",count:es.length};
}

/* ---------- seed some history so it looks alive ---------- */
function seed(){
  const plan={1:{6:[1,2,1,1,2,1,2,1,1,2,1,1],7:[2,1,2]},2:{6:[2,2,1,2,2,1]},3:{6:[1,1,1,1]}};
  for(const id in plan)for(const m in plan[id])
    plan[id][m].forEach((q,i)=>{const c=customers.find(x=>x.id==id);
      upsert(+id,2026,+m,i+1,q,0,c.rate);});
  paidMonths["1-2026-7"]=true; // Dikshant July paid
}
seed();

/* ---------- render ---------- */
const $=s=>document.querySelector(s);
function money(n){return "₹"+n.toLocaleString("en-IN");}

function renderSeller(){
  let rev=0,pend=0,milk=0;
  customers.forEach(c=>{
    [6,7].forEach(m=>{const b=monthBill(c.id,2026,m);rev+=b.amt;milk+=b.qty;
      if(b.status==="pending")pend+=b.amt;});
  });
  $("#k-cust").textContent=customers.length;
  $("#k-rev").textContent=money(rev);
  $("#k-pend").textContent=money(pend);
  $("#k-milk").textContent=Math.round(milk)+"L";

  $("#cust-rows").innerHTML=customers.map(c=>{
    const b=monthBill(c.id,today.y,today.m);
    return `<tr><td><b>${c.name}</b></td><td>₹${c.rate}/L</td>
      <td>${b.qty}L</td><td>${money(b.amt)}</td>
      <td><span class="pill ${b.status}">${b.status}</span></td></tr>`;
  }).join("");

  const sel=$("#f-cust");
  sel.innerHTML=customers.map(c=>`<option value="${c.id}">${c.name}</option>`).join("");
}

let curCust=1;
function renderCustomer(){
  const c=customers.find(x=>x.id===curCust);
  $("#c-name").textContent=c.name;
  const te=entries.find(e=>e.custId===c.id&&e.y===today.y&&e.m===today.m&&e.d===today.d);
  $("#c-today").textContent=(te?entryTotal(te):0)+"L";
  $("#c-todayamt").textContent=money(te?entryAmt(te):0);
  const b=monthBill(c.id,today.y,today.m);
  $("#c-month").textContent=b.qty+"L";
  $("#c-bill").textContent=money(b.amt);

  // calendar
  $("#cal-label").textContent=`${MONTHS[today.m-1]} ${today.y}`;
  const first=new Date(today.y,today.m-1,1).getDay();
  const days=new Date(today.y,today.m,0).getDate();
  let html=["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].map(d=>`<div class="dow">${d}</div>`).join("");
  for(let i=0;i<first;i++)html+=`<div class="day empty"></div>`;
  for(let d=1;d<=days;d++){
    const e=entries.find(x=>x.custId===c.id&&x.y===today.y&&x.m===today.m&&x.d===d);
    html+=`<div class="day ${e?'has':''}"><span class="d">${d}</span>`+
      (e?`<span class="q">${entryTotal(e)}L</span><span class="a">₹${entryAmt(e)}</span>`:``)+`</div>`;
  }
  $("#cal").innerHTML=html;

  // months
  const rows=[];
  [6,7].forEach(m=>{const mb=monthBill(c.id,2026,m);if(mb.count)
    rows.push(`<tr><td><b>${MONTHS[m-1]} 2026</b></td><td>${mb.qty}L</td>
      <td>${money(mb.amt)}</td><td><span class="pill ${mb.status}">${mb.status}</span></td>
      <td><button class="link" onclick="downloadInvoice(${m})">Invoice</button></td></tr>`);});
  $("#month-rows").innerHTML=rows.join("")||`<tr><td colspan=5>No records yet</td></tr>`;
}

/* ---------- WhatsApp parser (same rules as whatsapp_parser.py) ---------- */
function parseMsg(text){
  let t=text.trim(),rate=null;
  const rm=t.match(/@\s*(\d+(?:\.\d+)?)/);if(rm){rate=+rm[1];t=t.replace(rm[0],"");}
  let m=0,e=0,split=false;
  const mm=t.match(/(?:morning|subah|\bm\b)\s*(\d+(?:\.\d+)?)\s*l?/i);
  if(mm){m=+mm[1];split=true;t=t.replace(mm[0],"");}
  const em=t.match(/(?:evening|shaam|\be\b)\s*(\d+(?:\.\d+)?)\s*l?/i);
  if(em){e=+em[1];split=true;t=t.replace(em[0],"");}
  if(!split){const q=t.match(/(\d+(?:\.\d+)?)\s*l\b/i)||t.match(/\b(\d+(?:\.\d+)?)\b/);
    if(!q)throw "No quantity found";m=+q[1];t=t.replace(q[0],"");}
  const name=t.replace(/[^a-zA-Z\u0900-\u097F\s]/g," ").trim().replace(/\s+/g," ");
  if(!name)throw "No customer name found";
  return {name,m,e,rate};
}

function waMsg(cls,txt){const c=$("#wa-chat");
  c.innerHTML+=`<div class="msg ${cls}">${txt}</div>`;c.scrollTop=c.scrollHeight;}

function waSend(){
  const inp=$("#wa-in");const raw=inp.value.trim();if(!raw)return;
  waMsg("in",raw);inp.value="";
  let p;try{p=parseMsg(raw);}catch(err){waMsg("out","⚠️ "+err);return;}
  const c=customers.find(x=>x.name.toLowerCase()===p.name.toLowerCase());
  if(!c){waMsg("out",`⚠️ No customer named "${p.name}"`);return;}
  const rate=p.rate||c.rate;
  upsert(c.id,today.y,today.m,today.d,p.m,p.e,rate);
  const e={morning:p.m,evening:p.e,rate};
  const b=monthBill(c.id,today.y,today.m);
  waMsg("out",`✅ ${c.name} — ${today.d} ${MONTHS[today.m-1]}\n`+
    `Today: ${entryTotal(e)}L = ${money(entryAmt(e))}\n`+
    `This month: ${b.qty}L | Bill: ${money(b.amt)}`);
  refresh();toast(`Saved ${c.name}: ${entryTotal(e)}L`);
}

function addManual(){
  const id=+$("#f-cust").value;
  const dv=$("#f-date").value;
  const dt=dv?new Date(dv):new Date(today.y,today.m-1,today.d);
  upsert(id,dt.getFullYear(),dt.getMonth()+1,dt.getDate(),
    +$("#f-m").value||0,+$("#f-e").value||0,+$("#f-rate").value||0);
  refresh();toast("Entry saved");
}

/* ---------- AI assistant (answers from real data) ---------- */
const aiQ=["What is my bill?","How much milk this month?","Show my payment history",
  "Show July bill","Predict this month's bill"];
function renderAIChips(){$("#ai-chips").innerHTML=aiQ.map(q=>
  `<button class="chip" onclick="ask('${q}')">${q}</button>`).join("");}

function ask(q){
  const log=$("#ai-log");
  log.innerHTML+=`<div class="ai-q">${q}</div>`;
  const c=customers.find(x=>x.id===curCust);
  const b=monthBill(c.id,today.y,today.m);
  let a="";
  if(/bill/i.test(q)&&/july|jul/i.test(q)){const jb=monthBill(c.id,2026,7);
    a=`Your July 2026 bill is ${money(jb.amt)} for ${jb.qty}L — status: ${jb.status}.`;}
  else if(/predict/i.test(q)){const days=new Date(today.y,today.m,0).getDate();
    const perDay=b.count?b.amt/b.count:0;const proj=Math.round(perDay*days);
    a=`So far this month: ${money(b.amt)} over ${b.count} days.\nAt this pace, projected month-end bill ≈ ${money(proj)}.`;}
  else if(/history/i.test(q)){const lines=[6,7].map(m=>{const mb=monthBill(c.id,2026,m);
    return mb.count?`• ${MONTHS[m-1]} 2026: ${money(mb.amt)} — ${mb.status}`:null;}).filter(Boolean);
    a="Payment history:\n"+lines.join("\n");}
  else if(/milk|litre|liter/i.test(q)){a=`You've taken ${b.qty}L of milk this month (${MONTHS[today.m-1]} 2026).`;}
  else{a=`Your current bill for ${MONTHS[today.m-1]} 2026 is ${money(b.amt)} (${b.qty}L), status: ${b.status}.`;}
  log.innerHTML+=`<div class="ai-a">${a}</div>`;
  log.scrollTop=log.scrollHeight;
}

/* ---------- invoice (text download — real PDF is server-side) ---------- */
function downloadInvoice(m){
  m=m||today.m;const c=customers.find(x=>x.id===curCust);
  const es=entries.filter(e=>e.custId===c.id&&e.y===2026&&e.m===m).sort((a,b)=>a.d-b.d);
  const b=monthBill(c.id,2026,m);
  let txt=`SHARMA DAIRY — MILK INVOICE\n`;
  txt+=`Customer: ${c.name}\nMonth: ${MONTHS[m-1]} 2026\nRate: ₹${c.rate}/L\n`;
  txt+=`${"-".repeat(34)}\nDate   Qty     Amount\n`;
  es.forEach(e=>txt+=`${String(e.d).padStart(2,"0")} Jun  ${entryTotal(e)}L     ₹${entryAmt(e)}\n`);
  txt+=`${"-".repeat(34)}\nTotal: ${b.qty}L = ₹${b.amt}\nStatus: ${b.status.toUpperCase()}\n`;
  const blob=new Blob([txt],{type:"text/plain"});
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);
  a.download=`invoice-${c.name}-${MONTHS[m-1]}2026.txt`;a.click();
  toast("Invoice downloaded");
}

/* ---------- plumbing ---------- */
function refresh(){renderSeller();renderCustomer();}
function toast(t){const el=$("#toast");el.textContent=t;el.classList.add("show");
  setTimeout(()=>el.classList.remove("show"),1800);}
document.querySelectorAll("nav button").forEach(b=>b.onclick=()=>{
  document.querySelectorAll("nav button").forEach(x=>x.classList.remove("on"));
  document.querySelectorAll(".view").forEach(x=>x.classList.remove("on"));
  b.classList.add("on");$("#"+b.dataset.v).classList.add("on");
});
$("#f-date").value=`2026-06-${String(today.d).padStart(2,"0")}`;
renderAIChips();refresh();
waMsg("out","👋 Send a message like:\nDikshant 2L\nPriya Morning 1L Evening 1L\nRamesh 1.5L @ 60");
</script>
</body>
</html>
