// ──────────────── State ────────────────
let tickerData = [];
let activeSuggestionIndex = -1;

// ──────────────── Element refs ────────────────
const tickerInput = document.getElementById("ticker-input");
const researchBtn = document.getElementById("research-btn");
const progressSection = document.getElementById("progress-section");
const progressLog = document.getElementById("progress-log");
const sourcesStrip = document.getElementById("sources-strip");
const resultsSection = document.getElementById("results-section");
const resetBtn = document.getElementById("reset-btn");

// ──────────────── Init ────────────────
async function init() {
    try {
        const response = await fetch("/ui/tickers.json");
        tickerData = await response.json();
        console.log(`Loaded ${tickerData.length} tickers`);
    } catch (e) {
        console.error("Failed to load tickers:", e);
    }
    setupAutocomplete();
}

// ──────────────── Autocomplete ────────────────
function setupAutocomplete() {
    const dropdown = document.getElementById("autocomplete-dropdown");
    
    tickerInput.addEventListener("input", () => {
        const query = tickerInput.value.trim().toLowerCase();
        showSuggestions(query);
    });
    
    tickerInput.addEventListener("keydown", (e) => {
        const items = dropdown.querySelectorAll(".autocomplete-item");
        if (e.key === "ArrowDown") {
            e.preventDefault();
            activeSuggestionIndex = Math.min(activeSuggestionIndex + 1, items.length - 1);
            updateActiveSuggestion(items);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            activeSuggestionIndex = Math.max(activeSuggestionIndex - 1, -1);
            updateActiveSuggestion(items);
        } else if (e.key === "Enter") {
            if (activeSuggestionIndex >= 0 && items[activeSuggestionIndex]) {
                e.preventDefault();
                pickSuggestion(items[activeSuggestionIndex].dataset.ticker);
            } else {
                startResearch();
            }
        } else if (e.key === "Escape") {
            dropdown.style.display = "none";
        }
    });
    
    document.addEventListener("click", (e) => {
        if (!tickerInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = "none";
        }
    });
}

function showSuggestions(query) {
    const dropdown = document.getElementById("autocomplete-dropdown");
    if (!query) {
        dropdown.innerHTML = "";
        dropdown.style.display = "none";
        return;
    }
    
    const tickerMatches = tickerData.filter(t => t.ticker.toLowerCase().startsWith(query));
    const nameMatches = tickerData.filter(t =>
        !t.ticker.toLowerCase().startsWith(query) &&
        t.name.toLowerCase().includes(query)
    );
    const top = [...tickerMatches, ...nameMatches].slice(0, 8);
    
    if (top.length === 0) {
        dropdown.innerHTML = `<div class="autocomplete-empty">Press Enter to search "${escapeHtml(query.toUpperCase())}" anyway.</div>`;
        dropdown.style.display = "block";
        return;
    }
    
    dropdown.innerHTML = top.map((t, i) => `
        <div class="autocomplete-item" data-ticker="${t.ticker}" data-index="${i}">
            <span class="ac-ticker">${escapeHtml(t.ticker)}</span>
            <span class="ac-name">${escapeHtml(t.name)}</span>
        </div>
    `).join("");
    dropdown.style.display = "block";
    activeSuggestionIndex = -1;
    
    dropdown.querySelectorAll(".autocomplete-item").forEach(item => {
        item.addEventListener("click", () => pickSuggestion(item.dataset.ticker));
        item.addEventListener("mouseenter", () => {
            activeSuggestionIndex = parseInt(item.dataset.index);
            updateActiveSuggestion(dropdown.querySelectorAll(".autocomplete-item"));
        });
    });
}

function updateActiveSuggestion(items) {
    items.forEach((item, i) => item.classList.toggle("active", i === activeSuggestionIndex));
}

function pickSuggestion(ticker) {
    tickerInput.value = ticker;
    document.getElementById("autocomplete-dropdown").style.display = "none";
    startResearch();
}

// ──────────────── Helpers ────────────────
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

// ──────────────── Research flow ────────────────
researchBtn.addEventListener("click", startResearch);
resetBtn.addEventListener("click", () => {
    clearAll();
    tickerInput.value = "";
    tickerInput.focus();
    window.scrollTo({ top: 0, behavior: "smooth" });
});

