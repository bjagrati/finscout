// ──────────────── State ────────────────

let tickerData = [];   // loaded from tickers.json
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
        // App still works — user just won't get autocomplete
    }
    setupAutocomplete();
}

// ──────────────── Autocomplete ────────────────

function setupAutocomplete() {
    // Create the suggestions dropdown if it doesn't exist
    let dropdown = document.getElementById("autocomplete-dropdown");
    if (!dropdown) {
        dropdown = document.createElement("div");
        dropdown.id = "autocomplete-dropdown";
        dropdown.className = "autocomplete-dropdown";
        // Insert right after the search row
        tickerInput.parentElement.parentElement.insertBefore(
            dropdown,
            tickerInput.parentElement.nextSibling,
        );
    }
    
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
            dropdown.innerHTML = "";
            dropdown.style.display = "none";
        }
    });
    
    // Click outside closes dropdown
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
    
    // Match against ticker (starts-with priority) AND name (contains)
    const tickerMatches = tickerData.filter(t =>
        t.ticker.toLowerCase().startsWith(query)
    );
    const nameMatches = tickerData.filter(t =>
        !t.ticker.toLowerCase().startsWith(query) &&
        t.name.toLowerCase().includes(query)
    );
    
    const top = [...tickerMatches, ...nameMatches].slice(0, 8);
    
    if (top.length === 0) {
        dropdown.innerHTML = `<div class="autocomplete-empty">No matches. Press Enter to search "${escapeHtml(query.toUpperCase())}" anyway.</div>`;
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
        item.addEventListener("click", () => {
            pickSuggestion(item.dataset.ticker);
        });
        item.addEventListener("mouseenter", () => {
            activeSuggestionIndex = parseInt(item.dataset.index);
            updateActiveSuggestion(dropdown.querySelectorAll(".autocomplete-item"));
        });
    });
}

function updateActiveSuggestion(items) {
    items.forEach((item, i) => {
        item.classList.toggle("active", i === activeSuggestionIndex);
    });
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
});

function startResearch() {
    const ticker = tickerInput.value.trim().toUpperCase();
    if (!ticker) return;
    if (!/^[A-Z.]{1,8}$/.test(ticker)) {
        alert("Please enter a valid ticker (1-8 letters, dots allowed).");
        return;
    }

    document.getElementById("autocomplete-dropdown").style.display = "none";
    clearAll();
    progressSection.style.display = "";
    researchBtn.disabled = true;
    logLine(`Researching ${ticker}...`, "success");

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

    source.onerror = () => {
        logLine("✗ Connection lost.", "error");
        researchBtn.disabled = false;
        source.close();
    };
}

function renderBrief(brief) {
    document.getElementById("brief-ticker").textContent = brief.ticker;
    document.getElementById("brief-company").textContent = brief.company_name;
    document.getElementById("brief-summary").textContent = brief.one_line_summary;
    
    // Animate the numbers
    animateValue("brief-price", 0, brief.current_price, "$", 2);
    document.getElementById("brief-mcap").textContent = brief.market_cap || "—";
    
    if (brief.pe_ratio) {
        animateValue("brief-pe", 0, brief.pe_ratio, "", 2);
    } else {
        document.getElementById("brief-pe").textContent = "—";
    }

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

    document.getElementById("brief-bull").innerHTML = brief.bull_case
        .map(b => `<li>${escapeHtml(b)}</li>`).join("");
    document.getElementById("brief-bear").innerHTML = brief.bear_case
        .map(b => `<li>${escapeHtml(b)}</li>`).join("");
    document.getElementById("brief-risks").innerHTML = brief.key_risks
        .map(r => `<li>${escapeHtml(r)}</li>`).join("");
    document.getElementById("brief-confidence").textContent = brief.confidence_note;
    document.getElementById("brief-sources").innerHTML = brief.sources_visited
        .map(s => `<li>${escapeHtml(s)}</li>`).join("");

    resultsSection.style.display = "";
    // Stagger the card reveals for a nice cascade effect
    const cards = resultsSection.querySelectorAll(".card");
    cards.forEach((card, i) => {
        card.style.animation = `fadeInUp 0.45s ease ${i * 80}ms backwards`;
    });
    
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
}

// Animated number counter
function animateValue(elementId, start, end, prefix = "", decimals = 0) {
    if (end === null || end === undefined) {
        document.getElementById(elementId).textContent = "—";
        return;
    }
    const element = document.getElementById(elementId);
    const duration = 800;
    const startTime = performance.now();
    
    function step(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // Ease-out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = start + (end - start) * eased;
        element.textContent = `${prefix}${current.toFixed(decimals)}`;
        if (progress < 1) {
            requestAnimationFrame(step);
        } else {
            element.textContent = `${prefix}${end.toFixed(decimals)}`;
        }
    }
    requestAnimationFrame(step);
}

// Boot
init();