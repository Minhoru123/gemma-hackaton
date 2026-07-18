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
  $("#drop").textContent = "Uploaded " + file.name +
    ` (read as: ${data.doc_type}) — drop another to add`;
  loadTimeline();
  loadWarnings();
  loadQuestions();
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
    <button id="asklawyer">➕ Add a question for my attorney</button>`;
  $("#asklawyer").onclick = addOwnQuestion;
}

async function addOwnQuestion() {
  const q = prompt("What do you want to ask your attorney?");
  if (!q) return;
  await fetch("/api/questions/add", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: q }),
  });
  loadQuestions();
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
        `<div class="tl-item${e.kind === "presumptive_deadline" ? " presumptive" : ""}">` +
        `<span class="tl-when">${e.when}</span><span>${e.label}</span></div>`).join("")
    : "<p>No events yet. Upload a document to begin.</p>");
}

// Warnings (open obligations)
async function loadWarnings() {
  const r = await fetch("/api/warnings");
  const { warnings } = await r.json();
  const label = { overdue: "⏰ OVERDUE", due_soon: "⚠️ Due soon", open: "Open" };
  $("#warnings").innerHTML = "<h3>Warnings & to-do</h3>" + (warnings.length
    ? warnings.map((w) =>
        `<div class="warn ${w.urgency}"><span><b>${label[w.urgency]}</b> ${w.label}` +
        (w.due_date ? ` — due ${w.due_date}` : "") +
        (w.presumptive ? " <em>(presumptive — confirm with your attorney)</em>" : "") +
        `</span><button data-id="${w.id}">Done</button></div>`).join("")
    : "<p>Nothing open. Deadlines appear here when filings trigger them.</p>");
  $("#warnings").querySelectorAll("button").forEach((b) => {
    b.onclick = async () => {
      await fetch("/api/obligations/satisfy", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: parseInt(b.dataset.id, 10) }),
      });
      loadWarnings();
    };
  });
}

// Ask-your-attorney list
async function loadQuestions() {
  const r = await fetch("/api/questions");
  const { questions } = await r.json();
  $("#questions").innerHTML = "<h3>Ask your attorney</h3>" + (questions.length
    ? questions.map((q) =>
        `<div class="q-item"><span>${q.question}</span>` +
        `<button data-id="${q.id}">Asked</button></div>`).join("")
    : "<p>Nothing queued. Items appear when the system notices something worth raising.</p>");
  $("#questions").querySelectorAll("button").forEach((b) => {
    b.onclick = async () => {
      await fetch("/api/questions/resolve", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: parseInt(b.dataset.id, 10) }),
      });
      loadQuestions();
    };
  });
}

// Second opinion (advice cross-check)
$("#checkadvice").onclick = async () => {
  const text = $("#advice").value.trim();
  if (!text) return;
  $("#adviceresult").innerHTML = "<p>Checking each claim…</p>";
  const r = await fetch("/api/check-advice", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  const data = await r.json();
  const word = { matches: "matches captured text", conflicts: "conflicts with captured text",
                 not_covered: "not covered by captured text", unclear: "unclear" };
  $("#adviceresult").innerHTML = (data.claims.length
    ? data.claims.map((c) =>
        `<div class="claim ${c.verdict}"><span class="verdict">${word[c.verdict]}</span>` +
        `<div>${c.claim}</div>` +
        (c.quote ? `<span class="quote">"${c.quote}" — ${c.source}</span>` : "") +
        `</div>`).join("")
    : "<p>No checkable claims found in that text.</p>") +
    `<p class="hint">${data.note}</p>`;
  loadQuestions();
};

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
loadWarnings();
loadQuestions();
