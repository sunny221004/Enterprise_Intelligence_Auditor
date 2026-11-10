// PAGE NAVIGATION

function showPage(pageId) {
    document.querySelectorAll(".page").forEach(page => {
        page.classList.remove("active");
    });

    document.querySelectorAll(".nav-link").forEach(link => {
        link.classList.remove("active");
    });

    const selectedPage = document.getElementById(pageId);

    if (selectedPage) {
        selectedPage.classList.add("active");
    }

    const selectedLink = document.querySelector(
        `[data-page="${pageId}"]`
    );

    if (selectedLink) {
        selectedLink.classList.add("active");
    }

    document.querySelector(".topbar h2").textContent =
        pageId === "overview" ? "Enterprise Dashboard" :
        pageId === "documents" ? "Document Analyzer" :
        pageId === "changes" ? "Change Analysis" :
        pageId === "risks" ? "Risk Assessment" :
        pageId === "departments" ? "Departments" :
        pageId === "reports" ? "Audit Reports" : "Settings";
}

document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", function(event) {
        event.preventDefault();
        showPage(this.dataset.page);
    });
});

// DOCUMENT UPLOAD

const fileInput = document.getElementById("fileInput");
const fileInfo = document.getElementById("fileInfo");
const analyzeBtn = document.getElementById("analyzeBtn");
const dropArea = document.getElementById("dropArea");

let selectedFile = null;

function setFile(file) {
    if (!file) return;

    const allowed = [".pdf", ".docx", ".txt"];
    const valid = allowed.some(ext =>
        file.name.toLowerCase().endsWith(ext)
    );

    if (!valid) {
        alert("Please upload PDF, DOCX or TXT file.");
        return;
    }

    selectedFile = file;

    fileInfo.innerHTML = `
        <div class="result-box">
            <strong>Selected Document</strong>
            <p>📄 ${file.name}</p>
            <p>Size: ${(file.size / 1024).toFixed(2)} KB</p>
        </div>
    `;

    analyzeBtn.disabled = false;
}

fileInput.addEventListener("change", function() {
    setFile(this.files[0]);
});

dropArea.addEventListener("dragover", function(event) {
    event.preventDefault();
    dropArea.style.borderColor = "#9c8aff";
});

dropArea.addEventListener("dragleave", function() {
    dropArea.style.borderColor = "#495a7d";
});

dropArea.addEventListener("drop", function(event) {
    event.preventDefault();
    setFile(event.dataTransfer.files[0]);
});


// REAL DOCUMENT ANALYSIS

analyzeBtn.addEventListener("click", async function () {

    if (!selectedFile) return;

    const formData = new FormData();
    formData.append("document", selectedFile);

    const result = document.getElementById("analysisResult");

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing Document...";

    result.innerHTML = `
        <div class="result-box">
            <h3>Processing Document...</h3>
            <p>Extracting text and evaluating risks.</p>
        </div>
    `;

    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Analysis failed");
        }

        result.innerHTML = `
            <div class="result-box">
                <h3>✦ Document Analysis Complete</h3>

                <p><strong>Document:</strong> ${escapeHTML(data.filename)}</p>
                <p><strong>Words:</strong> ${data.word_count}</p>
                <p><strong>Characters:</strong> ${data.characters}</p>

                <p><strong>Risk Score:</strong>
                    ${data.risk.score}/100
                </p>

                <p><strong>Risk Level:</strong>
                    <span class="risk ${data.risk.level.toLowerCase()}-label">
                    ${escapeHTML(data.risk.level)}
                    </span>
                </p>

                <h3 style="margin-top:18px">Affected Departments</h3>
                <p>${data.departments.map(escapeHTML).join(", ")}</p>

                <h3 style="margin-top:18px">Document Preview</h3>
                <p>${escapeHTML(data.summary)}</p>

                <p style="color:#f3c46b;margin-top:12px">
                    Preliminary keyword-based assessment, not a validated AI risk prediction.
                </p>
            </div>
        `;

    } catch (error) {
        result.innerHTML = `
            <div class="result-box">
                <p style="color:#ff849b">
                    Error: ${escapeHTML(error.message)}
                </p>
            </div>
        `;
    }

    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "✦ Analyze Document";
});


// REAL DOCUMENT COMPARISON



