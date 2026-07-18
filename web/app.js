const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? "").replace(/[&<>"']/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const STR = {
  en: {
    badge: "Private — nothing leaves this device",
    disclaimer: "This is general information, not legal advice.",
    privacySub: "Case Companion runs entirely on this computer. Your documents are never uploaded.",
    dropTitle: "Add a document — drop a PDF or text file, or click to choose",
    uploadingLabel: "Reading the document on this device…",
    emptyHead: "Start by adding a court document",
    emptySub: "A notice, order, motion or letter — Case Companion will explain it in plain language.",
    b1t: "It explains the document",
    b1d: "What it is, what it asks for, and what it means for you — with quotes from the text itself.",
    b2t: "It builds your timeline",
    b2d: "Every dated event goes on one chronological view, past and upcoming.",
    b3t: "It watches your deadlines",
    b3d: "Likely deadlines are computed and labeled presumptive — always confirm them.",
    warnTitle: "Needs your attention", presTag: "Presumptive",
    presNudge: "Confirm with the court or your attorney",
    markDone: "Mark done", tlTitle: "Case timeline", today: "Today",
    docsTitle: "Your documents", noDocs: "No documents yet.",
    noWarnings: "Nothing open. Deadlines appear here when filings trigger them.",
    noEvents: "No events yet. Add a document to begin.",
    passages: (n) => `${n} passage${n === 1 ? "" : "s"} captured`,
    chatTitle: "Ask about your case",
    chatSub: "Answers come only from this case's documents, with the exact passages quoted.",
    askPlaceholder: "Ask a question about this case…", askBtn: "Ask",
    thinking1: "Reading your documents on this device…",
    thinking2: "This can take a minute or two — the first question is the slowest. Nothing is sent anywhere.",
    idkTitle: "Your documents don't answer this.",
    idkBody: "Rather than guess, Case Companion says so when the documents don't cover something. You can add the document that discusses it, or save this as a question for your attorney.",
    idkAdd: "Save for your attorney", srcLabel: "From your documents",
    sug1: "What is this document asking me to do?",
    sug2: "What deadlines do I have coming up?",
    aqTitle: "Ask your attorney",
    aqSub: "Questions collected from flagged sentences, advice checks and your own notes. Check them off once asked.",
    addPlaceholder: "Add a question…", addBtn: "Add",
    noQuestions: "Nothing queued. Items appear when the system notices something worth raising.",
    originFlag: "From a flagged sentence", originAdvice: "From an advice check",
    originManual: "Added by you",
    soTitle: "Second opinion",
    soSub: "Paste advice you were given. Each claim is compared with the captured text of this case's documents — it reports what matches, not whether the advice is right.",
    soPlaceholder: "Paste the advice here…", soBtn: "Check against your documents",
    soExample: "Try an example",
    soChecking: "Comparing with the captured text on this device…",
    soNoClaims: "No checkable claims found in that text.",
    vMatch: "Matches your documents", vDiffer: "Differs from your documents",
    vNot: "Not covered by your documents", vUnclear: "Comparison unclear",
    matchNote: "The captured text says the same thing.",
    differNote: "This isn't a verdict on the advice — it's worth asking about.",
    notCoveredNote: "Nothing in the captured text discusses this.",
    unclearNote: "The comparison was inconclusive — worth asking about.",
    exampleAdvice: "You have 30 days to respond to the complaint. The hearing is at 9 AM. You don't need to file anything before the hearing.",
    revealTitle: "Here's what I found in", rType: "Document type", rFiled: "Filed",
    rSummary: "Summary", rClose: "Got it", flaggedLabel: "Flagged for your attorney",
    rCourt: "Court",
    courtUtah: "Utah state court", courtFed: "Federal court",
    rulesUtah: "Deadlines are computed from Utah state rules",
    rulesFed: "Deadlines are computed from federal rules",
    rEvents: (n) => `${n} event${n === 1 ? "" : "s"} added to your timeline`,
    rDeadlines: (n) => `${n} presumptive deadline${n === 1 ? "" : "s"} computed`,
    rFlags: (n) => `${n} sentence${n === 1 ? "" : "s"} flagged for your attorney`,
    rSatisfied: (n) => `${n} open item${n === 1 ? "" : "s"} marked satisfied by this filing`,
    rChunks: (n) => `${n} passage${n === 1 ? "" : "s"} captured for search`,
    sevOverdue: "Overdue", sevSoon: "Due soon", sevOpen: "Open",
    due: "Due", presDue: "Presumptively due", wasDue: "Was due",
    wasPresDue: "Was presumptively due",
    inDays: (n) => n === 0 ? "today" : n === 1 ? "in 1 day" : `in ${n} days`,
    uploadFailed: "Something went wrong reading that file. Please try again.",
    askFailed: "Something went wrong answering that. Please try again.",
    langApi: "English",
    caseLabel: "Case", newCase: "＋ New case",
    newCasePrompt: "Name this case (e.g. \"Rivera divorce\"):",
    removeDoc: "Remove", removeDocConfirm: (n) =>
      `Remove "${n}" from this case? Its passages, timeline events and flagged questions will be deleted.`,
  },
  es: {
    badge: "Privado — nada sale de este equipo",
    disclaimer: "Esto es información general, no asesoría legal.",
    privacySub: "Case Companion funciona completamente en esta computadora. Sus documentos nunca se suben a internet.",
    dropTitle: "Agregue un documento — arrastre un PDF o archivo de texto, o haga clic para elegir",
    uploadingLabel: "Leyendo el documento en este equipo…",
    emptyHead: "Empiece agregando un documento del tribunal",
    emptySub: "Un aviso, una orden, una moción o una carta — Case Companion se lo explicará en lenguaje sencillo.",
    b1t: "Explica el documento",
    b1d: "Qué es, qué pide y qué significa para usted — con citas del propio texto.",
    b2t: "Construye su cronología",
    b2d: "Cada evento con fecha va a una sola vista cronológica, pasada y futura.",
    b3t: "Vigila sus plazos",
    b3d: "Los plazos probables se calculan y se marcan como presuntos — confírmelos siempre.",
    warnTitle: "Requiere su atención", presTag: "Presunto",
    presNudge: "Confírmelo con el tribunal o con su abogado",
    markDone: "Marcar como hecho", tlTitle: "Cronología del caso", today: "Hoy",
    docsTitle: "Sus documentos", noDocs: "Aún no hay documentos.",
    noWarnings: "Nada pendiente. Los plazos aparecen aquí cuando una presentación los activa.",
    noEvents: "Aún no hay eventos. Agregue un documento para empezar.",
    passages: (n) => `${n} pasaje${n === 1 ? "" : "s"} capturado${n === 1 ? "" : "s"}`,
    chatTitle: "Pregunte sobre su caso",
    chatSub: "Las respuestas provienen solo de los documentos de este caso, con los pasajes exactos citados.",
    askPlaceholder: "Haga una pregunta sobre este caso…", askBtn: "Preguntar",
    thinking1: "Leyendo sus documentos en este equipo…",
    thinking2: "Puede tardar uno o dos minutos — la primera pregunta es la más lenta. No se envía nada a ningún lado.",
    idkTitle: "Sus documentos no responden esto.",
    idkBody: "En vez de adivinar, Case Companion se lo dice cuando los documentos no cubren algo. Puede agregar el documento correspondiente o guardar esto como pregunta para su abogado.",
    idkAdd: "Guardar para su abogado", srcLabel: "De sus documentos",
    sug1: "¿Qué me pide este documento?",
    sug2: "¿Qué plazos tengo próximamente?",
    aqTitle: "Preguntas para su abogado",
    aqSub: "Preguntas reunidas de oraciones señaladas, verificaciones de consejos y sus propias notas. Márquelas cuando las haga.",
    addPlaceholder: "Agregue una pregunta…", addBtn: "Agregar",
    noQuestions: "Nada en la lista. Los elementos aparecen cuando el sistema nota algo que vale la pena preguntar.",
    originFlag: "De una oración señalada", originAdvice: "De una verificación de consejo",
    originManual: "Agregada por usted",
    soTitle: "Segunda opinión",
    soSub: "Pegue un consejo que le dieron. Cada afirmación se compara con el texto capturado de los documentos de este caso — reporta lo que coincide, no si el consejo es correcto.",
    soPlaceholder: "Pegue el consejo aquí…", soBtn: "Comparar con sus documentos",
    soExample: "Probar un ejemplo",
    soChecking: "Comparando con el texto capturado en este equipo…",
    soNoClaims: "No se encontraron afirmaciones verificables en ese texto.",
    vMatch: "Coincide con sus documentos", vDiffer: "Difiere de sus documentos",
    vNot: "Sus documentos no lo cubren", vUnclear: "Comparación no concluyente",
    matchNote: "El texto capturado dice lo mismo.",
    differNote: "Esto no es un veredicto sobre el consejo — vale la pena preguntarlo.",
    notCoveredNote: "Nada en el texto capturado trata este punto.",
    unclearNote: "La comparación no fue concluyente — vale la pena preguntarlo.",
    exampleAdvice: "Tiene 30 días para responder a la demanda. La audiencia es a las 9 AM. No necesita presentar nada antes de la audiencia.",
    revealTitle: "Esto es lo que encontré en", rType: "Tipo de documento", rFiled: "Presentado",
    rSummary: "Resumen", rClose: "Entendido", flaggedLabel: "Señalado para su abogado",
    rCourt: "Tribunal",
    courtUtah: "Tribunal estatal de Utah", courtFed: "Tribunal federal",
    rulesUtah: "Los plazos se calculan con las reglas estatales de Utah",
    rulesFed: "Los plazos se calculan con las reglas federales",
    rEvents: (n) => `${n} evento${n === 1 ? "" : "s"} agregado${n === 1 ? "" : "s"} a su cronología`,
    rDeadlines: (n) => `${n} plazo${n === 1 ? "" : "s"} presunto${n === 1 ? "" : "s"} calculado${n === 1 ? "" : "s"}`,
    rFlags: (n) => `${n} oraci${n === 1 ? "ón señalada" : "ones señaladas"} para su abogado`,
    rSatisfied: (n) => `${n} pendiente${n === 1 ? "" : "s"} satisfecho${n === 1 ? "" : "s"} con esta presentación`,
    rChunks: (n) => `${n} pasaje${n === 1 ? "" : "s"} capturado${n === 1 ? "" : "s"} para búsqueda`,
    sevOverdue: "Vencido", sevSoon: "Vence pronto", sevOpen: "Pendiente",
    due: "Vence", presDue: "Fecha presunta", wasDue: "Venció",
    wasPresDue: "Fecha presunta vencida",
    inDays: (n) => n === 0 ? "hoy" : n === 1 ? "en 1 día" : `en ${n} días`,
    uploadFailed: "Algo salió mal al leer ese archivo. Inténtelo de nuevo.",
    askFailed: "Algo salió mal al responder. Inténtelo de nuevo.",
    langApi: "Spanish",
    caseLabel: "Caso", newCase: "＋ Nuevo caso",
    newCasePrompt: "Nombre de este caso (p. ej. \"Divorcio Rivera\"):",
    removeDoc: "Quitar", removeDocConfirm: (n) =>
      `¿Quitar "${n}" de este caso? Se eliminarán sus pasajes, eventos de cronología y preguntas señaladas.`,
  },
};

const state = {
  lang: localStorage.getItem("cc_lang") || "en",
  uploading: false,
  asking: false, elapsed: 0, timer: null,
  checking: false,
  msgs: [],                 // {kind:'user'|'answer'|'idk'|'error', text, cits, q}
  reveal: null,             // last upload analysis
  jurisdiction: "",         // 'utah' | 'federal' | '' (unknown)
  events: [], warnings: [], questions: [], docs: [],
  cases: [], activeCase: null,
  resolvedLocal: new Set(), // question ids checked this session
  adviceResult: null,
  docMeta: JSON.parse(localStorage.getItem("cc_docmeta") || "{}"),
};

const t = (k) => STR[state.lang][k];
const locale = () => state.lang === "en" ? "en-US" : "es";

function fmtDay(iso) {
  const d = new Date(iso.slice(0, 10) + "T00:00:00");
  return isNaN(d) ? iso : d.toLocaleDateString(locale(), { month: "short", day: "numeric" });
}
function fmtLong(iso) {
  const d = new Date(iso.slice(0, 10) + "T00:00:00");
  return isNaN(d) ? iso
    : d.toLocaleDateString(locale(), { weekday: "short", month: "short", day: "numeric" });
}
const todayISO = () => new Date().toISOString().slice(0, 10);

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}
const post = (path, body) => api(path, {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

/* ---------- static text / language ---------- */

function applyStatic() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-t]").forEach((el) => {
    el.textContent = t(el.dataset.t);
  });
  $("#badge-text").textContent = t("badge");
  $("#empty-head").textContent = t("emptyHead");
  $("#empty-sub").textContent = t("emptySub");
  for (const k of ["b1t", "b1d", "b2t", "b2d", "b3t", "b3d"]) $("#" + k).textContent = t(k);
  $("#q").placeholder = t("askPlaceholder");
  $("#askbtn").textContent = t("askBtn");
  $("#qnew").placeholder = t("addPlaceholder");
  $("#qaddbtn").textContent = t("addBtn");
  $("#advice").placeholder = t("soPlaceholder");
  $("#checkadvice").textContent = t("soBtn");
  $("#fillexample").textContent = t("soExample");
  $("#lang-en").classList.toggle("active", state.lang === "en");
  $("#lang-es").classList.toggle("active", state.lang === "es");
}

