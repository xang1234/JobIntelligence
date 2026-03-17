# Counterfactual Career Delta Engine Plan

## Goal

Build a Counterfactual Career Delta Engine that answers:

- What single change would most improve a candidate's opportunity set?
- Which industry pivots preserve the same or a similar role while increasing reachable jobs, compensation, or market tailwinds?
- Which skills, titles, or career moves produce the best tradeoff between upside and pivot cost?

This should extend the existing profile matching, trend analysis, and search infrastructure rather than creating a parallel system.

## Product Thesis

The platform already does four valuable things:

- profile-to-job matching
- hybrid semantic and keyword retrieval
- trend analysis across roles, skills, and companies
- company similarity and related-skill discovery

The next compounding addition is not another dashboard. It is a decision engine that transforms those primitives into actionable recommendations:

- add skill `X`
- pivot title from `A` to `B`
- stay in the same role but move into industry `Y`
- make a bounded adjacent-role and adjacent-industry move

The system should quantify these moves with explicit before/after evidence instead of producing generic advice text.

## Scope

### In scope

- Counterfactual recommendations for skill, title, and industry pivots
- Same-role industry pivots
- Similar-role industry pivots
- Deterministic scoring with explicit evidence
- API support
- Frontend exploration UI
- Unit and integration tests

### Out of scope for v1

- LLM-generated long-form coaching
- user accounts or saved plans
- fully personalized learning-path generation
- automated resume rewriting
- multi-step optimization across long time horizons

## Existing Reuse Points

The feature should build on existing components:

- Profile matching in `src/mcf/embeddings/search_engine.py`
- Role, skill, company, and overview trend access in `src/mcf/database.py`
- API contracts in `src/api/models.py`
- HTTP route registration in `src/api/app.py`
- Profile-matching UX in `src/frontend/src/pages/MatchLabPage.tsx`

## Core Concept

A **delta scenario** is a synthetic change applied to a candidate profile, then rescored against the market.

Examples:

- add `Kubernetes`
- shift target title from `Data Analyst` to `Analytics Engineer`
- keep title family but move from `Banking` to `HealthTech`
- move from `Operations Analyst` to `Revenue Operations` in SaaS

Each scenario should produce:

- a ranked score
- an estimate of jobs unlocked
- fit improvement
- salary impact
- market momentum
- diversification benefit
- pivot cost
- concrete before/after examples

## Scenario Types

### 1. Skill Addition

Apply one to three high-signal missing or adjacent skills to the candidate profile.

Examples:

- `Python` plus `Airflow`
- `SQL` plus `dbt`
- `Kubernetes`

### 2. Title Pivot

Shift target title while keeping industry broad.

Examples:

- `Data Analyst` -> `Analytics Engineer`
- `Software Engineer` -> `Platform Engineer`

### 3. Industry Pivot, Same Role

Keep the same role family and test performance in a different industry bucket.

Examples:

- `Data Analyst` in Banking -> `Data Analyst` in Logistics
- `Product Manager` in E-commerce -> `Product Manager` in HealthTech

This should be a first-class scenario type because it often has lower pivot cost and higher practical value than a full career change.

### 4. Industry Pivot, Adjacent Role

Shift both role and industry, but only within a bounded semantic distance.

Examples:

- `Operations Analyst` -> `Revenue Operations` in SaaS
- `Compliance Analyst` -> `Risk Analyst` in FinTech

This should carry a higher pivot cost penalty than same-role industry pivots.

## Industry Pivot Design

Industry pivots need explicit handling rather than relying only on title changes.

### Available signals

- `categories` already captured from MCF job data
- company identity
- title text
- skill mix

### v1 industry strategy

Use a deterministic normalized industry taxonomy built from:

- job `categories`
- fallback company-level dominant categories
- fallback keyword heuristics only if categories are sparse

### Industry-pivot rules

- same-role industry pivot requires strong title-family similarity and different industry buckets
- similar-role industry pivot requires both title similarity and industry difference
- cross-industry moves should be rewarded when they unlock more jobs, higher compensation, or stronger momentum
- cross-industry moves should be penalized when title drift and skill-gap cost are too large

## Data Model

Add new API models for a dedicated career-delta endpoint.

### Request

`CareerDeltaRequest`

Fields:

- `profile_text`
- `target_titles`
- `salary_expectation_annual`
- `employment_type`
- `region`
- `current_industry` optional
- `delta_types` optional
- `max_scenarios`

### Response

`CareerDeltaResponse`

Fields:

- `baseline`
- `recommendations`
- `search_time_ms`
- `degraded`

### Recommendation shape

`CareerDeltaScenario`

Fields:

- `delta_type`
- `label`
- `proposed_change`
- `jobs_unlocked`
- `median_salary_delta`
- `demand_momentum`
- `diversification_gain`
- `pivot_cost`
- `confidence`
- `score`
- `why_this_move`
- `risks_or_tradeoffs`
- `before_examples`
- `after_examples`
- `supporting_signals`

## Backend Architecture

Do not keep expanding `SemanticSearchEngine` as a monolith. Add a thin orchestrator layer that reuses it.

### New modules

- `src/mcf/career_delta.py`
- `src/mcf/industry_taxonomy.py`

### Responsibilities

`src/mcf/career_delta.py`

- generate candidate scenarios
- apply synthetic deltas
- call profile matching for baseline and counterfactuals
- score scenarios
- return structured recommendations

`src/mcf/industry_taxonomy.py`

- normalize categories into stable industry buckets
- infer company-level dominant industries
- derive title families
- help determine same-role versus adjacent-role pivots

## Matching and Scoring Strategy