async function compareDemo() {

    const oldFile = document.getElementById("oldFile").files[0];
    const newFile = document.getElementById("newFile").files[0];

    const output = document.getElementById("compareResult");

    if (!oldFile || !newFile) {
        alert("Please select both documents.");
        return;
    }

    const formData = new FormData();
    formData.append("old_document", oldFile);
    formData.append("new_document", newFile);

    output.innerHTML = `
        <div class="neon-loading">
            <div class="loader"></div>
            <h3>Analyzing Documents...</h3>
            <p>Detecting every document change</p>
        </div>
    `;

    try {

        const response = await fetch("/api/compare", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Comparison failed");
        }

        const oldRows = data.rows.filter(
            row => row.old_status !== "empty"
        );

        const newRows = data.rows.filter(
            row => row.new_status !== "empty"
        );

        function createRows(rows, side) {

            if (!rows.length) {
                return `<div class="empty-document">
                    No content found
                </div>`;
            }

            return rows.map(row => {

                const isOld = side === "old";

                const status = isOld
                    ? row.old_status
                    : row.new_status;

                const lineNumber = isOld
                    ? row.old_line
                    : row.new_line;

                const content = isOld
                    ? row.old_text
                    : row.new_text;

                const label = status === "removed"
                    ? "REMOVED"
                    : status === "added"
                    ? "ADDED"
                    : "UNCHANGED";

                return `
                    <div class="neon-line ${status}">
                        <span class="neon-number">
                            ${lineNumber}
                        </span>

                        <span class="neon-label">
                            ${label}
                        </span>

                        <span class="neon-content">
                            ${escapeHTML(content)}
                        </span>
                    </div>
                `;

            }).join("");
        }

        const similarity = Math.max(
            0, Math.min(100, Number(data.similarity) || 0)
        );

        output.innerHTML = `

        <div class="neon-report">

            <!-- REPORT HEADING -->

            <div class="neon-title">
                <div class="title-icon">📄</div>

                <h2>
                    Document Comparison Complete
                    <span class="success-check">✓</span>
                </h2>
            </div>

            <!-- SUMMARY CARDS -->

            <div class="neon-stats">

                <div class="neon-stat removed-stat">
                    <div class="stat-symbol">▤</div>
                    <div>
                        <h2>${data.removed_count}</h2>
                        <p>Lines Removed</p>
                    </div>
                </div>

                <div class="neon-stat added-stat">
                    <div class="stat-symbol">＋</div>
                    <div>
                        <h2>${data.added_count}</h2>
                        <p>Lines Added</p>
                    </div>
                </div>

                <div class="neon-stat same-stat">
                    <div class="stat-symbol">⇄</div>
                    <div>
                        <h2>${data.unchanged_count}</h2>
                        <p>Unchanged Lines</p>
                    </div>
                </div>

                <div class="neon-stat similarity-stat">
                    <div class="stat-symbol">▥</div>
                    <div>
                        <h2>${similarity}%</h2>
                        <p>Similarity</p>
                    </div>
                </div>

                <div class="neon-stat total-stat">
                    <div class="stat-symbol">▧</div>
                    <div>
                        <h2>${data.total_changes}</h2>
                        <p>Total Changes</p>
                    </div>
                </div>

            </div>

            <!-- SIMILARITY BAR -->

            <div class="similarity-panel">
                <span>Similarity: ${similarity}%</span>

                <div class="similarity-track">
                    <div class="similarity-fill"
                         style="width:${similarity}%">
                    </div>
                </div>

                <strong>${similarity}%</strong>
            </div>

            <!-- LEGEND -->

            <div class="neon-legend">
                <span><i class="legend-red"></i> Removed from old</span>
                <span><i class="legend-green"></i> Added in new</span>
                <span><i class="legend-purple"></i> Unchanged</span>
            </div>

            <!-- DOCUMENT COMPARISON -->

            <div class="neon-comparison">

                <div class="neon-document old-document">

                    <div class="document-heading">
                        <div class="document-icon old-icon">▤</div>
                        <div>
                            <h3>OLD DOCUMENT</h3>
                            <p>${escapeHTML(oldFile.name)}</p>
                        </div>
                    </div>

                    <div class="document-lines">
                        ${createRows(oldRows, "old")}
                    </div>

                </div>

                <div class="neon-document new-document">

                    <div class="document-heading">
                        <div class="document-icon new-icon">▤</div>
                        <div>
                            <h3>NEW DOCUMENT</h3>
                            <p>${escapeHTML(newFile.name)}</p>
                        </div>
                    </div>

                    <div class="document-lines">
                        ${createRows(newRows, "new")}
                    </div>

                </div>

            </div>

            <!-- BOTTOM LEGEND -->

            <div class="neon-footer">
                <span><i class="legend-red"></i> Red = Removed</span>
                <span><i class="legend-green"></i> Green = Added</span>
                <span><i class="legend-purple"></i> Purple = Unchanged</span>
            </div>

        </div>
        `;

    } catch(error) {

        output.innerHTML = `
            <div class="result-box">
                <p style="color:#ff849b">
                    ${escapeHTML(error.message)}
                </p>
            </div>
        `;
    }
}




// SAFE HTML DISPLAY

function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}
// LOAD SAVED DATABASE HISTORY

async function loadHistory() {

    const container = document.getElementById("historyData");

    if (!container) return;

    container.innerHTML = "<p>Loading history...</p>";

    try {

        const response = await fetch("/api/history");
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Unable to load history");
        }

        if (data.history.length === 0) {
            container.innerHTML =
                "<p class='muted'>No audit records found.</p>";
            return;
        }

        container.innerHTML = data.history.map(item => `
            <div class="risk-row">
                <div>
                    <strong>${escapeHTML(item.filename || "Document")}</strong>
                    <p class="muted">${escapeHTML(item.activity)}
                    · ${escapeHTML(item.created_at)}</p>
                </div>
                <div>
                    <span class="risk ${
                        item.risk_level.toLowerCase()
                    }-label">
                        ${escapeHTML(item.risk_level)}
                    </span>
                    <p class="muted">${item.risk_score}/100</p>
                </div>
            </div>
        `).join("");

    } catch(error) {

        container.innerHTML =
            `<p style="color:#ff849b">${escapeHTML(error.message)}</p>`;
    }
}

