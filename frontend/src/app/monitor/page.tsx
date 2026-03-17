'use client';

import React, { useState, useCallback, useMemo } from 'react';
import { useNews } from '@/hooks/useNews';
import { useCrawlJob } from '@/hooks/useCrawlJob';
import { useAuth } from '@/hooks/useAuth';
import { startCrawl, resetCrawl, clearReports } from '@/lib/api';
import { useToast } from '@/components/ui/Toast';
import ReportCard from '@/components/monitor/ReportCard';
import CrawlJobPanel from '@/components/monitor/CrawlJobPanel';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';

const ALL_REGIONS = [
  'Global', 'US', 'EU', 'UK', 'Korea', 'Japan', 'China', 'India',
  'Southeast Asia', 'Middle East', 'Australia', 'Africa', 'Latin America',
];

export default function MonitorPage() {
  const { data, isLoading, mutate: mutateNews } = useNews();
  const { data: crawlJob, isRunning, mutate: mutateCrawl } = useCrawlJob();
  const { token } = useAuth();
  const { addToast } = useToast();

  // Crawl controls state
  const [topicInput, setTopicInput] = useState('');
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [regionFilter, setRegionFilter] = useState('');
  const [docTypeFilter, setDocTypeFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');

  const reports = data?.reports || [];
  const reportStats = data?.report_stats || { total: 0, source_count: 0, regions: [] };

  // Compute breakdowns
  const breakdowns = useMemo(() => {
    const byDocType: Record<string, number> = {};
    const byRegion: Record<string, number> = {};
    const bySrc: Record<string, number> = {};

    reports.forEach((r) => {
      const dt = r.doc_type || 'unknown';
      byDocType[dt] = (byDocType[dt] || 0) + 1;

      const rg = r.region || 'unknown';
      byRegion[rg] = (byRegion[rg] || 0) + 1;

      const src = r.source || 'unknown';
      bySrc[src] = (bySrc[src] || 0) + 1;
    });

    return { byDocType, byRegion, bySource: bySrc };
  }, [reports]);

  // Filter reports
  const filteredReports = useMemo(() => {
    let items = reports;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      items = items.filter((item) => {
        const text = [item.headline, item.translated_headline, item.summary, item.source, item.region]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return text.includes(q);
      });
    }

    if (regionFilter) {
      items = items.filter((item) => item.region === regionFilter);
    }

    if (docTypeFilter) {
      items = items.filter((item) => item.doc_type === docTypeFilter);
    }

    if (sourceFilter) {
      items = items.filter((item) => item.source === sourceFilter);
    }

    items.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
    return items;
  }, [reports, searchQuery, regionFilter, docTypeFilter, sourceFilter]);

  // Auth guard helper
  const requireAuth = useCallback(
    (action: string): boolean => {
      if (!token) {
        addToast({ type: 'error', title: 'Login required', message: `Please log in to ${action}.` });
        return false;
      }
      return true;
    },
    [token, addToast],
  );

  // Crawl actions
  const handleStartTopicCrawl = useCallback(async () => {
    if (!requireAuth('start crawl')) return;
    if (!topicInput.trim()) {
      addToast({ type: 'error', title: 'Topic required', message: 'Enter a topic keyword to crawl.' });
      return;
    }
    try {
      await startCrawl({ seeds: [topicInput.trim()] }, token!);
      setTopicInput('');
      await mutateCrawl();
      addToast({ type: 'success', title: 'Topic crawl started' });
    } catch (err) {
      addToast({ type: 'error', title: 'Crawl failed', message: String(err) });
    }
  }, [topicInput, token, mutateCrawl, addToast, requireAuth]);

  const handleStartStatsCrawl = useCallback(async () => {
    if (!requireAuth('start crawl')) return;
    try {
      await startCrawl({}, token!);
      await mutateCrawl();
      addToast({ type: 'success', title: 'Stats crawl started' });
    } catch (err) {
      addToast({ type: 'error', title: 'Crawl failed', message: String(err) });
    }
  }, [token, mutateCrawl, addToast, requireAuth]);

  const handleStartRegionCrawl = useCallback(async () => {
    if (!requireAuth('start crawl')) return;
    if (selectedRegions.length === 0) {
      addToast({ type: 'error', title: 'Region required', message: 'Select at least one region.' });
      return;
    }
    try {
      await startCrawl({ regions: selectedRegions }, token!);
      setSelectedRegions([]);
      await mutateCrawl();
      addToast({ type: 'success', title: 'Region crawl started' });
    } catch (err) {
      addToast({ type: 'error', title: 'Crawl failed', message: String(err) });
    }
  }, [selectedRegions, token, mutateCrawl, addToast, requireAuth]);

  const handleReset = useCallback(async () => {
    if (!requireAuth('reset crawl')) return;
    try {
      await resetCrawl(token!);
      await mutateCrawl();
      addToast({ type: 'success', title: 'Crawl reset' });
    } catch (err) {
      addToast({ type: 'error', title: 'Reset failed', message: String(err) });
    }
  }, [token, mutateCrawl, addToast, requireAuth]);

  const handleClearReports = useCallback(async () => {
    if (!requireAuth('clear reports')) return;
    try {
      await clearReports(token!);
      await mutateNews();
      addToast({ type: 'success', title: 'Reports cleared' });
    } catch (err) {
      addToast({ type: 'error', title: 'Clear failed', message: String(err) });
    }
  }, [token, mutateNews, addToast, requireAuth]);

  const toggleRegion = useCallback((region: string) => {
    setSelectedRegions((prev) =>
      prev.includes(region) ? prev.filter((r) => r !== region) : [...prev, region],
    );
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 rounded-full border-4 border-accent/30 border-t-accent animate-spin" />
          <p className="text-sm text-muted font-medium">Loading reports...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6">
        {/* Sidebar */}
        <aside className="flex flex-col gap-5">
          {/* Stats panel */}
          <section className="rounded-3xl bg-gradient-to-br from-accent via-accent-2 to-accent-3 p-6 text-white shadow-lg relative overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,rgba(255,255,255,0.15),transparent_60%)]" />
            <div className="relative z-10">
              <span className="inline-block px-2.5 py-1 rounded-full bg-white/20 text-[10px] font-semibold uppercase tracking-widest mb-3">
                Report Monitor
              </span>
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div className="flex flex-col">
                  <span className="text-3xl font-display font-bold leading-none">{reportStats.total}</span>
                  <span className="text-[11px] text-white/70 mt-1">Total Reports</span>
                </div>
                <div className="flex flex-col">
                  <span className="text-3xl font-display font-bold leading-none">{reportStats.source_count}</span>
                  <span className="text-[11px] text-white/70 mt-1">Sources</span>
                </div>
              </div>
            </div>
          </section>

          {/* Doc type breakdown */}
          <section className="rounded-3xl bg-white border border-muted/10 p-5 shadow-sm">
            <h3 className="font-display font-bold text-text text-sm mb-3">By Document Type</h3>
            <div className="flex flex-col gap-2">
              {Object.entries(breakdowns.byDocType)
                .sort((a, b) => b[1] - a[1])
                .map(([type, count]) => (
                  <button
                    key={type}
                    onClick={() => setDocTypeFilter((prev) => (prev === type ? '' : type))}
                    className={`flex items-center justify-between rounded-2xl px-3 py-2 text-left transition-colors ${
                      docTypeFilter === type
                        ? 'bg-accent/10 border border-accent/20'
                        : 'bg-bg/50 hover:bg-accent/5 border border-transparent'
                    }`}
                  >
                    <span className="text-xs font-semibold text-text">{type}</span>
                    <span className="text-xs text-muted font-medium">{count}</span>
                  </button>
                ))}
              {Object.keys(breakdowns.byDocType).length === 0 && (
                <p className="text-xs text-muted text-center py-2">No data yet</p>
              )}
            </div>
          </section>

          {/* Region breakdown */}
          <section className="rounded-3xl bg-white border border-muted/10 p-5 shadow-sm">
            <h3 className="font-display font-bold text-text text-sm mb-3">By Region</h3>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(breakdowns.byRegion)
                .sort((a, b) => b[1] - a[1])
                .map(([region, count]) => (
                  <button
                    key={region}
                    onClick={() => setRegionFilter((prev) => (prev === region ? '' : region))}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                      regionFilter === region
                        ? 'bg-accent/15 text-accent'
                        : 'bg-bg text-muted hover:bg-accent/5 hover:text-text'
                    }`}
                  >
                    {region}
                    <span className="text-[10px] opacity-60">{count}</span>
                  </button>
                ))}
              {Object.keys(breakdowns.byRegion).length === 0 && (
                <p className="text-xs text-muted text-center py-2 w-full">No data yet</p>
              )}
            </div>
          </section>

          {/* Crawl control panel */}
          <section className="rounded-3xl bg-white border border-muted/10 p-5 shadow-sm">
            <h3 className="font-display font-bold text-text text-sm mb-4">Crawl Control</h3>

            {/* Topic crawl */}
            <div className="mb-4">
              <label className="text-[11px] text-muted font-semibold uppercase tracking-wide block mb-1.5">
                Topic Crawl
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={topicInput}
                  onChange={(e) => setTopicInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleStartTopicCrawl()}
                  placeholder="e.g. drone delivery"
                  className="flex-1 px-3 py-2 rounded-xl border border-muted/15 text-sm text-text placeholder:text-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent/40 transition-all"
                />
                <Button size="sm" onClick={handleStartTopicCrawl} disabled={isRunning}>
                  Start
                </Button>
              </div>
            </div>

            {/* Stats crawl */}
            <div className="mb-4">
              <label className="text-[11px] text-muted font-semibold uppercase tracking-wide block mb-1.5">
                Stats Crawl
              </label>
              <Button size="sm" onClick={handleStartStatsCrawl} disabled={isRunning} className="w-full">
                Start Stats Crawl
              </Button>
            </div>

            {/* Region crawl */}
            <div className="mb-4">
              <label className="text-[11px] text-muted font-semibold uppercase tracking-wide block mb-1.5">
                Region Crawl
              </label>
              <div className="flex flex-wrap gap-1.5 mb-2">
                {ALL_REGIONS.map((region) => (
                  <button
                    key={region}
                    onClick={() => toggleRegion(region)}
                    className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
                      selectedRegions.includes(region)
                        ? 'bg-accent/15 text-accent border border-accent/30'
                        : 'bg-bg text-muted hover:bg-accent/5 border border-transparent'
                    }`}
                  >
                    {region}
                  </button>
                ))}
              </div>
              <Button size="sm" onClick={handleStartRegionCrawl} disabled={isRunning || selectedRegions.length === 0} className="w-full">
                Start Region Crawl ({selectedRegions.length})
              </Button>
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-3 border-t border-muted/10">
              <Button variant="danger" size="sm" onClick={handleClearReports} className="flex-1">
                Clear Reports
              </Button>
            </div>
          </section>

          {/* Crawl job status */}
          {crawlJob && <CrawlJobPanel job={crawlJob} onReset={handleReset} />}
        </aside>

        {/* Feed section */}
        <div className="flex flex-col gap-4">
          {/* Search and filter bar */}
          <div className="flex flex-col gap-3">
            <div className="relative">
              <svg
                className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted pointer-events-none"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search reports..."
                className="w-full pl-11 pr-4 py-3 rounded-2xl bg-white border border-muted/15 text-sm text-text placeholder:text-muted/50 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent/40 transition-all"
              />
            </div>

            {/* Active filters */}
            {(regionFilter || docTypeFilter || sourceFilter) && (
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs text-muted font-medium">Filters:</span>
                {regionFilter && (
                  <button
                    onClick={() => setRegionFilter('')}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-accent/15 text-accent text-xs font-medium hover:bg-accent/25 transition-colors"
                  >
                    Region: {regionFilter} <span>&times;</span>
                  </button>
                )}
                {docTypeFilter && (
                  <button
                    onClick={() => setDocTypeFilter('')}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-accent/15 text-accent text-xs font-medium hover:bg-accent/25 transition-colors"
                  >
                    Type: {docTypeFilter} <span>&times;</span>
                  </button>
                )}
                {sourceFilter && (
                  <button
                    onClick={() => setSourceFilter('')}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-accent/15 text-accent text-xs font-medium hover:bg-accent/25 transition-colors"
                  >
                    Source: {sourceFilter} <span>&times;</span>
                  </button>
                )}
              </div>
            )}

            {/* Source filter chips */}
            {Object.keys(breakdowns.bySource).length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(breakdowns.bySource)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 10)
                  .map(([src, count]) => (
                    <button
                      key={src}
                      onClick={() => setSourceFilter((prev) => (prev === src ? '' : src))}
                      className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
                        sourceFilter === src
                          ? 'bg-accent/15 text-accent'
                          : 'bg-bg text-muted hover:bg-accent/5 hover:text-text'
                      }`}
                    >
                      {src}
                      <span className="text-[10px] opacity-60">{count}</span>
                    </button>
                  ))}
              </div>
            )}
          </div>

          {/* Results count */}
          <p className="text-xs text-muted font-medium px-1">
            {filteredReports.length} report{filteredReports.length !== 1 ? 's' : ''}
          </p>

          {/* Report list */}
          {filteredReports.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-muted/20 p-12 text-center">
              <p className="text-sm text-muted">No reports match the current filters.</p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {filteredReports.map((item, index) => (
                <div
                  key={item.id}
                  className="animate-[fadeIn_0.3s_ease-out_both]"
                  style={{ animationDelay: `${index * 40}ms` }}
                >
                  <ReportCard item={item} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
