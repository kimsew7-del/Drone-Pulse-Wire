const refs = {
  // Stats
  metrics: document.querySelector("#rm-metrics"),
  regionBreakdown: document.querySelector("#rm-region-breakdown"),
  // Crawl controls
  topicInput: document.querySelector("#rm-topic"),
  topicBtn: document.querySelector("#rm-topic-btn"),
  statsBtn: document.querySelector("#rm-stats-btn"),
  regionSelect: document.querySelector("#rm-region"),
  regionBtn: document.querySelector("#rm-region-btn"),
  // Job panel
  jobPanel: document.querySelector("#rm-job-panel"),
  jobStatusLabel: document.querySelector("#rm-job-status-label"),
  status: document.querySelector("#rm-status"),
  progressBar: document.querySelector("#rm-progress-bar"),
  progressText: document.querySelector("#rm-progress-text"),
  log: document.querySelector("#rm-log"),
  // Feed
  feed: document.querySelector("#rm-feed"),
  count: document.querySelector("#rm-count"),
  search: document.querySelector("#rm-search"),
  regionFilter: document.querySelector("#rm-region-filter"),
  docTypeFilter: document.querySelector("#rm-doc-type-filter"),
  sourceFilter: document.querySelector("#rm-source-filter"),
  resetBtn: document.querySelector("#rm-reset-btn"),
  clearReportsBtn: document.querySelector("#rm-clear-reports"),
  // Toast
  toastContainer: document.querySelector("#toast-container"),
};

let pollTimer = null;
let lastStatus = "idle";
let reports = [];
let reportStats = {};

// ── Stats dashboard ──────────────────────────────────────────

function renderStats() {
  if (!refs.metrics) return;

  const regionCounts = {};
  const sourceCounts = {};
  const docTypeCounts = {};
  reports.forEach((r) => {
    regionCounts[r.region] = (regionCounts[r.region] || 0) + 1;
    sourceCounts[r.source] = (sourceCounts[r.source] || 0) + 1;
    const dt = r.doc_type || "뉴스";
    docTypeCounts[dt] = (docTypeCounts[dt] || 0) + 1;
  });

  const avgImpact = reports.length
    ? Math.round(reports.reduce((s, r) => s + (Number(r.impact) || 0), 0) / reports.length)
    : 0;

  refs.metrics.innerHTML = "";
  [
    { label: "전체", value: `${reports.length}건`, filter: "all" },
    { label: "논문", value: `${docTypeCounts["논문"] || 0}건`, filter: "논문" },
    { label: "보고서/정부", value: `${(docTypeCounts["보고서"] || 0) + (docTypeCounts["정부문서"] || 0) + (docTypeCounts["국제기구"] || 0)}건`, filter: "보고서+정부" },
    { label: "통계", value: `${docTypeCounts["통계"] || 0}건`, filter: "통계" },
    { label: "뉴스", value: `${docTypeCounts["뉴스"] || 0}건`, filter: "뉴스" },
  ].forEach((m) => {
    const tile = document.createElement("article");
    tile.className = "trend-metric rm-stat-tile";
    if (m.filter === (refs.docTypeFilter?.value || "all")) {
      tile.classList.add("active");
    }
    tile.innerHTML = `<span>${m.label}</span><strong>${m.value}</strong>`;
    tile.addEventListener("click", () => {
      if (refs.docTypeFilter) {
        if (m.filter === "보고서+정부") {
          refs.docTypeFilter.value = "보고서";
        } else {
          refs.docTypeFilter.value = m.filter;
        }
        renderReports();
        renderStats();
      }
    });
    refs.metrics.append(tile);
  });

  // Region breakdown (clickable)
  if (refs.regionBreakdown) {
    refs.regionBreakdown.innerHTML = "";
    const sorted = Object.entries(regionCounts).sort((a, b) => b[1] - a[1]);
    const activeRegion = refs.regionFilter?.value || "all";
    sorted.forEach(([region, count]) => {
      const pct = reports.length ? Math.round((count / reports.length) * 100) : 0;
      const row = document.createElement("div");
      row.className = `rm-region-row ${activeRegion === region ? "active" : ""}`;
      row.innerHTML = `
        <span class="rm-region-name">${region}</span>
        <div class="rm-region-bar"><span style="width:${pct}%"></span></div>
        <span class="rm-region-count">${count}건</span>
      `;
      row.addEventListener("click", () => {
        if (refs.regionFilter) {
          refs.regionFilter.value = activeRegion === region ? "all" : region;
          renderReports();
          renderStats();
        }
      });
      refs.regionBreakdown.append(row);
    });
  }
}

