const refs = {
  monitorStatus: document.querySelector("#monitor-status"),
  monitorSummary: document.querySelector("#monitor-summary"),
  monitorMetrics: document.querySelector("#monitor-metrics"),
  sourcesCount: document.querySelector("#sources-count"),
  sourceList: document.querySelector("#source-list"),
  signalList: document.querySelector("#signal-list"),
};

function formatSourceError(error) {
  if (!error) {
    return "없음";
  }
  if (error === "network_error") {
    return "네트워크";
  }
  if (error === "collection_error") {
    return "수집 실패";
  }
  return error;
}

function getSourceStatus(stats) {
  if (stats.blocked_reason === "missing_env_key") {
    return { label: "키 대기", tone: "warn" };
  }
  if (stats.last_error) {
    return { label: "오류", tone: "danger" };
  }
  if (stats.last_checked_at && (stats.fetched_count ?? 0) === 0) {
    return { label: "대기", tone: "neutral" };
  }
  if (stats.last_checked_at) {
    return { label: "정상", tone: "ok" };
  }
  return { label: "미확인", tone: "neutral" };
}

function renderMetrics(payload) {
  const stats = payload.source_stats || {};
  const values = Object.values(stats);
  const okCount = values.filter((item) => !item.last_error && !item.blocked_reason && (item.fetched_count ?? 0) > 0).length;
  const warnCount = values.filter((item) => item.blocked_reason === "missing_env_key").length;
  const errorCount = values.filter((item) => item.last_error).length;

  refs.monitorMetrics.innerHTML = "";
  [
    { label: "정상 소스", value: `${okCount}` },
    { label: "키 대기", value: `${warnCount}` },
    { label: "오류 소스", value: `${errorCount}` },
  ].forEach((metric) => {
    const tile = document.createElement("article");
    tile.className = "trend-metric";
    tile.innerHTML = `<span>${metric.label}</span><strong>${metric.value}</strong>`;
    refs.monitorMetrics.append(tile);
  });
}

function renderSources(payload) {
  const sources = payload.sources || [];
  const sourceStats = payload.source_stats || {};
  refs.sourcesCount.textContent = `${sources.length}개 소스`;
  refs.sourceList.innerHTML = "";

  sources.forEach((source) => {
    const stats = sourceStats[source.id] || {};
    const status = getSourceStatus(stats);
    const card = document.createElement("article");
    card.className = "source-item";
    card.innerHTML = `
      <div class="source-head">
        <strong>${source.name}</strong>
        <span class="source-badge source-badge-${status.tone}">${status.label}</span>
      </div>
      <div class="source-tags">
        <span class="highlight">${source.type.toUpperCase()}</span>
        <span class="highlight">${source.env_key ? "API" : "OPEN"}</span>
      </div>
      <p>${source.url}</p>
      <div class="source-metrics">
        <span>최근 수집 ${stats.fetched_count ?? 0}건</span>
        <span>오류 ${formatSourceError(stats.last_error)}</span>
      </div>
      <div class="related-meta">최근 확인 ${formatRelative(stats.last_checked_at)} · 최근 성공 ${formatRelative(stats.last_success_at)}</div>
    `;
    refs.sourceList.append(card);
  });
}

function renderSignals(payload) {
  refs.signalList.innerHTML = "";
  (payload.signals || []).forEach((signal) => {
    const card = document.createElement("article");
    card.className = "signal-item";
    card.innerHTML = `
      <strong>${signal.title}</strong>
      <p>${signal.copy}</p>
      <span class="tag">${signal.tag}</span>
    `;
    refs.signalList.append(card);
  });
}

async function loadMonitor() {
  refs.monitorStatus.textContent = "SYNCING";
  const response = await fetch("/api/news");
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const payload = await response.json();
  refs.monitorStatus.textContent = payload.meta?.feed_status || "LIVE";
  refs.monitorSummary.textContent = `최근 동기화 ${formatRelative(payload.meta?.last_sync)}`;
  renderMetrics(payload);
  renderSources(payload);
  renderSignals(payload);
}

async function init() {
  try {
    await loadMonitor();
  } catch (error) {
    refs.monitorStatus.textContent = "OFFLINE";
    refs.monitorSummary.textContent = "모니터링 API에 연결할 수 없습니다.";
    console.error(error);
  }

  window.setInterval(loadMonitor, 30000);
}

init();