function setLang(lang) {
  state.lang = lang;
  localStorage.setItem("cc_lang", lang);
  applyStatic();
  renderAll();
}
$("#lang-en").onclick = () => setLang("en");
$("#lang-es").onclick = () => setLang("es");

/* ---------- upload ---------- */

function setUploading(on) {
  state.uploading = on;
  for (const zone of ["#drop-big", "#drop-small"]) {
    $(zone).querySelector(".drop-idle").classList.toggle("hidden", on);
    $(zone).querySelector(".drop-busy").classList.toggle("hidden", !on);
  }
}

async function uploadFile(file) {
  if (!file || state.uploading) return;
  setUploading(true);
  try {
    const fd = new FormData();
    fd.append("file", file);
    const data = await api("/api/upload", { method: "POST", body: fd });
    state.reveal = { file: file.name, ...data };
    state.docMeta[file.name] = { type: data.doc_type, filed: data.filed_date };
    localStorage.setItem("cc_docmeta", JSON.stringify(state.docMeta));
    await refresh();
  } catch (e) {
    alert(t("uploadFailed"));
  } finally {
    setUploading(false);
    renderAll();
  }
}

function wireDrop(zone) {
  zone.addEventListener("click", () => !state.uploading && $("#file").click());
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("dragover"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("dragover"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("dragover");
    uploadFile(e.dataTransfer.files[0]);
  });
}
wireDrop($("#drop-big"));
wireDrop($("#drop-small"));
$("#file").onchange = (e) => { uploadFile(e.target.files[0]); e.target.value = ""; };