// ── Crawl job ────────────────────────────────────────────────

function setButtons(disabled) {
  if (refs.topicBtn) refs.topicBtn.disabled = disabled;
  if (refs.statsBtn) refs.statsBtn.disabled = disabled;
  if (refs.regionBtn) refs.regionBtn.disabled = disabled;
}

function showJobPanel() {
  refs.jobPanel?.classList.remove("hidden");
}

function renderJob(job) {
  if (job.status === "idle") return;

  showJobPanel();

  const isRunning = job.status === "running";
  const pct = job.total ? Math.round((job.progress / job.total) * 100) : 0;

  if (refs.jobStatusLabel) {
    refs.jobStatusLabel.textContent =
      isRunning ? "진행 중" : job.status === "completed" ? "완료" : "오류";
  }

  refs.status.className = `rm-status ${job.status}`;
  if (isRunning) {
    refs.status.innerHTML = `
      <div class="rm-status-main">
        <strong>${job.current_seed || "준비 중"}</strong>
        <span>${job.current_region || ""}</span>
      </div>
      <div class="rm-status-sub">발견 ${job.discovered}건</div>
    `;
  } else if (job.status === "completed") {
    refs.status.innerHTML = `
      <div class="rm-status-main"><strong>수집 완료</strong></div>
      <div class="rm-status-sub">${job.discovered}건 추가됨</div>
    `;
  } else {
    refs.status.innerHTML = `<div class="rm-status-main"><strong>오류 발생</strong></div>`;
  }

  if (refs.progressBar) refs.progressBar.style.width = `${pct}%`;
  if (refs.progressText) refs.progressText.textContent = `${job.progress}/${job.total}`;

  if (refs.log && job.log) {
    refs.log.innerHTML = job.log
      .slice(-25)
      .map((entry) => {
        const cls = entry.includes("오류") ? "rm-log-error" : entry.includes("수집") || entry.includes("완료") ? "rm-log-success" : "";
        return `<div class="rm-log-entry ${cls}">${entry}</div>`;
      })
      .join("");
    refs.log.scrollTop = refs.log.scrollHeight;
  }

  setButtons(isRunning);
}

async function pollStatus() {
  try {
    const resp = await fetch("/api/crawl");
    if (!resp.ok) return;
    const job = await resp.json();
    renderJob(job);

    if (job.status === "running") {
      pollTimer = window.setTimeout(pollStatus, 1500);
    } else {
      pollTimer = null;
      if (lastStatus === "running" && job.status === "completed") {
        showToast("수집 완료", `${job.discovered}건의 리포트를 수집했습니다.`, "success");
        await loadReports();
      } else if (lastStatus === "running" && job.status === "error") {
        showToast("수집 오류", "크롤링 중 문제가 발생했습니다.", "error");
      }
      lastStatus = job.status;
    }
    if (job.status === "running") lastStatus = "running";
  } catch (e) {
    console.error(e);
  }
}

async function startTopicCrawl() {
  const topic = (refs.topicInput?.value || "").trim();
  if (!topic) {
    refs.topicInput?.focus();
    return;
  }
  setButtons(true);
  showJobPanel();
  try {
    const resp = await fetch("/api/crawl", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });
    const job = await resp.json();
    if (job.error) {
      showToast("수집 불가", job.error, "error");
      setButtons(false);
      return;
    }
    renderJob(job);
    lastStatus = "running";
    pollTimer = window.setTimeout(pollStatus, 1500);
  } catch (e) {
    console.error(e);
    setButtons(false);
    showToast("네트워크 오류", "서버에 연결할 수 없습니다.", "error");
  }
}

