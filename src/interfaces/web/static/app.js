const tickerInput = document.getElementById("ticker-input");
const researchBtn = document.getElementById("research-btn");
const progressSection = document.getElementById("progress-section");
const progressLog = document.getElementById("progress-log");
const sourcesStrip = document.getElementById("sources-strip");
const resultsSection = document.getElementById("results-section");
const resetBtn = document.getElementById("reset-btn");

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = String(text);
    return div.innerHTML;
}

function logLine(message, cls = "") {
    const div = document.createElement("div");
    div.className = `line ${cls}`;
    div.textContent = message;
    progressLog.appendChild(div);
    progressLog.scrollTop = progressLog.scrollHeight;
}

function clearAll() {
    progressLog.innerHTML = "";
    sourcesStrip.innerHTML = "";
    progressSection.style.display = "none";
    resultsSection.style.display = "none";
}

researchBtn.addEventListener("click", startResearch);
tickerInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") startResearch();
});
resetBtn.addEventListener("click", () => {
    clearAll();
    tickerInput.value = "";
    tickerInput.focus();
});

function startResearch() {
    const ticker = tickerInput.value.trim().toUpperCase();
    if (!ticker) return;
    if (!/^[A-Z]{1,8}$/.test(ticker)) {
        alert("Please enter a valid ticker (1-8 letters).");
        return;
    }

    clearAll();
    progressSection.style.display = "";
    researchBtn.disabled = true;
    logLine(`Researching ${ticker}...`, "success");

    // EventSource is the browser's built-in SSE client.
    const source = new EventSource(`/research/${ticker}`);

    source.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "progress") {
            logLine(data.message);
        } else if (data.type === "source_done") {
            logLine(`✓ ${data.source_name}: ${data.chars} chars extracted`, "success");
            const img = document.createElement("img");
            img.src = `/screenshots/${data.screenshot}`;
            img.alt = data.source_name;
            img.title = data.url;
            img.addEventListener("click", () => window.open(img.src, "_blank"));
            sourcesStrip.appendChild(img);
        } else if (data.type === "complete") {
            logLine("✓ Brief synthesized.", "success");
            renderBrief(data.brief);
            researchBtn.disabled = false;
            source.close();
        } else if (data.type === "error") {
            logLine(`✗ ${data.message}`, "error");
            researchBtn.disabled = false;
            source.close();
        }
    };

    source.onerror = (e) => {
        logLine("✗ Connection lost.", "error");
        researchBtn.disabled = false;
        source.close();
    };
}

function renderBrief(brief) {
    document.getElementById("brief-ticker").textContent = brief.ticker;
    document.getElementById("brief-company").textContent = brief.company_name;
    document.getElementById("brief-summary").textContent = brief.one_line_summary;
    document.getElementById("brief-price").textContent =
        brief.current_price ? `$${brief.current_price.toFixed(2)}` : "—";
    document.getElementById("brief-mcap").textContent = brief.market_cap || "—";
    document.getElementById("brief-pe").textContent =
        brief.pe_ratio ? brief.pe_ratio.toFixed(2) : "—";

    // News
    const newsContainer = document.getElementById("brief-news");
    newsContainer.innerHTML = brief.recent_news.map(n => `
        <div class="news-item">
            <div class="news-header">
                <div class="news-sentiment ${n.sentiment}"></div>
                <div class="news-headline">${escapeHtml(n.headline)}</div>
            </div>
            <div class="news-meta">${escapeHtml(n.source)} · ${escapeHtml(n.age)}</div>
            <div class="news-summary">${escapeHtml(n.summary)}</div>
        </div>
    `).join("");

    // Bull / Bear
    document.getElementById("brief-bull").innerHTML = brief.bull_case
        .map(b => `<li>${escapeHtml(b)}</li>`).join("");
    document.getElementById("brief-bear").innerHTML = brief.bear_case
        .map(b => `<li>${escapeHtml(b)}</li>`).join("");

    // Risks
    document.getElementById("brief-risks").innerHTML = brief.key_risks
        .map(r => `<li>${escapeHtml(r)}</li>`).join("");

    // Confidence + sources
    document.getElementById("brief-confidence").textContent = brief.confidence_note;
    document.getElementById("brief-sources").innerHTML = brief.sources_visited
        .map(s => `<li>${escapeHtml(s)}</li>`).join("");

    resultsSection.style.display = "";
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}