### Baseline

Run the existing profile match flow using the current profile and filters.

Capture:

- top matches
- extracted skills
- average and top fit
- matched industries
- reachable companies
- salary distribution

### Candidate generation

Generate scenario candidates from:

- extracted skills in the current profile
- missing skills in top high-fit jobs
- related skills from adjacent jobs or skill neighborhoods
- adjacent titles from high-fit jobs
- same-title jobs in different industries
- similar companies from company similarity logic

### Candidate constraints

Keep the scenario set small and deterministic:

- top missing skills only
- top adjacent titles only
- same-role industry pivots prioritized
- strict cap on total scenarios

### Counterfactual evaluation

For each scenario:

1. apply the synthetic change
2. rerun profile matching
3. compare against baseline
4. compute composite score

### Composite score

Use weighted components such as:

- `opportunity_gain`: increase in high-fit reachable jobs
- `quality_gain`: increase in mean or top fit score
- `salary_gain`: increase in median annual salary
- `market_tailwind`: role, skill, or industry momentum
- `diversification_gain`: increase in distinct companies or industries unlocked
- `pivot_cost`: penalty based on skill gap and distance from current role or industry

### Industry-specific weighting

- same-role industry pivots should have low pivot-cost penalties
- adjacent-role industry pivots should have higher penalties
- very large pivots should require significantly larger upside to rank well

## Role and Industry Normalization

### Title families

Create a lightweight role-family normalizer using:

- lowercased and cleaned title tokens
- removal of seniority and common noise tokens
- phrase patterns for role families

Examples:

- `Senior Data Analyst` and `Data Analyst` map to the same family
- `Platform Engineer` and `Site Reliability Engineer` may be adjacent families

### Industry taxonomy

Normalize category strings into a manageable set of buckets, for example:

- Banking and Financial Services
- Healthcare and Life Sciences
- Logistics and Supply Chain
- E-commerce and Retail
- SaaS and Enterprise Software
- Public Sector
- Manufacturing and Industrial

The first version should prefer precision over coverage. Unknowns can remain uncategorized rather than forcing noisy assignments.

## API Plan

### Endpoint

Add:

- `POST /api/career-delta`

### Routing

Register the endpoint in `src/api/app.py` using the existing async executor pattern.

### Validation

Add new request and response models to `src/api/models.py`.

Validation should enforce:

- minimum profile length
- bounded scenario counts
- supported delta types
- reasonable title list sizes

## Frontend Plan

The initial UX should be a dedicated surface adjacent to Match Lab, not a dense extension of the current result cards.

### Option for v1

Add a new page:

- `Career Delta`

Navigation target:

- `/career-delta`

### UI sections

- input form reusing profile-match inputs
- baseline summary
- top recommended moves
- same-role industry pivots
- before/after comparison for a selected scenario

### Recommendation card contents

- scenario label
- expected jobs unlocked
- expected salary delta
- current versus target industry
- current versus target role
- top evidence chips
- risk/tradeoff note

### Interaction model

- user pastes profile
- user runs analysis
- recommendations appear ranked
- user selects one recommendation
- UI expands with before/after job examples and missing-skill detail

## Testing Plan

### Unit tests

Add deterministic tests for:

- industry normalization
- title-family normalization
- same-role cross-industry detection
- adjacent-role detection
- scenario generation rules
- score ordering under obvious synthetic examples

### Integration tests

Use the existing database factory style to build small controlled markets and test:

- skill-addition scenarios
- title pivots
- same-role industry pivots
- adjacent-role industry pivots
- degraded-mode behavior

### API tests

Add endpoint tests for:

- valid response shape
- capped scenario count
- no-result profiles
- sparse-category markets
- degraded retrieval fallback

### Frontend tests

Add at least one integration-level UI test once the page structure is stable:

- submit profile
- receive recommendation cards
- expand a scenario
- inspect before/after evidence

## Phased Delivery

### Phase 1

Backend MVP:

- `CareerDeltaRequest` and `CareerDeltaResponse`
- `career_delta.py` orchestrator
- skill-addition scenarios
- title-pivot scenarios
- backend tests

### Phase 2

Industry pivot foundation:

- `industry_taxonomy.py`
- same-role industry pivots
- category normalization tests
- API integration tests

### Phase 3

Expanded pivots:

- adjacent-role industry pivots
- stronger pivot-cost modeling
- more explicit evidence payloads

### Phase 4

Frontend:

- `Career Delta` page
- ranked recommendation cards
- before/after scenario explorer

### Phase 5

Tuning and hardening:

- weight tuning
- latency optimization
- degraded-mode UX polish
- broader regression coverage

## MVP Acceptance Criteria

- Given a realistic profile, the system returns three to five ranked recommendations.
- At least one recommendation can be an industry pivot for the same or a very similar role.
- Each recommendation includes explicit evidence, not just a score.
- The endpoint works in degraded mode using deterministic fallback retrieval.
- Recommendations are stable under test fixtures and do not depend on free-form generation.

## Key Design Principles

- Prefer deterministic recommendation logic over free-form advice generation.
- Reuse existing retrieval and trend infrastructure.
- Keep industry pivots first-class rather than hiding them inside title pivots.
- Optimize for explainability, testability, and product compounding value.
- Penalize unrealistic pivots unless their upside clearly exceeds the transition cost.

## Recommended First Slice

Implement the smallest useful slice in this order:

1. baseline profile analysis
2. skill-addition scenarios
3. title pivots
4. same-role industry pivots
5. response payload and API endpoint
6. frontend page

This gets a useful engine into the product quickly while preserving a clean path toward richer industry and adjacent-role recommendations.