async function startStatsCrawl() {
  const topic = (refs.topicInput?.value || "").trim();
  if (!topic) {
    refs.topicInput?.focus();
    return;
  }
  setButtons(true);
  showJobPanel();
  try {
    const resp = await fetch("/api/crawl", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, mode: "stats" }),
    });
    const job = await resp.json();
    if (job.error) {
      showToast("수집 불가", job.error, "error");
      setButtons(false);
      return;
    }
    renderJob(job);
    lastStatus = "running";
    pollTimer = window.setTimeout(pollStatus, 1500);
  } catch (e) {
    console.error(e);
    setButtons(false);
    showToast("네트워크 오류", "서버에 연결할 수 없습니다.", "error");
  }
}

async function startRegionCrawl() {
  if (!refs.regionSelect) return;
  const selected = [...refs.regionSelect.selectedOptions].map((o) => o.value);
  const regions = selected.includes("all") ? null : selected;
  setButtons(true);
  showJobPanel();
  try {
    const resp = await fetch("/api/crawl", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ regions }),
    });
    const job = await resp.json();
    if (job.error) {
      showToast("수집 불가", job.error, "error");
      setButtons(false);
      return;
    }
    renderJob(job);
    lastStatus = "running";
    pollTimer = window.setTimeout(pollStatus, 1500);
  } catch (e) {
    console.error(e);
    setButtons(false);
    showToast("네트워크 오류", "서버에 연결할 수 없습니다.", "error");
  }
}

async function resetCrawl() {
  try {
    const resp = await fetch("/api/crawl", { method: "DELETE" });
    if (!resp.ok) return;
    const job = await resp.json();
    if (pollTimer) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
    lastStatus = "idle";
    refs.jobPanel?.classList.add("hidden");
    refs.status.className = "rm-status";
    refs.status.innerHTML = "대기 중";
    if (refs.progressBar) refs.progressBar.style.width = "0%";
    if (refs.progressText) refs.progressText.textContent = "0/0";
    if (refs.log) refs.log.innerHTML = "";
    if (refs.jobStatusLabel) refs.jobStatusLabel.textContent = "대기";
    setButtons(false);
    showToast("초기화 완료", "크롤 상태가 초기화되었습니다.", "success");
  } catch (e) {
    console.error(e);
  }
}

async function clearReports() {
  if (!window.confirm("수집된 리포트를 모두 삭제합니다. 계속하시겠습니까?")) return;
  try {
    const resp = await fetch("/api/reports", { method: "DELETE" });
    if (!resp.ok) return;
    const result = await resp.json();
    showToast("리포트 초기화", `${result.removed}건 삭제 완료`, "success");
    await loadReports();
  } catch (e) {
    console.error(e);
    showToast("오류", "리포트 초기화에 실패했습니다.", "error");
  }
}

// ── Report feed ──────────────────────────────────────────────

async function loadReports() {
  try {
    const resp = await fetch("/api/news");
    if (!resp.ok) return;
    const payload = await resp.json();

    reports = payload.reports || [];
    reportStats = payload.report_stats || {};

    renderStats();
    populateFilters();
    renderReports();
  } catch (e) {
    console.error(e);
  }
}

function populateFilters() {
  // Region filter
  if (refs.regionFilter) {
    const regions = new Set(reports.map((r) => r.region).filter(Boolean));
    const current = refs.regionFilter.value;
    refs.regionFilter.innerHTML = '<option value="all">전체 지역</option>';
    [...regions].sort().forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r;
      opt.textContent = r;
      refs.regionFilter.append(opt);
    });
    refs.regionFilter.value = current;
  }

  // Source filter
  if (refs.sourceFilter) {
    const sources = new Set(reports.map((r) => r.source).filter(Boolean));
    const current = refs.sourceFilter.value;
    refs.sourceFilter.innerHTML = '<option value="all">전체 소스</option>';
    [...sources].sort().forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      refs.sourceFilter.append(opt);
    });
    refs.sourceFilter.value = current;
  }
}

function filterReports() {
  const query = (refs.search?.value || "").trim().toLowerCase();
  const region = refs.regionFilter?.value || "all";
  const docType = refs.docTypeFilter?.value || "all";
  const source = refs.sourceFilter?.value || "all";

  return reports.filter((item) => {
    const matchSearch =
      !query ||
      `${item.headline} ${item.summary} ${item.source} ${item.region}`
        .toLowerCase()
        .includes(query);
    const matchRegion = region === "all" || item.region === region;
    const itemDocType = item.doc_type || "뉴스";
    const reportGroup = ["보고서", "정부문서", "국제기구"];
    const matchDocType =
      docType === "all" ||
      itemDocType === docType ||
      (docType === "보고서" && reportGroup.includes(itemDocType));
    const matchSource = source === "all" || item.source === source;
    return matchSearch && matchRegion && matchDocType && matchSource;
  });
}

