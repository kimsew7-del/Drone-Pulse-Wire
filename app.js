const RESEARCH_SOURCES = new Set([
  "Crossref Drone AI Research",
  "Europe PMC AI Robotics",
  "KCI Korea Drone AI Papers",
  "AI",
  "AIP Conference Proceedings",
  "Lecture Notes in Networks and Systems",
  "International Journal of Advanced Research in Science, Communication and Technology",
  "Journal of Systemics, Cybernetics and Informatics",
  "Contributions to Security and Defence Studies",
]);

const TREND_TERMS = [
  "drone",
  "uav",
  "swarm",
  "delivery",
  "ai",
  "autonomous",
  "robotics",
  "inspection",
  "mapping",
  "navigation",
  "vision",
  "airspace",
  "defense",
  "safety",
  "semiconductor",
  "edge",
];


const state = {
  feed: [],
  sources: [],
  sourceStats: {},
  signals: [],
  trendHistory: [],
  autoCategories: [],
  categorySnapshots: [],
  activeCategoryWindow: "24h",
  likedIds: new Set(),
  savedIds: new Set(),
  meta: {
    tracked_sources: 0,
    feed_status: "BOOTING",
    last_sync: null,
  },
  filters: {
    search: "",
    category: "all",
  },
};

const refs = {
  newsList: document.querySelector("#news-list"),
  trendMetrics: document.querySelector("#trend-metrics"),
  trendSummary: document.querySelector("#trend-summary"),
  trendList: document.querySelector("#trend-list"),
  reportSummary: document.querySelector("#report-summary"),
  reportList: document.querySelector("#report-list"),
  signalList: document.querySelector("#signal-list"),
  sourceList: document.querySelector("#source-list"),
  categoryList: document.querySelector("#category-list"),
  search: document.querySelector("#search"),
  refreshButton: document.querySelector("#refresh-button"),
  resultsCount: document.querySelector("#results-count"),
  trackedCount: document.querySelector("#tracked-count"),
  feedStatus: document.querySelector("#feed-status"),
  sourcesCount: document.querySelector("#sources-count"),
  template: document.querySelector("#feed-card-template"),
};

function classifyItem(item) {
  if (item.content_type) {
    return item.content_type;
  }
  return RESEARCH_SOURCES.has(item.source) ? "research" : "news";
}

function isKoreanText(text) {
  return isKorean(text);
}

function loadStoredSet(key) {
  try {
    const raw = localStorage.getItem(key);
    return new Set(normalizeArray(JSON.parse(raw)));
  } catch (error) {
    return new Set();
  }
}

function persistStoredSet(key, value) {
  localStorage.setItem(key, JSON.stringify([...value]));
}

function filterFeed() {
  const { search, category } = state.filters;
  const query = search.trim().toLowerCase();

  return [...state.feed]
    .filter((item) => {
      const matchesSearch =
        !query ||
        [
          item.headline,
          item.summary,
          item.source,
          item.region,
          ...normalizeArray(item.highlights),
        ]
          .join(" ")
          .toLowerCase()
          .includes(query);
      const matchesCategory =
        category === "all" ||
        normalizeArray(item.auto_categories).includes(category);
      return matchesSearch && matchesCategory;
    })
    .sort(
      (left, right) =>
        new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime(),
    );
}

function extractTrendScores(items) {
  const scores = new Map();

  items.forEach((item) => {
    const text = [item.headline, item.summary, ...normalizeArray(item.highlights)]
      .join(" ")
      .toLowerCase();

    TREND_TERMS.forEach((term) => {
      if (!text.includes(term)) {
        return;
      }
      scores.set(term, (scores.get(term) || 0) + 1);
    });
  });

  return [...scores.entries()]
    .sort((left, right) => right[1] - left[1])
    .slice(0, 6)
    .map(([term, count]) => ({ term, count }));
}