/* ---------- reveal card ---------- */

function renderReveal() {
  const el = $("#reveal");
  const r = state.reveal;
  if (!r) { el.classList.add("hidden"); el.innerHTML = ""; return; }
  const rows = [];
  if (r.events_added) rows.push({ n: r.events_added, t: t("rEvents")(r.events_added) });
  const nd = (r.presumptive_deadlines || []).length;
  if (nd) rows.push({ n: nd, t: t("rDeadlines")(nd), pres: true });
  const nf = (r.faults_flagged || []).length;
  if (nf) rows.push({ n: nf, t: t("rFlags")(nf) });
  const ns = (r.obligations_satisfied || []).length;
  if (ns) rows.push({ n: ns, t: t("rSatisfied")(ns) });
  if (!rows.length) rows.push({ n: r.chunks_added || 0, t: t("rChunks")(r.chunks_added || 0) });

  const summary = r.key_facts && r.key_facts.summary && r.key_facts.summary !== "Not stated"
    ? r.key_facts.summary : "";
  const quote = nf ? r.faults_flagged[0].quote : "";
  const court = r.jurisdiction === "utah" ? t("courtUtah")
    : r.jurisdiction === "federal" ? t("courtFed") : "";

  el.className = "reveal";
  el.innerHTML = `
    <div class="reveal-title">${esc(t("revealTitle"))} <span class="mono-chip">${esc(r.file)}</span></div>
    <div class="reveal-meta">
      <div><div class="meta-label">${esc(t("rType"))}</div><div class="meta-value">${esc(r.doc_type || "—")}</div></div>
      <div><div class="meta-label">${esc(t("rFiled"))}</div><div class="meta-value">${esc(r.filed_date ? fmtLong(r.filed_date) : "—")}</div></div>
      ${court ? `<div><div class="meta-label">${esc(t("rCourt"))}</div><div class="meta-value">${esc(court)}</div></div>` : ""}
    </div>
    ${summary ? `<div class="reveal-quote"><div class="meta-label">${esc(t("rSummary"))}</div><div class="serif-quote">${esc(summary)}</div></div>` : ""}
    <div class="reveal-rows">
      ${rows.map((row) => `<div class="reveal-row"><div class="reveal-n">${row.n}</div>
        <div class="reveal-row-t">${esc(row.t)}</div>
        ${row.pres ? `<span class="pres-tag">${esc(t("presTag"))}</span>` : ""}</div>`).join("")}
    </div>
    ${quote ? `<div class="reveal-quote"><div class="meta-label">${esc(t("flaggedLabel"))}</div><div class="serif-quote">“${esc(quote)}”</div></div>` : ""}
    <div><button id="reveal-close" class="btn-primary" style="padding:8px 18px;font-size:13.5px">${esc(t("rClose"))}</button></div>`;
  $("#reveal-close").onclick = () => { state.reveal = null; renderReveal(); };
}

