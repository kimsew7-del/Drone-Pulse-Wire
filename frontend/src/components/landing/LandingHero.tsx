'use client';

import React from 'react';
import Link from 'next/link';
import Button from '@/components/ui/Button';

export default function LandingHero() {
  return (
    <section className="relative px-6 py-16 sm:py-24">
      {/* Hero gradient background */}
      <div className="absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute top-12 left-1/2 -translate-x-1/2 w-[800px] h-[600px] rounded-full bg-gradient-to-br from-accent/10 via-accent-2/5 to-transparent blur-3xl" />
      </div>

      <div className="mx-auto flex max-w-6xl flex-col gap-14">
        <div className="flex flex-col items-center justify-center min-h-[70vh] text-center">
          <span className="inline-block px-4 py-1.5 rounded-full bg-accent/10 text-accent text-xs font-semibold uppercase tracking-widest mb-6">
            AI-Powered News Intelligence
          </span>

          <h1 className="text-4xl sm:text-5xl font-display font-bold text-text mb-4 max-w-2xl leading-tight">
            나만의 뉴스 인텔리전스
            <br />
            <span className="text-accent">Briefwave</span>
          </h1>

          <p className="text-base sm:text-lg text-muted mb-8 max-w-lg leading-relaxed">
            관심 키워드를 설정하면, 글로벌 뉴스·논문·리포트를 자동으로 수집하고
            AI가 분석해 드립니다.
          </p>

          <Link href="/login">
            <Button variant="primary">시작하기</Button>
          </Link>
          <p className="mt-3 text-xs text-muted">
            계정이 없으신가요?{' '}
            <Link href="/login?mode=register" className="text-accent font-semibold hover:text-accent/80 transition-colors">
              회원가입
            </Link>
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mt-16 max-w-3xl w-full">
            {[
              {
                title: '키워드 구독',
                desc: '관심 분야의 키워드를 설정하고 자동 수집',
              },
              {
                title: '글로벌 소스',
                desc: '뉴스 API, RSS, 학술 DB를 하나의 피드로 통합',
              },
              {
                title: '실시간 피드',
                desc: '사용자별 맞춤 기사 흐름과 트렌드 신호 제공',
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className="rounded-2xl bg-white/80 backdrop-blur-sm border border-muted/10 p-5 text-left"
              >
                <h3 className="text-sm font-bold text-text mb-1">{feature.title}</h3>
                <p className="text-xs text-muted leading-relaxed">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel rounded-[2rem] p-6 sm:p-10">
          <div className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-start">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent mb-4">
                Project Overview
              </p>
              <h2 className="font-display text-3xl sm:text-4xl font-bold text-text leading-tight">
                흩어진 드론·AI 정보를
                <br />
                개인화된 판단용 피드로 바꿉니다
              </h2>
              <p className="mt-5 max-w-2xl text-sm sm:text-base leading-7 text-muted">
                Briefwave는 글로벌 뉴스, 논문, 리포트를 자동으로 수집한 뒤 중복을
                정리하고, 번역과 분류, 구독 기반 필터링을 거쳐 사용자별 인사이트
                피드로 재구성합니다.
              </p>
            </div>

            <div className="grid gap-4">
              {[
                ['수집', 'RSS, 뉴스 API, 연구 데이터베이스에서 자동 확보'],
                ['정리', '중복 제거와 카테고리 분류로 핵심 변화만 압축'],
                ['개인화', '키워드, 지역, 언어 조건으로 맞춤 피드 구성'],
                ['활용', '번역, 트렌드, 소스 모니터링으로 빠른 판단 지원'],
              ].map(([title, desc], index) => (
                <div
                  key={title}
                  className="rounded-2xl border border-[color:var(--line)] bg-white/70 px-5 py-4 text-left"
                >
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">
                    Step {index + 1}
                  </p>
                  <h3 className="mt-2 text-base font-semibold text-text">{title}</h3>
                  <p className="mt-1 text-sm leading-6 text-muted">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