function buildAnalytics(items) {
  const now = Date.now();
  const recentWindow = items.filter((item) => {
    const timestamp = new Date(item.timestamp).getTime();
    return Number.isFinite(timestamp) && now - timestamp <= 72 * 60 * 60 * 1000;
  });
  const averageImpact = items.length
    ? Math.round(
        items.reduce((sum, item) => sum + (Number(item.impact) || 0), 0) / items.length,
      )
    : 0;
  const topicCounts = new Map();
  const regionCounts = new Map();

  items.forEach((item) => {
    topicCounts.set(item.topic, (topicCounts.get(item.topic) || 0) + 1);
    regionCounts.set(item.region, (regionCounts.get(item.region) || 0) + 1);
  });

  return {
    total: items.length,
    recent: recentWindow.length,
    averageImpact,
    topicCounts: [...topicCounts.entries()].sort((left, right) => right[1] - left[1]),
    regionCounts: [...regionCounts.entries()].sort((left, right) => right[1] - left[1]),
  };
}

function buildTrendDeltaMap() {
  const history = normalizeArray(state.trendHistory);
  const latest = history[history.length - 1];
  const previous = history[history.length - 2];
  const deltas = new Map();

  if (!latest) {
    return deltas;
  }

  Object.entries(latest.keyword_counts || {}).forEach(([term, count]) => {
    const previousCount = previous?.keyword_counts?.[term] || 0;
    deltas.set(term, count - previousCount);
  });

  return deltas;
}

const TECH_REPORTS = [
  {
    title: "드론",
    terms: ["drone", "drones", "uav", "uas", "bvlos", "eVTOL", "air mobility",
            "드론", "무인기", "도심항공", "비행체", "UAM"],
  },
  {
    title: "피지컬 AI",
    terms: ["physical ai", "embodied ai", "sim2real", "world model",
            "computer vision", "edge ai", "autonomous system",
            "피지컬 ai", "비전 ai", "월드모델", "자율시스템"],
  },
  {
    title: "로봇",
    terms: ["robot", "robots", "robotic", "robotics", "humanoid",
            "manipulation", "mobile robot", "autonomous robot",
            "로봇", "로보틱스", "휴머노이드", "자율로봇"],
  },
];

// 공신력 높은 소스 — 정렬 시 우선
const AUTHORITATIVE_SOURCES = new Set([
  "FAA", "NASA", "DARPA", "GAO", "EASA", "ICAO", "OECD",
  "RAND", "Brookings", "IEEE", "Nature", "Science",
  "Reuters", "Associated Press", "Bloomberg",
  "국토부", "과기부", "산업부", "KARI", "KAIST", "ADD",
  "DLR", "ONERA", "JAXA", "CAAC",
]);

function isToday(isoString) {
  if (!isoString) return false;
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return false;
  const now = new Date();
  return d.getFullYear() === now.getFullYear()
    && d.getMonth() === now.getMonth()
    && d.getDate() === now.getDate();
}

function sourceCredibility(item) {
  // 높을수록 공신력 높음
  let score = item.impact || 0;
  const src = (item.source || "").toLowerCase();
  for (const name of AUTHORITATIVE_SOURCES) {
    if (src.includes(name.toLowerCase())) { score += 30; break; }
  }
  const ct = item.content_type || "";
  if (ct === "report") score += 20;
  if (ct === "research") score += 15;
  return score;
}

function buildReports(items) {
  // 오늘 기사만
  const todayItems = items.filter((item) => isToday(item.timestamp));

  return TECH_REPORTS.map((topic) => {
    const matched = todayItems.filter((item) => {
      const text = `${item.headline} ${item.summary}`.toLowerCase();
      return topic.terms.some((term) => text.toLowerCase().includes(term.toLowerCase()));
    });

    // 공신력 + 최신순 정렬
    matched.sort((a, b) => sourceCredibility(b) - sourceCredibility(a));

    const topItems = matched.slice(0, 3);
    const highlights = [];
    topItems.forEach((item) => {
      normalizeArray(item.highlights).forEach((point) => {
        if (!highlights.includes(point)) highlights.push(point);
      });
    });

    return {
      title: topic.title,
      count: matched.length,
      averageImpact: matched.length
        ? Math.round(matched.reduce((s, i) => s + (Number(i.impact) || 0), 0) / matched.length)
        : 0,
      keywords: highlights.slice(0, 3),
      summary: matched.length
        ? `오늘 ${matched.length}건 — ${highlights.slice(0, 3).join(", ") || "최신 기술"} 관련 기사가 수집됐습니다.`
        : "",
      items: topItems,
      hasUpdate: matched.length > 0,
    };
  });
}

