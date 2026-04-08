const TYPE_CLASS = {
  KEYWORD: "t-keyword",
  IDENTIFIER: "t-identifier",
  INTEGER_LITERAL: "t-integer",
  FLOAT_LITERAL: "t-float",
  STRING_LITERAL: "t-string",
  CHAR_LITERAL: "t-char",
  OPERATOR: "t-operator",
  PUNCTUATION: "t-punctuation",
  UNKNOWN: "t-unknown"
};

let currentLanguage = "c";
let history = JSON.parse(localStorage.getItem("ed-history") || "[]");

function setLanguage(lang, btn) {
  currentLanguage = lang;
  document.querySelectorAll(".lang-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  const labelMap = { c: "C Language", cpp: "C++ Language", python: "Python" };
  document.getElementById("lang-label").textContent = labelMap[lang];
  resetOutput();
}

async function runAnalysis() {
  const code = document.getElementById("code-input").value;
  if (!code.trim()) return;

  const btn = document.getElementById("analyze-btn");
  btn.textContent = "Analyzing…";
  btn.classList.add("loading");
  btn.disabled = true;

  try {
    const res = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, language: currentLanguage })
    });
    const result = await res.json();

    history.unshift({
      summary: result.summary,
      has_errors: result.has_errors,
      snippet: code.slice(0, 120),
      time: new Date().toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
    });
    history = history.slice(0, 20);
    localStorage.setItem("ed-history", JSON.stringify(history));

    renderResults(result);
    renderTokens(result.tokens);
    renderHistory();
  } catch (err) {
    showError(err.message);
  } finally {
    btn.textContent = "▶ Analyze Code";
    btn.classList.remove("loading");
    btn.disabled = false;
  }
}

function resetOutput() {
  document.getElementById("results-empty").style.display = "";
  document.getElementById("results-content").style.display = "none";
  document.getElementById("tokens-empty").style.display = "";
  document.getElementById("tokens-content").style.display = "none";
}

function showError(msg) {
  document.getElementById("results-empty").style.display = "none";
  const el = document.getElementById("results-content");
  el.style.display = "block";
  el.innerHTML = `
    <div class="summary-banner error">
      <div class="summary-icon">&#x2715;</div>
      <div>
        <div class="summary-title">Server error</div>
        <div class="summary-sub">${escHtml(msg)}</div>
      </div>
    </div>`;
}

function renderResults(result) {
  document.getElementById("results-empty").style.display = "none";
  const el = document.getElementById("results-content");
  el.style.display = "block";

  const counts = { lexical: 0, syntax: 0, semantic: 0 };
  (result.errors || []).forEach(e => { if (counts[e.phase] !== undefined) counts[e.phase]++; });

  const pillClass = p => counts[p] > 0 ? `${p}-err` : "ok";
  const pillLabel = p => counts[p] > 0 ? `${p} (${counts[p]})` : `${p} &#x2713;`;

  const errCards = (result.errors || []).map(e => `
    <div class="error-card">
      <div class="error-card-header">
        <span class="phase-badge ${e.phase}">${e.phase}</span>
        <span class="error-location">Ln ${e.line}, Col ${e.column}</span>
      </div>
      <div class="error-message">${escHtml(e.message)}</div>
      ${e.token ? `<div class="error-token">Token: <code>${escHtml(e.token)}</code></div>` : ""}
    </div>`).join("");

  el.innerHTML = `
    <div class="summary-banner ${result.has_errors ? "error" : "success"}">
      <div class="summary-icon">${result.has_errors ? "&#x2715;" : "&#x2713;"}</div>
      <div>
        <div class="summary-title">${escHtml(result.summary)}</div>
        <div class="summary-sub">${(result.tokens || []).length} tokens analyzed (${currentLanguage.toUpperCase()})</div>
      </div>
    </div>
    <div class="pipeline">
      <span class="phase-pill ${pillClass("lexical")}">${pillLabel("lexical")}</span>
      <span class="arrow">&#x2192;</span>
      <span class="phase-pill ${pillClass("syntax")}">${pillLabel("syntax")}</span>
      <span class="arrow">&#x2192;</span>
      <span class="phase-pill ${pillClass("semantic")}">${pillLabel("semantic")}</span>
    </div>
    ${result.has_errors ? errCards : ""}`;
}

function renderTokens(tokens) {
  document.getElementById("tokens-empty").style.display = "none";
  const el = document.getElementById("tokens-content");
  el.style.display = "block";

  const rows = (tokens || []).map(t => `
    <div class="token-row">
      <span class="t-pos">${t.line}:${t.column}</span>
      <span class="${TYPE_CLASS[t.type] || "t-unknown"}">${t.type}</span>
      <span class="t-val">${escHtml(t.value === " " ? "SPACE" : t.value)}</span>
    </div>`).join("");

  el.innerHTML = `
    <div style="margin-bottom:6px;font-size:11px;color:#8b949e;">${(tokens||[]).length} tokens total</div>
    <div class="token-header"><span>Ln:Col</span><span>Type</span><span>Value</span></div>
    <div class="token-list">${rows}</div>`;
}

function renderHistory() {
  const el = document.getElementById("history-content");
  if (!history.length) {
    el.innerHTML = `<div class="empty-state"><div class="empty-icon">&#x1F550;</div><p>No history yet.</p></div>`;
    return;
  }
  const items = history.map(item => `
    <div class="history-item">
      <div class="history-item-header">
        <div class="history-status ${item.has_errors ? "err" : "ok"}">
          ${item.has_errors ? "&#x2715;" : "&#x2713;"} ${escHtml(item.summary)}
        </div>
        <span class="history-time">${item.time}</span>
      </div>
      <div class="history-snippet">${escHtml(item.snippet)}</div>
    </div>`).join("");
  el.innerHTML = `
    <div class="history-bar">
      <span class="history-label">Last ${history.length} sessions</span>
      <button class="clear-btn" onclick="clearHistory()">&#x1F5D1; Clear</button>
    </div>${items}`;
}

function clearHistory() {
  history = [];
  localStorage.removeItem("ed-history");
  renderHistory();
}

function switchTab(name, btn) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
  btn.classList.add("active");
  document.getElementById("tab-" + name).classList.add("active");
}

function updateLineNumbers() {
  const ta = document.getElementById("code-input");
  const lines = ta.value.split("\n").length;
  document.getElementById("line-numbers").innerHTML =
    Array.from({ length: Math.max(lines, 1) }, (_, i) =>
      `<div style="height:22px;line-height:22px;">${i + 1}</div>`).join("");
}

function syncScroll() {
  const ta = document.getElementById("code-input");
  document.getElementById("line-numbers").scrollTop = ta.scrollTop;
}

function loadSample() {
  const samples = {
    c: `int main() {\n    int x = 10;\n    int y = 20\n    float z = 3.14;\n\n    total = x + y;\n\n    int bad = 9.99;\n    int w = x @ y;\n\n    return 0;\n}`,
    cpp: `#include<iostream>\nusing namespace std;\n\nint main() {\n    int x = 10\n    cout << x << endl\n    return 0;\n}`,
    python: `def main():\n    x = 10\n    y = 20\n    print(x + y\n\n`
  };
  document.getElementById("code-input").value = samples[currentLanguage];
  updateLineNumbers();
  resetOutput();
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

renderHistory();
updateLineNumbers();