/* ---------- warnings ---------- */

function warnDueText(w) {
  if (!w.due_date) return w.presumptive ? t("presNudge") : "";
  const base = fmtLong(w.due_date);
  let text;
  if (w.urgency === "overdue") {
    text = `${w.presumptive ? t("wasPresDue") : t("wasDue")} ${base}`;
  } else {
    const days = Math.round((new Date(w.due_date) - new Date(todayISO())) / 86400000);
    text = `${w.presumptive ? t("presDue") : t("due")} ${base}`;
    if (w.urgency === "due_soon") text += ` · ${t("inDays")(days)}`;
  }
  if (w.presumptive) text += ` — ${t("presNudge")}`;
  return text;
}

function renderWarnings() {
  const sevLabel = { overdue: t("sevOverdue"), due_soon: t("sevSoon"), open: t("sevOpen") };
  $("#warn-count").textContent = state.warnings.length || "";
  $("#warnings").innerHTML = state.warnings.length
    ? state.warnings.map((w) => `
      <div class="warn ${w.urgency}">
        <div class="warn-tags">
          <span class="sev">${esc(sevLabel[w.urgency])}</span>
          ${w.presumptive ? `<span class="pres-tag">${esc(t("presTag"))}</span>` : ""}
        </div>
        <div class="warn-title">${esc(w.label)}</div>
        <div class="warn-due">${esc(warnDueText(w))}</div>
        <div><button class="btn-small" data-id="${w.id}">${esc(t("markDone"))}</button></div>
      </div>`).join("")
    : `<p class="list-empty">${esc(t("noWarnings"))}</p>`;
  $("#warnings").querySelectorAll("button").forEach((b) => {
    b.onclick = async () => {
      const data = await post("/api/obligations/satisfy", { id: parseInt(b.dataset.id, 10) });
      state.warnings = data.warnings;
      renderWarnings();
    };
  });
}

