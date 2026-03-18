import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import JobCard from '@/components/JobCard'
import { analyzeCareerDelta, matchProfile } from '@/services/api'
import { buildCareerDeltaAnalysisRequest, buildProfileMatchRequest } from '@/services/matchLab'
import type { CareerDeltaScenarioSummary, MatchLabSharedInputs } from '@/types/api'

type MatchLabTab = 'match' | 'what-if'

function tabButtonClass(isActive: boolean): string {
  return isActive
    ? 'bg-[color:var(--brand)] text-white shadow-lg'
    : 'bg-[color:var(--surface)] text-slate-600 hover:text-[color:var(--brand)]'
}

function WhatIfScenarioPreview({ scenario }: { scenario: CareerDeltaScenarioSummary }) {
  return (
    <article className="rounded-[24px] border border-[color:var(--border)] bg-white/90 p-5">
      <div className="flex flex-wrap items-center gap-3">
        <span className="rounded-full bg-[color:var(--surface)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
          {scenario.scenario_type.replaceAll('_', ' ')}
        </span>
        <span className="text-sm font-semibold text-[color:var(--ink)]">
          {(scenario.confidence.score * 100).toFixed(0)} confidence
        </span>
      </div>
      <h3 className="mt-3 text-lg font-semibold text-[color:var(--ink)]">{scenario.title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-600">{scenario.summary}</p>
    </article>
  )
}

export default function MatchLabPage() {
  const [activeTab, setActiveTab] = useState<MatchLabTab>('match')
  const [inputs, setInputs] = useState<MatchLabSharedInputs>({
    profileText:
      'Senior data professional with Python, SQL, machine learning, experimentation, stakeholder management, and dashboarding experience. Looking for Singapore-based roles in AI, analytics, or applied ML.',
    targetTitles: 'Data Scientist, Machine Learning Engineer',
    salaryExpectation: '180000',
    employmentType: '',
    region: '',
  })

  const matchMutation = useMutation({
    mutationFn: () => matchProfile(buildProfileMatchRequest(inputs)),
  })

  const whatIfMutation = useMutation({
    mutationFn: () => analyzeCareerDelta(buildCareerDeltaAnalysisRequest(inputs)),
  })

  const inputsReady = inputs.profileText.trim().length >= 20
  const anyPending = matchMutation.isPending || whatIfMutation.isPending

  const runCurrentMatch = () => {
    setActiveTab('match')
    matchMutation.mutate()
  }

  const runWhatIf = () => {
    setActiveTab('what-if')
    whatIfMutation.mutate()
  }

  return (
    <div className="space-y-8">
      <section className="rounded-[32px] border border-[color:var(--border)] bg-white/90 p-8 shadow-[0_24px_80px_rgba(15,23,42,0.08)]">
        <p className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-500">Match lab</p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-[color:var(--ink)]">
          Paste a profile and inspect both current fit and improvement paths.
        </h1>
        <p className="mt-3 max-w-3xl text-base leading-7 text-slate-600">
          Stay in one workflow: score what fits now, then switch into What If to see how the same
          profile could move toward stronger scenarios without re-entering the context.
        </p>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <article className="rounded-[28px] border border-[color:var(--border)] bg-white/90 p-6">
          <label className="block text-sm font-semibold text-[color:var(--ink)]">
            Candidate profile or resume text
            <textarea
              value={inputs.profileText}
              onChange={(event) => setInputs((current) => ({ ...current, profileText: event.target.value }))}
              rows={12}
              className="mt-3 block w-full rounded-[24px] border border-[color:var(--border)] bg-[color:var(--surface)] px-4 py-4 text-sm leading-6 text-slate-700"
            />
          </label>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <label className="text-sm text-slate-600">
              Target titles
              <input
                value={inputs.targetTitles}
                onChange={(event) => setInputs((current) => ({ ...current, targetTitles: event.target.value }))}
                placeholder="Data Scientist, ML Engineer"
                className="mt-1 block w-full rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] px-4 py-3"
              />
            </label>
            <label className="text-sm text-slate-600">
              Salary expectation (annual)
              <input
                value={inputs.salaryExpectation}
                onChange={(event) =>
                  setInputs((current) => ({ ...current, salaryExpectation: event.target.value }))
                }
                type="number"
                min={0}
                className="mt-1 block w-full rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] px-4 py-3"
              />
            </label>
            <label className="text-sm text-slate-600">
              Employment type
              <input
                value={inputs.employmentType}
                onChange={(event) => setInputs((current) => ({ ...current, employmentType: event.target.value }))}
                placeholder="Full Time"
                className="mt-1 block w-full rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] px-4 py-3"
              />
            </label>
            <label className="text-sm text-slate-600">
              Region
              <input
                value={inputs.region}
                onChange={(event) => setInputs((current) => ({ ...current, region: event.target.value }))}
                placeholder="Central"
                className="mt-1 block w-full rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] px-4 py-3"
              />
            </label>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={runCurrentMatch}
              disabled={anyPending || !inputsReady}
              className="rounded-full bg-[color:var(--brand)] px-5 py-3 text-sm font-semibold text-white shadow-lg transition hover:bg-[color:var(--brand-strong)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {matchMutation.isPending ? 'Scoring profile...' : 'Run profile match'}
            </button>
            <button
              type="button"
              onClick={runWhatIf}
              disabled={anyPending || !inputsReady}
              className="rounded-full border border-[color:var(--brand)] bg-white px-5 py-3 text-sm font-semibold text-[color:var(--brand)] transition hover:bg-[color:var(--surface)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {whatIfMutation.isPending ? 'Running What If...' : 'Run What If'}
            </button>
          </div>
        </article>

        <article className="space-y-5">
          <div className="rounded-[28px] border border-[color:var(--border)] bg-white/90 p-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Result shell</p>
                <h2 className="mt-2 text-2xl font-semibold text-[color:var(--ink)]">
                  One profile, two analysis modes.
                </h2>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setActiveTab('match')}
                  className={`rounded-full px-4 py-2 text-sm font-semibold transition ${tabButtonClass(activeTab === 'match')}`}
                >
                  Current Match
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('what-if')}
                  className={`rounded-full px-4 py-2 text-sm font-semibold transition ${tabButtonClass(activeTab === 'what-if')}`}
                >
                  What If
                </button>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-3 text-sm text-slate-600">
              <span>
                Shared profile context:{' '}
                <span className="font-semibold text-[color:var(--ink)]">
                  {inputsReady ? 'ready' : 'needs more detail'}
                </span>
              </span>
            </div>
          </div>

          {activeTab === 'match' ? (
            <>
              <div className="rounded-[28px] border border-[color:var(--border)] bg-white/90 p-6">
                <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
                  <span>
                    Candidates scanned:{' '}
                    <span className="font-semibold text-[color:var(--ink)]">
                      {matchMutation.data?.total_candidates.toLocaleString() ?? 0}
                    </span>
                  </span>
                  <span>{matchMutation.data ? `${matchMutation.data.search_time_ms.toFixed(0)}ms` : null}</span>
                  {matchMutation.data?.degraded && (
                    <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
                      degraded retrieval
                    </span>
                  )}
                </div>

                <div className="mt-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Extracted skills</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {matchMutation.data?.extracted_skills.length ? (
                      matchMutation.data.extracted_skills.map((skill) => (
                        <span key={skill} className="rounded-full bg-[color:var(--surface)] px-3 py-1 text-xs font-medium text-slate-700">
                          {skill}
                        </span>
                      ))
                    ) : (
                      <span className="text-sm text-slate-500">Run a profile match to inspect extracted skills.</span>
                    )}
                  </div>
                </div>
              </div>

              {matchMutation.error ? (
                <div className="rounded-[24px] border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-900">
                  {matchMutation.error instanceof Error ? matchMutation.error.message : 'Current match request failed.'}
                </div>
              ) : null}

              <div className="space-y-4">
                {matchMutation.data?.results.length ? (
                  matchMutation.data.results.map((job) => (
                    <JobCard key={job.uuid} job={job} />
                  ))
                ) : (
                  <div className="rounded-[28px] border border-dashed border-[color:var(--border)] bg-white/70 p-10 text-center text-sm text-slate-500">
                    Match results will appear here with score decomposition and missing-skill signals.
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <div className="rounded-[28px] border border-[color:var(--border)] bg-white/90 p-6">
                <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
                  <span>
                    Scenario count:{' '}
                    <span className="font-semibold text-[color:var(--ink)]">
                      {whatIfMutation.data?.scenarios.length ?? 0}
                    </span>
                  </span>
                  <span>
                    Analysis time:{' '}
                    <span className="font-semibold text-[color:var(--ink)]">
                      {whatIfMutation.data?.analysis_time_ms?.toFixed(0) ?? '0'}ms
                    </span>
                  </span>
                  {whatIfMutation.data?.thin_market && (
                    <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
                      thin market
                    </span>
                  )}
                  {whatIfMutation.data?.degraded && (
                    <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
                      degraded retrieval
                    </span>
                  )}
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div className="rounded-[24px] bg-[color:var(--surface)] px-5 py-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Market position</p>
                    <p className="mt-2 text-2xl font-semibold capitalize text-[color:var(--ink)]">
                      {whatIfMutation.data?.baseline?.position ?? 'pending'}
                    </p>
                  </div>
                  <div className="rounded-[24px] bg-[color:var(--surface)] px-5 py-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Reachable jobs</p>
                    <p className="mt-2 text-2xl font-semibold text-[color:var(--ink)]">
                      {whatIfMutation.data?.baseline?.reachable_jobs ?? 0}
                    </p>
                  </div>
                </div>
              </div>

              {whatIfMutation.error ? (
                <div className="rounded-[24px] border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-900">
                  {whatIfMutation.error instanceof Error ? whatIfMutation.error.message : 'What If request failed.'}
                </div>
              ) : null}

              <div className="space-y-4">
                {whatIfMutation.data?.scenarios.length ? (
                  whatIfMutation.data.scenarios.map((scenario) => (
                    <WhatIfScenarioPreview key={scenario.scenario_id} scenario={scenario} />
                  ))
                ) : (
                  <div className="rounded-[28px] border border-dashed border-[color:var(--border)] bg-white/70 p-10 text-center text-sm text-slate-500">
                    What If results will appear here once you run counterfactual analysis from the shared profile inputs.
                  </div>
                )}
              </div>
            </>
          )}
        </article>
      </section>
    </div>
  )
}