function startResearch() {
    const ticker = tickerInput.value.trim().toUpperCase();
    if (!ticker) return;
    if (!/^[A-Z.]{1,8}$/.test(ticker)) {
        alert("Please enter a valid ticker (1-8 letters).");
        return;
    }

    document.getElementById("autocomplete-dropdown").style.display = "none";
    clearAll();
    progressSection.style.display = "";
    researchBtn.disabled = true;
    logLine(`Reading about ${ticker}...`, "success");

    const source = new EventSource(`/research/${ticker}`);

    source.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "progress") {
            logLine(data.message);
        } else if (data.type === "source_done") {
            logLine(`Got ${data.chars.toLocaleString()} characters from ${data.source_name}`, "success");
            const img = document.createElement("img");
            img.src = `/screenshots/${data.screenshot}`;
            img.alt = data.source_name;
            img.title = data.url;
            img.addEventListener("click", () => window.open(img.src, "_blank"));
            sourcesStrip.appendChild(img);
        } else if (data.type === "complete") {
            logLine("Done. Writing it up...", "success");
            renderExplainer(data.brief);
            researchBtn.disabled = false;
            source.close();
        } else if (data.type === "error") {
            logLine(`Something went wrong: ${data.message}`, "error");
            researchBtn.disabled = false;
            source.close();
        }
    };

    source.onerror = () => {
        logLine("Connection lost.", "error");
        researchBtn.disabled = false;
        source.close();
    };
}

// ──────────────── Render ────────────────
const MOOD_EMOJI = {
    very_positive: "🟢",
    positive: "🟢",
    mixed: "🟡",
    negative: "🔴",
    very_negative: "🔴",
};

const MOOD_WORD = {
    very_positive: "Very positive",
    positive: "Positive",
    mixed: "Mixed",
    negative: "Negative",
    very_negative: "Concerning",
};

const NEWS_EMOJI = {
    good_news: "👍",
    bad_news: "👎",
    mixed: "🤔",
    neutral_info: "ℹ️",
};

function renderExplainer(e) {
    document.getElementById("brief-ticker").textContent = e.ticker;
    document.getElementById("brief-company").textContent = e.company_name;
    document.getElementById("brief-mood-emoji").textContent = MOOD_EMOJI[e.overall_mood] || "🟡";
    document.getElementById("brief-mood-word").textContent = MOOD_WORD[e.overall_mood] || "Mixed";
    document.getElementById("brief-oneliner").textContent = `"${e.mood_one_liner}"`;
    
    document.getElementById("brief-what").textContent = e.what_they_do;
    document.getElementById("brief-story").textContent = e.the_story;
    
    document.getElementById("brief-price").textContent = e.current_price
        ? `$${e.current_price.toFixed(2)}`
        : "Price not available";
    document.getElementById("brief-price-context").textContent = e.price_context;
    document.getElementById("brief-size-context").textContent = e.company_size_context;
    
    document.getElementById("brief-good").innerHTML = e.good_signs
        .map(s => `<li>${escapeHtml(s)}</li>`).join("");
    document.getElementById("brief-concerns").innerHTML = e.concerns
        .map(s => `<li>${escapeHtml(s)}</li>`).join("");
    
    document.getElementById("brief-takeaway").textContent = e.honest_takeaway;
    
    document.getElementById("brief-news").innerHTML = e.recent_news.map(n => `
        <div class="news-item">
            <div class="news-mood">${NEWS_EMOJI[n.mood] || "ℹ️"}</div>
            <div class="news-body">
                <div class="news-headline">${escapeHtml(n.headline)}</div>
                <div class="news-meta">${escapeHtml(n.source)} · ${escapeHtml(n.age)}</div>
                <div class="news-summary">${escapeHtml(n.plain_summary)}</div>
            </div>
        </div>
    `).join("");
    
    document.getElementById("brief-limits").textContent = e.what_we_could_not_check;
    document.getElementById("brief-sources").innerHTML = e.sources_visited
        .map(s => `<li>${escapeHtml(s)}</li>`).join("");
    
    resultsSection.style.display = "";
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 200);
}

init();