/* ---------- timeline ---------- */

function renderTimeline() {
  const today = todayISO();
  const rows = state.events.map((e) => {
    let label = e.label, sub = "";
    const m = label.match(/\s*\(PRESUMPTIVE[^;)]*(?:;\s*(.*))?\)\s*$/);
    if (m) { sub = m[1] || ""; label = label.slice(0, m.index); }
    const day = (e.when || "").slice(0, 10);
    const kind = e.kind === "presumptive_deadline" ? "pres" : day > today ? "future" : "past";
    return { day, date: fmtDay(e.when), label, sub, kind };
  });
  const idx = rows.findIndex((r) => r.day > today);
  const todayRow = { day: today, date: fmtDay(today), label: t("today"), kind: "today" };
  if (idx === -1) rows.push(todayRow); else rows.splice(idx, 0, todayRow);

  $("#timeline").innerHTML = state.events.length
    ? rows.map((r) => `
      <div class="tl-row ${r.kind}">
        <div class="tl-date">${esc(r.date)}</div>
        <div class="tl-spine"><div class="tl-dot"></div><div class="tl-line"></div></div>
        <div class="tl-body">
          <div class="tl-title">${esc(r.label)}</div>
          ${r.kind === "pres" ? `<div class="tl-pres-line">
              <span class="pres-tag">${esc(t("presTag"))}</span>
              <span class="pres-nudge">${esc(t("presNudge"))}</span></div>` : ""}
          ${r.sub ? `<div class="tl-sub">· ${esc(r.sub)}</div>` : ""}
        </div>
      </div>`).join("")
    : `<p class="list-empty">${esc(t("noEvents"))}</p>`;
}

