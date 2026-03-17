'use client';

import React, { useMemo } from 'react';
import type { NewsItem } from '@/lib/types';
import Badge from '@/components/ui/Badge';

/* ── Report-building logic (ported from app.js) ───────── */

const TECH_REPORTS = [
  {
    title: 'Drone',
    titleKo: '드론',
    terms: [
      'drone', 'drones', 'uav', 'uas', 'bvlos', 'evtol', 'air mobility',
      '드론', '무인기', '도심항공', '비행체', 'uam',
    ],
  },
  {
    title: 'Physical AI',
    titleKo: '피지컬 AI',
    terms: [
      'physical ai', 'embodied ai', 'sim2real', 'world model',
      'computer vision', 'edge ai', 'autonomous system',
      '피지컬 ai', '비전 ai', '월드모델', '자율시스템',
    ],
  },
  {
    title: 'Robotics',
    titleKo: '로봇',
    terms: [
      'robot', 'robots', 'robotic', 'robotics', 'humanoid',
      'manipulation', 'mobile robot', 'autonomous robot',
      '로봇', '로보틱스', '휴머노이드', '자율로봇',
    ],
  },
];

const AUTHORITATIVE_SOURCES = new Set([
  'FAA', 'NASA', 'DARPA', 'GAO', 'EASA', 'ICAO', 'OECD',
  'RAND', 'Brookings', 'IEEE', 'Nature', 'Science',
  'Reuters', 'Associated Press', 'Bloomberg',
]);

function isToday(iso: string): boolean {
  if (!iso) return false;
  const d = new Date(iso);
  if (isNaN(d.getTime())) return false;
  const now = new Date();
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  );
}

function sourceCredibility(item: NewsItem): number {
  let score = item.impact || 0;
  const src = (item.source || '').toLowerCase();
  for (const name of AUTHORITATIVE_SOURCES) {
    if (src.includes(name.toLowerCase())) {
      score += 30;
      break;
    }
  }
  const ct = item.content_type || '';
  if (ct === 'report') score += 20;
  if (ct === 'research') score += 15;
  return score;
}

interface Report {
  title: string;
  titleKo: string;
  count: number;
  averageImpact: number;
  keywords: string[];
  summary: string;
  items: NewsItem[];
  hasUpdate: boolean;
}

function buildReports(items: NewsItem[]): Report[] {
  const todayItems = items.filter((i) => isToday(i.timestamp));

  return TECH_REPORTS.map((topic) => {
    const matched = todayItems.filter((item) => {
      const text = `${item.headline} ${item.summary}`.toLowerCase();
      return topic.terms.some((term) => text.includes(term.toLowerCase()));
    });

    matched.sort((a, b) => sourceCredibility(b) - sourceCredibility(a));
    const topItems = matched.slice(0, 3);

    const highlights: string[] = [];
    topItems.forEach((item) => {
      (item.highlights || []).forEach((point) => {
        if (!highlights.includes(point)) highlights.push(point);
      });
    });

    return {
      title: topic.title,
      titleKo: topic.titleKo,
      count: matched.length,
      averageImpact: matched.length
        ? Math.round(matched.reduce((s, i) => s + (Number(i.impact) || 0), 0) / matched.length)
        : 0,
      keywords: highlights.slice(0, 3),
      summary: matched.length
        ? `${matched.length} articles today covering ${highlights.slice(0, 3).join(', ') || 'latest technology'}.`
        : '',
      items: topItems,
      hasUpdate: matched.length > 0,
    };
  });
}

/* ── Components ────────────────────────────────────────── */

function ReportTopicCard({ report }: { report: Report }) {
  return (
    <article className="rounded-2xl border border-muted/10 bg-white p-5 transition-shadow hover:shadow-md">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-display font-bold text-text text-sm">
          {report.titleKo}{' '}
          <span className="text-muted font-normal text-xs">({report.title})</span>
        </h4>
        <Badge variant="default">{report.count} articles</Badge>
      </div>

      <div className="flex items-center gap-2 mb-3">
        <Badge variant="neutral">Impact {report.averageImpact || '-'}</Badge>
      </div>

      <p className="text-xs text-muted leading-relaxed mb-3">{report.summary}</p>

      {report.keywords.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {report.keywords.map((kw) => (
            <span
              key={kw}
              className="inline-block px-2 py-0.5 rounded-full bg-accent/8 text-accent text-[11px] font-medium"
            >
              {kw}
            </span>
          ))}
        </div>
      )}

      {report.items.length > 0 && (
        <div className="flex flex-col gap-1.5">
          {report.items.map((item) => (
            <a
              key={item.id}
              href={item.url}
              target="_blank"
              rel="noreferrer"
              className="block text-xs text-accent hover:text-accent/80 truncate transition-colors"
            >
              {item.translated_headline || item.headline}
            </a>
          ))}
        </div>
      )}
    </article>
  );
}

/* ── Main ──────────────────────────────────────────────── */

export interface RightRailProps {
  items: NewsItem[];
}

export default function RightRail({ items }: RightRailProps) {
  const reports = useMemo(() => buildReports(items), [items]);
  const activeReports = reports.filter((r) => r.hasUpdate);
  const totalToday = activeReports.reduce((s, r) => s + r.count, 0);

  return (
    <aside className="flex flex-col gap-5 w-full">
      {/* Summary header */}
      <section className="rounded-3xl bg-white border border-muted/10 p-6 shadow-sm">
        <h3 className="font-display font-bold text-text text-base mb-1">
          Today&apos;s Tech Report
        </h3>
        {activeReports.length > 0 ? (
          <p className="text-xs text-muted leading-relaxed">
            {activeReports.map((r) => r.titleKo).join(' / ')} &mdash; {totalToday} articles collected
          </p>
        ) : (
          <p className="text-xs text-muted leading-relaxed">
            No related articles collected today yet.
          </p>
        )}
      </section>

      {/* Report cards */}
      {reports.map((report) =>
        report.hasUpdate ? (
          <ReportTopicCard key={report.title} report={report} />
        ) : null,
      )}

      {activeReports.length === 0 && (
        <div className="rounded-2xl border border-dashed border-muted/20 p-8 text-center">
          <p className="text-sm text-muted">Waiting for today&apos;s articles...</p>
        </div>
      )}
    </aside>
  );
}