function renderTrends(items) {
  const trends = extractTrendScores(items);
  const analytics = buildAnalytics(items);
  const deltaMap = buildTrendDeltaMap();
  refs.trendMetrics.innerHTML = "";
  refs.trendSummary.innerHTML = "";
  refs.trendList.innerHTML = "";

  [
    { label: "피드 볼륨", value: `${analytics.total}건` },
    { label: "72시간", value: `${analytics.recent}건` },
    { label: "평균 영향도", value: analytics.averageImpact || "-" },
  ].forEach((metric) => {
    const tile = document.createElement("article");
    tile.className = "trend-metric";
    tile.innerHTML = `<span>${metric.label}</span><strong>${metric.value}</strong>`;
    refs.trendMetrics.append(tile);
  });

  if (!trends.length) {
    refs.trendSummary.textContent = "트렌드 집계중";
    return;
  }

  const leaderShare = analytics.total
    ? Math.round((trends[0].count / analytics.total) * 100)
    : 0;
  refs.trendSummary.innerHTML = `
    <strong>${trends[0].term.toUpperCase()}</strong>
    <p>최근 피드에서 가장 많이 반복된 키워드이며 전체 피드의 ${leaderShare}%에서 관측됩니다. 전일 대비 ${
      formatDelta(deltaMap.get(trends[0].term) || 0)
    }.</p>
  `;

  trends.forEach((trend, index) => {
    const card = document.createElement("article");
    card.className = "trend-item";
    const width = trends[0].count
      ? Math.max((trend.count / trends[0].count) * 100, 18)
      : 18;
    card.innerHTML = `
      <span class="trend-rank">0${index + 1}</span>
      <div>
        <strong>${trend.term}</strong>
        <p>${trend.count}회 언급 · ${formatDelta(deltaMap.get(trend.term) || 0)}</p>
      </div>
      <div class="trend-bar"><span style="width: ${width}%"></span></div>
    `;
    refs.trendList.append(card);
  });
}

function renderReports(items) {
  const reports = buildReports(items);
  const activeReports = reports.filter((r) => r.hasUpdate);

  if (!activeReports.length) {
    refs.reportSummary.innerHTML = `
      <strong>오늘의 신기술 리포트</strong>
      <p>오늘 수집된 관련 기사가 아직 없습니다.</p>
    `;
    refs.reportList.innerHTML = "";
    return;
  }

  const totalToday = activeReports.reduce((s, r) => s + r.count, 0);
  refs.reportSummary.innerHTML = `
    <strong>오늘의 신기술 리포트</strong>
    <p>${activeReports.map((r) => r.title).join(" · ")} — 총 ${totalToday}건 수집</p>
  `;
  refs.reportList.innerHTML = "";

  reports.forEach((report) => {
    if (!report.hasUpdate) return;

    const block = document.createElement("article");
    block.className = "report-card";
    block.innerHTML = `
      <div class="report-head">
        <strong>${report.title}</strong>
        <span>${report.count}건</span>
      </div>
      <div class="report-meta">
        <span class="tag">영향도 ${report.averageImpact || "-"}</span>
      </div>
      <p>${report.summary}</p>
      <div class="report-keywords"></div>
      <div class="report-links"></div>
    `;

    const keywordList = block.querySelector(".report-keywords");
    report.keywords.forEach((keyword) => {
      const chip = document.createElement("span");
      chip.className = "highlight";
      chip.textContent = keyword;
      keywordList.append(chip);
    });

    const links = block.querySelector(".report-links");
    report.items.forEach((item) => {
      const displayTitle = item.translated_headline || item.headline;
      const link = document.createElement("a");
      link.className = "report-link";
      link.href = item.url;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = displayTitle;
      links.append(link);
    });

    refs.reportList.append(block);
  });
}

function getCategoriesForWindow() {
  const snapshots = normalizeArray(state.categorySnapshots);
  const latest = snapshots[snapshots.length - 1];
  if (!latest || !latest.windows) {
    return state.autoCategories || [];
  }
  const windowCats = latest.windows[state.activeCategoryWindow];
  return normalizeArray(windowCats);
}