/* ---------- documents ---------- */

function renderDocs() {
  $("#docs").innerHTML = state.docs.length
    ? state.docs.map((d) => {
        const meta = state.docMeta[d.source];
        const line = meta
          ? `${meta.type}${meta.filed ? ` · ${t("rFiled")} ${fmtLong(meta.filed)}` : ""}`
          : t("passages")(d.chunks);
        return `<div class="doc">
          <div class="doc-icon">${esc((d.source.split(".").pop() || "DOC").toUpperCase().slice(0, 4))}</div>
          <div class="doc-info">
            <div class="doc-name">${esc(d.source)}</div>
            <div class="doc-meta">${esc(line)}</div>
          </div>
          <button class="doc-remove" data-src="${esc(d.source)}" title="${esc(t("removeDoc"))}">✕</button>
        </div>`;
      }).join("")
    : `<p class="list-empty">${esc(t("noDocs"))}</p>`;
  $("#docs").querySelectorAll(".doc-remove").forEach((b) => {
    b.onclick = () => removeDoc(b.dataset.src);
  });
}

async function removeDoc(source) {
  if (!confirm(t("removeDocConfirm")(source))) return;
  await post("/api/documents/remove", { source });
  // Clear the reveal card if it was for this doc, and drop local meta.
  if (state.reveal && state.reveal.file === source) state.reveal = null;
  delete state.docMeta[source];
  localStorage.setItem("cc_docmeta", JSON.stringify(state.docMeta));
  await refresh();
}

/* ---------- chat ---------- */

function renderChat() {
  const log = $("#chatlog");
  log.innerHTML = state.msgs.map((m, i) => {
    if (m.kind === "user") return `<div class="msg-user">${esc(m.text)}</div>`;
    if (m.kind === "idk") return `
      <div class="msg-idk">
        <div class="idk-title">${esc(t("idkTitle"))}</div>
        <div class="idk-body">${esc(t("idkBody"))}</div>
        <button class="btn-small" data-save="${i}">${esc(t("idkAdd"))}</button>
      </div>`;
    if (m.kind === "error") return `<div class="msg-idk"><div class="idk-body">${esc(m.text)}</div></div>`;
    const cits = (m.cits || []).map((c) => `
      <div class="cit">
        <div class="serif-quote">“${esc(c.quote)}”</div>
        <div class="cit-src"><span class="mono-chip">${esc(c.doc)}</span></div>
      </div>`).join("");
    return `<div class="msg-answer">
      <div class="msg-answer-text">${esc(m.text)}</div>
      ${cits ? `<div class="cits"><div class="cits-label">${esc(t("srcLabel"))}</div>${cits}</div>` : ""}
    </div>`;
  }).join("");
  log.querySelectorAll("[data-save]").forEach((b) => {
    b.onclick = async () => {
      const m = state.msgs[parseInt(b.dataset.save, 10)];
      const data = await post("/api/questions/add", { question: m.q });
      state.questions = data.questions;
      b.disabled = true;
      renderQuestions();
    };
  });
  log.scrollTop = log.scrollHeight;

  $("#thinking").classList.toggle("hidden", !state.asking);
  $("#elapsed").textContent = state.asking ? `${state.elapsed}s` : "";
  $("#askbtn").disabled = state.asking;

  const chips = $("#chips");
  if (!state.asking && state.msgs.length < 4 && state.docs.length) {
    chips.innerHTML = [t("sug1"), t("sug2")]
      .map((s) => `<button class="chip">${esc(s)}</button>`).join("");
    chips.querySelectorAll(".chip").forEach((c) => { c.onclick = () => ask(c.textContent); });
  } else chips.innerHTML = "";
}