async function runAIImpactAnalysis() {

    const oldFile = document.getElementById("oldFile").files[0];
    const newFile = document.getElementById("newFile").files[0];

    const output = document.getElementById("aiImpactResult");
    const button = document.getElementById("aiImpactBtn");

    if (!oldFile || !newFile) {
        alert("Please select both old and new documents first.");
        return;
    }

    const formData = new FormData();

    formData.append("old_document", oldFile);
    formData.append("new_document", newFile);

    button.disabled = true;
    button.textContent = "AI Engine Analyzing...";

    output.innerHTML = `
        <div class="result-box">
            <h3>✦ Intelligence Engine Running</h3>
            <p>Analyzing document changes and business dependencies...</p>
        </div>
    `;

    try {

        const response = await fetch("/api/ai-impact", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "AI analysis failed");
        }

        const riskClass = data.risk.level.toLowerCase();

        const addedHTML = data.changes.added.length
            ? data.changes.added.map(item =>
                `<p class="added-change">+ ${escapeHTML(item)}</p>`
            ).join("")
            : "<p>No added sentences.</p>";

        const removedHTML = data.changes.removed.length
            ? data.changes.removed.map(item =>
                `<p class="removed-change">− ${escapeHTML(item)}</p>`
            ).join("")
            : "<p>No removed sentences.</p>";

        const modifiedHTML = data.changes.modified.length
            ? data.changes.modified.map(item => `
                <div class="modified-change">
                    <p class="removed-change">Old: ${escapeHTML(item.old)}</p>
                    <p class="added-change">New: ${escapeHTML(item.new)}</p>
                    <small>Text similarity: ${item.similarity}%</small>
                </div>
            `).join("")
            : "<p>No modified sentences.</p>";

        const departmentHTML = data.departments.map(department =>
            `<span class="department-chip">${escapeHTML(department)}</span>`
        ).join("");

        const recommendationHTML = data.recommendations.map(item =>
            `<li>${escapeHTML(item)}</li>`
        ).join("");

        const categoryHTML = Object.keys(data.categories).length
            ? Object.keys(data.categories).map(category =>
                `<span class="department-chip">${escapeHTML(category)}</span>`
            ).join("")
            : "<span>No specific category identified</span>";

        output.innerHTML = `
            <div class="ai-report">

                <div class="ai-report-header">
                    <span class="eyebrow">INTELLIGENCE REPORT</span>
                    <h2>Change Impact Assessment</h2>
                    <p>${escapeHTML(data.summary)}</p>
                </div>

                <div class="ai-metrics">

                    <div class="ai-metric">
                        <small>Risk Score</small>
                        <h2>${data.risk.score}/100</h2>
                    </div>

                    <div class="ai-metric">
                        <small>Risk Level</small>
                        <h2 class="${riskClass}-text">
                            ${escapeHTML(data.risk.level)}
                        </h2>
                    </div>

                    <div class="ai-metric">
                        <small>Similarity</small>
                        <h2>${data.similarity}%</h2>
                    </div>

                    <div class="ai-metric">
                        <small>Total Changes</small>
                        <h2>${data.changes.added.length +
                            data.changes.removed.length +
                            data.changes.modified.length}</h2>
                    </div>

                </div>

                <div class="ai-report-section">
                    <h3>Business Impact Categories</h3>
                    <div class="chip-container">
                        ${categoryHTML}
                    </div>
                </div>

                <div class="ai-report-section">
                    <h3>Affected Departments</h3>
                    <div class="chip-container">
                        ${departmentHTML}
                    </div>
                </div>

                <div class="ai-report-section">
                    <h3>New Changes</h3>
                    ${addedHTML}
                </div>

                <div class="ai-report-section">
                    <h3>Removed Changes</h3>
                    ${removedHTML}
                </div>

                <div class="ai-report-section">
                    <h3>Modified Sentences</h3>
                    ${modifiedHTML}
                </div>

                <div class="ai-report-section">
                    <h3>✦ AI Recommendations</h3>
                    <ul class="recommendation-list">
                        ${recommendationHTML}
                    </ul>
                </div>

                <div class="ai-report-section">
                    <small class="muted">
                        Engine: ${escapeHTML(data.engine)}
                    </small>
                    <p class="muted">
                        Preliminary automated assessment.
                        Human review is required before business decisions.
                    </p>
                </div>

                <button class="primary-btn" onclick="window.print()">
                    Print AI Audit Report
                </button>

            </div>
        `;

    } catch(error) {

        output.innerHTML = `
            <div class="result-box">
                <p style="color:#ff849b">
                    ${escapeHTML(error.message)}
                </p>
            </div>
        `;

    } finally {

        button.disabled = false;
        button.textContent = "✦ Run Advanced AI Impact Analysis";
    }
}
