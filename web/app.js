const $ = (s) => document.querySelector(s);
const chat = $("#chat");
let lastSources = [];

function bubble(text, who) {
  const d = document.createElement("div");
  d.className = "msg " + who;
  d.innerHTML = `<span class="bubble">${text}</span>`;
  chat.appendChild(d);
  chat.scrollTop = chat.scrollHeight;
  return d;
}

function linkCitations(text) {
  return text.replace(/\[Source (\d+)\]/g,
    (m, n) => `<span class="cite" data-i="${n}">${m}</span>`);
}

// Upload
$("#drop").onclick = () => $("#file").click();
$("#file").onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  $("#drop").textContent = "Reading " + file.name + "…";
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch("/api/upload", { method: "POST", body: fd });
  const data = await r.json();
  renderFacts(data.key_facts);
  $("#drop").textContent = "Uploaded " + file.name + " — drop another to add";
  loadTimeline();
};

function renderFacts(f) {
  const card = $("#facts");
  card.classList.remove("hidden");
  const rows = [
    ["Summary", f.summary], ["Parties", f.parties],
    ["Deadline", f.deadline], ["Amount", f.amount],
    ["Action required", f.action_required],
  ].map(([k, v]) => `<div class="facts-row"><b>${k}</b><span>${v}</span></div>`).join("");
  const risks = (f.risks || []).map((r) => `<div class="risk">⚠️ ${r}</div>`).join("");
  card.innerHTML = `<h3>Key facts</h3>${rows}${risks}
    <button id="asklawyer">✉️ Ask my lawyer about this</button>`;
  $("#asklawyer").onclick = () => draftLawyer(f.deadline);
}

async function draftLawyer(keyFact) {
  const q = prompt("What do you want to ask your lawyer?");
  if (!q) return;
  const r = await fetch("/api/draft-lawyer", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: q, key_fact: keyFact }),
  });
  const d = await r.json();
  window.location.href =
    `mailto:?subject=${encodeURIComponent(d.subject)}&body=${encodeURIComponent(d.body)}`;
}

// Ask
$("#askform").onsubmit = async (e) => {
  e.preventDefault();
  const q = $("#q").value.trim();
  if (!q) return;
  bubble(q, "you");
  $("#q").value = "";
  const thinking = bubble("…", "bot");
  const r = await fetch("/api/ask", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: q, language: $("#lang").value }),
  });
  const data = await r.json();
  lastSources = data.sources || [];
  thinking.querySelector(".bubble").innerHTML = linkCitations(data.answer);
};

// Citation click reveals snippet
chat.onclick = (e) => {
  if (!e.target.classList.contains("cite")) return;
  const i = parseInt(e.target.dataset.i, 10) - 1;
  const src = lastSources[i];
  if (!src) return;
  const s = document.createElement("div");
  s.className = "snippet";
  s.textContent = `${src.source}: ${src.text}`;
  e.target.closest(".msg").appendChild(s);
};

// Timeline
async function loadTimeline() {
  const r = await fetch("/api/timeline");
  const { events } = await r.json();
  $("#timeline").innerHTML = "<h3>Case timeline</h3>" + (events.length
    ? events.map((e) =>
        `<div class="tl-item"><span class="tl-when">${e.when}</span><span>${e.label}</span></div>`).join("")
    : "<p>No events yet. Upload a document to begin.</p>");
}

// Offline indicator
function updateNet() {
  const el = $("#net");
  if (navigator.onLine) { el.textContent = "🌐 Online"; el.classList.remove("off"); }
  else { el.textContent = "🔒 Offline — still working"; el.classList.add("off"); }
}
window.addEventListener("online", updateNet);
window.addEventListener("offline", updateNet);
updateNet();
loadTimeline();