async function ask(question) {
  const q = (question || "").trim();
  if (!q || state.asking) return;
  state.msgs.push({ kind: "user", text: q });
  state.asking = true;
  state.elapsed = 0;
  $("#q").value = "";
  clearInterval(state.timer);
  state.timer = setInterval(() => {
    state.elapsed += 1;
    $("#elapsed").textContent = `${state.elapsed}s`;
  }, 1000);
  renderChat();
  try {
    const data = await post("/api/ask", { question: q, language: t("langApi") });
    if (!data.grounded) {
      state.msgs.push({ kind: "idk", q });
    } else {
      const text = data.answer.replace(/\s*\[Source \d+\]/g, "");
      const seen = new Set();
      const cits = (data.sources || []).filter((s) => {
        const key = s.source + s.text.slice(0, 60);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      }).slice(0, 3).map((s) => ({ doc: s.source, quote: s.text }));
      state.msgs.push({ kind: "answer", text, cits });
    }
  } catch (e) {
    state.msgs.push({ kind: "error", text: t("askFailed") });
  } finally {
    clearInterval(state.timer);
    state.asking = false;
    renderChat();
  }
}

$("#askform").onsubmit = (e) => { e.preventDefault(); ask($("#q").value); };

/* ---------- attorney questions ---------- */

function originLabel(q) {
  if (q.source === "user") return t("originManual");
  if (q.source === "advice check") return t("originAdvice");
  return t("originFlag");
}

function renderQuestions() {
  $("#questions").innerHTML = state.questions.length
    ? state.questions.map((q) => {
        const resolved = state.resolvedLocal.has(q.id);
        return `<div class="q-item${resolved ? " resolved" : ""}">
          <button class="q-check" data-id="${q.id}" ${resolved ? "disabled" : ""}>${resolved ? "✓" : ""}</button>
          <div class="q-body">
            <div class="q-text">${esc(q.question)}</div>
            ${q.context_quote ? `<div class="q-quote">“${esc(q.context_quote)}”</div>` : ""}
            <div class="q-origin">${esc(originLabel(q))}</div>
          </div>
        </div>`;
      }).join("")
    : `<p class="list-empty">${esc(t("noQuestions"))}</p>`;
  $("#questions").querySelectorAll(".q-check").forEach((b) => {
    b.onclick = async () => {
      const id = parseInt(b.dataset.id, 10);
      state.resolvedLocal.add(id);
      renderQuestions();
      await post("/api/questions/resolve", { id });
    };
  });
}

$("#qform").onsubmit = async (e) => {
  e.preventDefault();
  const q = $("#qnew").value.trim();
  if (!q) return;
  $("#qnew").value = "";
  const data = await post("/api/questions/add", { question: q });
  state.questions = data.questions;
  renderQuestions();
};

/* ---------- second opinion ---------- */

const VERDICT = {
  matches: { cls: "match", label: "vMatch", note: "matchNote" },
  conflicts: { cls: "differ", label: "vDiffer", note: "differNote" },
  not_covered: { cls: "not", label: "vNot", note: "notCoveredNote" },
  unclear: { cls: "not", label: "vUnclear", note: "unclearNote" },
};