function renderCategories() {
  if (!refs.categoryList) {
    return;
  }
  refs.categoryList.innerHTML = "";
  const categories = getCategoriesForWindow();

  if (!categories.length) {
    refs.categoryList.innerHTML =
      '<div class="empty-state" style="padding:16px;font-size:0.85rem;">카테고리 데이터를 수집 중입니다.</div>';
    return;
  }

  categories.forEach((cat) => {
    const item = document.createElement("article");
    item.className = "category-item";
    const momentumClass = cat.momentum || "stable";
    const momentumLabel =
      momentumClass === "rising" ? "상승" : momentumClass === "falling" ? "하락" : "유지";
    const momentumArrow =
      momentumClass === "rising" ? "\u25B2" : momentumClass === "falling" ? "\u25BC" : "\u2014";

    item.innerHTML = `
      <div class="category-item-head">
        <strong>${cat.label}</strong>
        <span class="category-momentum ${momentumClass}">${momentumArrow} ${momentumLabel}</span>
      </div>
      <div class="category-item-meta">
        <span>${cat.article_count || 0}건</span>
        <span>영향도 ${cat.avg_impact || "-"}</span>
      </div>
      <div class="category-terms"></div>
    `;

    const termsContainer = item.querySelector(".category-terms");
    normalizeArray(cat.terms)
      .slice(0, 4)
      .forEach((term) => {
        const chip = document.createElement("span");
        chip.className = "highlight";
        chip.textContent = term;
        termsContainer.append(chip);
      });

    item.addEventListener("click", () => {
      state.filters.category = cat.label;
      rerender();
    });

    refs.categoryList.append(item);
  });
}


function renderSources() {
  if (!refs.sourceList || !refs.sourcesCount) {
    return;
  }
  refs.sourceList.innerHTML = "";
  refs.sourcesCount.textContent = `${state.sources.length}개 소스`;

  state.sources.forEach((source) => {
    const stats = state.sourceStats[source.id] || {};
    const status = getSourceStatus(stats, source);
    const item = document.createElement("article");
    item.className = "source-item";
    item.innerHTML = `
      <div class="source-head">
        <strong>${source.name}</strong>
        <span class="source-badge source-badge-${status.tone}">${status.label}</span>
      </div>
      <div class="source-tags">
        <span class="highlight">${source.type.toUpperCase()}</span>
        <span class="highlight">${classifySource(source)}</span>
      </div>
      <p>${source.url}</p>
      <div class="source-metrics">
        <span>최근 수집 ${stats.fetched_count ?? 0}건</span>
        <span>오류 ${formatSourceError(stats.last_error)}</span>
      </div>
      <div class="related-meta">최근 확인 ${formatRelative(stats.last_checked_at)} · 최근 성공 ${formatRelative(stats.last_success_at)}</div>
    `;
    refs.sourceList.append(item);
  });
}

function classifySource(source) {
  if (source.type === "crossref" || source.type === "europepmc") {
    return "연구";
  }
  return "뉴스";
}