function renderReports() {
  const filtered = filterReports();
  refs.count.textContent = `${filtered.length}건`;
  refs.feed.innerHTML = "";

  if (!filtered.length) {
    refs.feed.innerHTML =
      '<div class="empty-state">수집된 리포트가 없습니다.<br>위 주제 입력란에 키워드를 넣고 <strong>수집</strong>을 눌러보세요.</div>';
    return;
  }

  filtered.forEach((item) => {
    const card = document.createElement("article");
    card.className = "rm-report-card";

    const originalTitle = item.headline || "";
    const translatedTitle = item.translated_headline || "";
    const originalIsKo = isKorean(originalTitle);

    let titleHtml = `<h3 class="rm-title-original">${originalTitle}</h3>`;
    if (translatedTitle && translatedTitle !== originalTitle) {
      titleHtml += `<p class="rm-title-translated">${translatedTitle}</p>`;
    } else if (!originalIsKo) {
      titleHtml += `<p class="rm-title-untranslated">${originalTitle}</p>`;
    }

    const displaySummary = item.translated_summary || item.summary || "";
    const hideSummary =
      !displaySummary ||
      displaySummary === originalTitle ||
      displaySummary === translatedTitle ||
      displaySummary === "요약 정보가 아직 제공되지 않았습니다.";

    const dateStr = formatDate(item.timestamp);
    const relStr = formatRelative(item.timestamp);
    const dateDisplay = dateStr ? `${dateStr} (${relStr})` : relStr;

    card.innerHTML = `
      <div class="rm-report-head">
        <div class="rm-report-titles">${titleHtml}</div>
        <a class="source-link" href="${item.url}" target="_blank" rel="noreferrer">원문</a>
      </div>
      ${!hideSummary ? `<p class="rm-report-summary">${displaySummary}</p>` : ""}
      <div class="rm-report-meta">
        <span class="badge rm-doc-type rm-doc-${(item.doc_type || "뉴스").replace(/\s/g, "")}">${item.doc_type || "뉴스"}</span>
        <span class="badge report-type">${item.region}</span>
        <span class="badge">${item.source}</span>
        <span class="badge rm-date-badge">${dateDisplay}</span>
        <span class="badge">영향도 ${item.impact}</span>
      </div>
    `;

    const highlights = item.highlights || [];
    if (highlights.length) {
      const hl = document.createElement("div");
      hl.className = "rm-report-tags";
      highlights.forEach((h) => {
        const chip = document.createElement("span");
        chip.className = "highlight";
        chip.textContent = h;
        hl.append(chip);
      });
      card.append(hl);
    }

    refs.feed.append(card);
  });
}

// ── Init ─────────────────────────────────────────────────────

function bindControls() {
  refs.topicBtn?.addEventListener("click", startTopicCrawl);
  refs.statsBtn?.addEventListener("click", startStatsCrawl);
  refs.topicInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") startTopicCrawl();
  });
  refs.regionBtn?.addEventListener("click", startRegionCrawl);
  refs.resetBtn?.addEventListener("click", resetCrawl);
  refs.clearReportsBtn?.addEventListener("click", clearReports);
  refs.search?.addEventListener("input", renderReports);
  refs.docTypeFilter?.addEventListener("change", renderReports);
  refs.regionFilter?.addEventListener("change", renderReports);
  refs.sourceFilter?.addEventListener("change", renderReports);
}

async function init() {
  bindControls();
  await loadReports();

  // Resume if crawl already running
  try {
    const resp = await fetch("/api/crawl");
    if (resp.ok) {
      const job = await resp.json();
      if (job.status !== "idle") {
        renderJob(job);
        if (job.status === "running") {
          lastStatus = "running";
          pollTimer = window.setTimeout(pollStatus, 1500);
        }
      }
    }
  } catch (e) {
    /* ignore */
  }

  window.setInterval(loadReports, 30000);
}

init();