function renderAdvice() {
  const box = $("#adviceresult");
  $("#checking").classList.toggle("hidden", !state.checking);
  $("#checkadvice").disabled = state.checking;
  const res = state.adviceResult;
  if (!res) { box.classList.add("hidden"); box.innerHTML = ""; return; }
  box.classList.remove("hidden");
  box.innerHTML = (res.claims.length
    ? res.claims.map((c) => {
        const v = VERDICT[c.verdict] || VERDICT.unclear;
        return `<div class="claim ${v.cls}">
          <span class="verdict">${esc(t(v.label))}</span>
          <div class="claim-text">“${esc(c.claim)}”</div>
          ${c.quote ? `<div class="claim-quote">
            <div class="serif-quote">“${esc(c.quote)}”</div>
            ${c.source ? `<span class="mono-chip">${esc(c.source)}</span>` : ""}
          </div>` : ""}
          <div class="claim-note">${esc(t(v.note))}</div>
        </div>`;
      }).join("")
    : `<p class="list-empty">${esc(t("soNoClaims"))}</p>`)
    + (res.note ? `<div class="advice-note">${esc(res.note)}</div>` : "");
}

$("#fillexample").onclick = () => { $("#advice").value = t("exampleAdvice"); };
$("#checkadvice").onclick = async () => {
  const text = $("#advice").value.trim();
  if (!text || state.checking) return;
  state.checking = true;
  state.adviceResult = null;
  renderAdvice();
  try {
    state.adviceResult = await post("/api/check-advice", { text });
    const data = await api("/api/questions");
    state.questions = data.questions;
    renderQuestions();
  } finally {
    state.checking = false;
    renderAdvice();
  }
};

/* ---------- data loading / top-level render ---------- */

async function refresh() {
  const [tl, warn, qs, docs, cs] = await Promise.all([
    api("/api/timeline"), api("/api/warnings"), api("/api/questions"),
    api("/api/documents").catch(() => ({ documents: [] })),
    api("/api/case").catch(() => ({ jurisdiction: "" })),
  ]);
  state.events = tl.events;
  state.warnings = warn.warnings;
  state.questions = qs.questions;
  state.docs = docs.documents;
  state.jurisdiction = cs.jurisdiction;
  renderAll();
}

function renderCasebar() {
  const j = state.jurisdiction;
  $("#casebar").classList.toggle("hidden", !j);
  if (!j) return;
  $("#casebar-court").textContent = j === "utah" ? t("courtUtah") : t("courtFed");
  $("#casebar-rules").textContent = j === "utah" ? t("rulesUtah") : t("rulesFed");
}

/* ---------- cases ---------- */

function renderCases() {
  $("#case-label").textContent = t("caseLabel");
  $("#case-new").textContent = t("newCase");
  const sel = $("#case-select");
  sel.innerHTML = state.cases
    .map((c) => `<option value="${c.id}"${c.id === state.activeCase ? " selected" : ""}>${esc(c.name)}</option>`)
    .join("");
}

async function loadCases() {
  const data = await api("/api/cases");
  state.cases = data.cases;
  state.activeCase = data.active_id;
  renderCases();
}

// Switching a case resets all per-case UI, then reloads that case's data.
async function switchCase(id) {
  const data = await post("/api/cases/switch", { id });
  state.cases = data.cases;
  state.activeCase = data.active_id;
  state.reveal = null;
  state.msgs = [];
  state.adviceResult = null;
  state.resolvedLocal = new Set();
  renderCases();
  await refresh();
}

$("#case-select").onchange = (e) => switchCase(parseInt(e.target.value, 10));
$("#case-new").onclick = async () => {
  const name = prompt(t("newCasePrompt"));
  if (name === null) return;               // cancelled
  const data = await post("/api/cases", { name });
  state.cases = data.cases;
  state.activeCase = data.active_id;
  state.reveal = null;
  state.msgs = [];
  state.adviceResult = null;
  state.resolvedLocal = new Set();
  renderCases();
  await refresh();
};

function renderAll() {
  const empty = !state.events.length && !state.docs.length;
  $("#empty").classList.toggle("hidden", !empty);
  $("#app").classList.toggle("hidden", empty);
  renderCases();
  renderCasebar();
  renderReveal();
  renderWarnings();
  renderTimeline();
  renderDocs();
  renderChat();
  renderQuestions();
  renderAdvice();
}

applyStatic();
loadCases().then(refresh);