function getSourceStatus(stats, source) {
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

function renderSignals() {
  refs.signalList.innerHTML = "";

  state.signals.forEach((signal) => {
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

// ── renderFeed (split into sub-functions) ────────────────────

function renderCardBadges(fragment, item) {
  const badges = fragment.querySelector(".card-badges");
  const itemType = classifyItem(item);
  const typeBadge = document.createElement("span");
  typeBadge.className = `badge content-type${itemType === "report" ? " report-type" : ""}`;
  typeBadge.textContent =
    itemType === "research" ? "연구" : itemType === "report" ? "리포트" : "뉴스";
  badges.append(typeBadge);

  if (item.translated_to_ko) {
    const translateBadge = document.createElement("span");
    translateBadge.className = "badge translation";
    translateBadge.textContent = "한글 번역";
    badges.append(translateBadge);

    const originalHeadline = fragment.querySelector(".original-headline");
    const originalSummary = fragment.querySelector(".original-summary");
    originalHeadline.textContent = item.headline;
    originalSummary.textContent = item.summary;
    originalHeadline.classList.add("visible");
    originalSummary.classList.add("visible");
  }

  normalizeArray(item.auto_categories).forEach((catLabel) => {
    const catBadge = document.createElement("span");
    catBadge.className = "badge auto-category";
    catBadge.textContent = catLabel;
    catBadge.addEventListener("click", (e) => {
      e.stopPropagation();
      state.filters.category = catLabel;
      rerender();
    });
    badges.append(catBadge);
  });
}

function renderCardActions(fragment, item) {
  const likeButton = fragment.querySelector(".like-button");
  const saveButton = fragment.querySelector(".save-button");
  const translateButton = fragment.querySelector(".translate-button");
  const shareButton = fragment.querySelector(".share-button");
  const relatedButton = fragment.querySelector(".related-button");

  likeButton.textContent = state.likedIds.has(item.id) ? "공감됨" : "공감";
  saveButton.textContent = state.savedIds.has(item.id) ? "저장됨" : "저장";
  if (item.translated_to_ko) {
    translateButton.textContent = "재번역";
  } else if (isKoreanText(item.headline) && isKoreanText(item.summary)) {
    translateButton.disabled = true;
    translateButton.textContent = "한글 기사";
  }
  if (!normalizeArray(item.related_articles).length) {
    relatedButton.disabled = true;
    relatedButton.textContent = "관련 없음";
  }

  if (normalizeArray(item.related_articles).length) {
    const details = document.createElement("details");
    details.className = "related-details";
    details.innerHTML = `<summary>관련 기사 ${item.related_articles.length}건</summary>`;
    const list = document.createElement("div");
    list.className = "related-list";
    item.related_articles.forEach((article) => {
      const child = document.createElement("a");
      child.className = "report-link";
      child.href = article.url;
      child.target = "_blank";
      child.rel = "noreferrer";
      child.textContent = article.headline;
      list.append(child);
    });
    details.append(list);
    fragment.querySelector(".related-wrapper").append(details);

    relatedButton.addEventListener("click", () => {
      details.open = !details.open;
    });
  }

  likeButton.addEventListener("click", () => {
    toggleStoredId(state.likedIds, "drone-pulse-liked", item.id);
    rerender();
  });

  saveButton.addEventListener("click", () => {
    toggleStoredId(state.savedIds, "drone-pulse-saved", item.id);
    rerender();
  });

  translateButton.addEventListener("click", async () => {
    translateButton.disabled = true;
    translateButton.textContent = "번역 중";
    await translateItem(item.id);
  });

  shareButton.addEventListener("click", async () => {
    await shareItem(item);
    shareButton.textContent = "복사됨";
    window.setTimeout(() => {
      shareButton.textContent = "공유";
    }, 1200);
  });
}

function renderFeedCard(item, index) {
  const fragment = refs.template.content.cloneNode(true);
  const card = fragment.querySelector(".feed-card");
  card.style.animationDelay = `${index * 50}ms`;
  fragment.querySelector(".source-name").textContent = item.source;
  fragment.querySelector(".region").textContent = item.region;
  fragment.querySelector(".timestamp").textContent = formatRelative(item.timestamp);
  fragment.querySelector(".cover-topic").textContent = item.topic;
  const displayHeadline = item.translated_headline || item.headline;
  const displaySummary = item.translated_summary || item.summary;
  fragment.querySelector(".headline").textContent = displayHeadline;
  const summaryEl = fragment.querySelector(".summary");
  const hideSummary =
    displaySummary === displayHeadline ||
    displaySummary === "요약 정보가 아직 제공되지 않았습니다.";
  if (hideSummary) {
    summaryEl.style.display = "none";
  } else {
    summaryEl.textContent = displaySummary;
  }
  fragment.querySelector(".impact").textContent = `영향도 ${item.impact}`;
  fragment.querySelector(".source-link").href = item.url;
  card.dataset.id = item.id;

  renderCardBadges(fragment, item);

  if (item.duplicate_count > 0) {
    const duplicateNote = fragment.querySelector(".duplicate-note");
    duplicateNote.textContent = `중복 기사 ${item.duplicate_count}건 통합 · ${item.related_sources.join(", ")}`;
    duplicateNote.classList.add("visible");
  }

  if (item.merged_summary) {
    const merged = fragment.querySelector(".merged-summary");
    merged.textContent = item.merged_summary;
    merged.classList.add("visible");
  }

  const highlights = fragment.querySelector(".highlights");
  normalizeArray(item.highlights).forEach((point) => {
    const pill = document.createElement("span");
    pill.className = "highlight";
    pill.textContent = point;
    highlights.append(pill);
  });

  renderCardActions(fragment, item);

  return fragment;
}

function renderFeed(items) {
  refs.newsList.innerHTML = "";
  refs.resultsCount.textContent = `${items.length}건`;

  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "조건에 맞는 피드가 없습니다.";
    refs.newsList.append(empty);
    return;
  }

  items.forEach((item, index) => {
    refs.newsList.append(renderFeedCard(item, index));
  });
}

function toggleStoredId(targetSet, storageKey, itemId) {
  if (targetSet.has(itemId)) {
    targetSet.delete(itemId);
  } else {
    targetSet.add(itemId);
  }
  persistStoredSet(storageKey, targetSet);
}

function formatDelta(value) {
  if (value > 0) {
    return `+${value}`;
  }
  if (value < 0) {
    return `${value}`;
  }
  return "변화 없음";
}

async function shareItem(item) {
  const payload = `${item.headline}\n${item.url}`;
  if (navigator.share) {
    try {
      await navigator.share({ title: item.headline, text: item.summary, url: item.url });
      return;
    } catch (error) {
      if (error?.name !== "AbortError") {
        console.error(error);
      }
    }
  }

  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(payload);
    return;
  }

  window.prompt("링크를 복사하세요", payload);
}

function renderMeta() {
  refs.trackedCount.textContent = String(state.meta.tracked_sources);
  refs.feedStatus.textContent = state.meta.last_persisted_at
    ? `${state.meta.feed_status} · LIVE`
    : state.meta.feed_status;
}

async function loadNews() {
  const response = await fetch("/api/news");
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const payload = await response.json();
  state.feed = [...normalizeArray(payload.news), ...normalizeArray(payload.published)];
  state.sources = payload.sources || [];
  state.sourceStats = payload.source_stats || {};
  state.signals = payload.signals || [];
  state.trendHistory = payload.trend_history || [];
  state.autoCategories = payload.auto_categories || [];
  state.categorySnapshots = payload.category_snapshots || [];
  state.meta = payload.meta;

  const filtered = filterFeed();
  renderMeta();
  renderSources();
  renderSignals();
  renderTrends(filtered);
  renderReports(filtered);
  renderCategories();
  renderFeed(filtered);
}

async function refreshFeed() {
  refs.feedStatus.textContent = "SYNCING";

  try {
    const response = await fetch("/api/refresh", { method: "POST" });
    if (!response.ok) {
      throw new Error(`Refresh failed: ${response.status}`);
    }
    await loadNews();
  } catch (error) {
    refs.feedStatus.textContent = "ERROR";
    console.error(error);
  }
}

async function translateItem(itemId) {
  try {
    const response = await fetch(`/api/articles/${itemId}/translate`, { method: "POST" });
    const payload = await response.json();
    state.feed = normalizeArray(payload.news);
    state.sources = normalizeArray(payload.sources);
    state.sourceStats = payload.source_stats || {};
    state.signals = normalizeArray(payload.signals);
    state.trendHistory = normalizeArray(payload.trend_history);
    state.meta = payload.meta || state.meta;
    rerender();
    renderMeta();
    renderSignals();
  } catch (error) {
    console.error(error);
  }
}

function rerender() {
  const filtered = filterFeed();
  renderTrends(filtered);
  renderReports(filtered);
  renderCategories();
  renderFeed(filtered);
}

function bindControls() {
  refs.search.addEventListener("input", (event) => {
    state.filters.search = event.target.value;
    rerender();
  });

  document.querySelectorAll(".category-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".category-tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      state.activeCategoryWindow = tab.dataset.window;
      renderCategories();
    });
  });

  refs.refreshButton.addEventListener("click", refreshFeed);
}

async function init() {
  state.likedIds = loadStoredSet("drone-pulse-liked");
  state.savedIds = loadStoredSet("drone-pulse-saved");
  bindControls();

  try {
    await loadNews();
  } catch (error) {
    refs.feedStatus.textContent = "OFFLINE";
    refs.newsList.innerHTML =
      '<div class="empty-state">API 서버에 연결할 수 없습니다. `python3 server.py`로 백엔드를 실행하세요.</div>';
    console.error(error);
  }

  window.setInterval(loadNews, 30000);
}

init();
