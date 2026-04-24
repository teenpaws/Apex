# Multi-User Self-Host Distribution — Design Spec

**Date:** 2026-04-24
**Status:** Approved, ready for implementation planning
**Scope:** Phases 20–24 (post-Phase-19)

---

## 1. Goal

Transform Apex from "one developer's local dev setup" into a codebase that any reasonably motivated non-technical user can deploy as their own personal tool — without Swapneet running any infrastructure or paying any ongoing cost.

The primary audience is the HEC MBA cohort and similar graduate-level job seekers who understand AI tools broadly but are not software engineers.

---

## 2. Strategic Decisions (Locked)

### 2.1 Distribution Model
**Self-host, open-source, bring-your-own-keys (BYOK).** Not SaaS.

- User clones the public repo and deploys it themselves (Railway primary, Docker secondary)
- User creates their own Supabase project and supplies their own API keys
- User pays each vendor directly for their own usage
- Swapneet pays $0 ongoing; runs no infrastructure

SaaS is deferred indefinitely and would only be revisited if HEC or a sponsor funds hosting. Architecture preserves the pivot option (see §2.7).

### 2.2 Database
**Each install = one user's own Supabase project.** Free tier (500MB DB + 500MB storage) is sufficient for a single user's corpus.

- On first install: user creates a Supabase project, pastes our single consolidated `schema/initial.sql` into the Supabase SQL Editor, clicks Run. App is immediately ready.
- No incremental migration system shipped to users. The `supabase/migrations/` folder exists in git for history only — downstream forks are responsible for applying changes if they pull updates.

### 2.3 Deploy Path
**Railway primary, Docker secondary.**

- **Railway** (recommended for non-technical users): "Deploy on Railway" button in README → Railway forks the repo → provisions backend, worker, Redis, frontend from `railway.json` → user pastes API keys into Railway's env var UI → app is live at a public URL. Cost to user: ~$5–10/month for compute. Total install time ~30–45 minutes.
- **Docker Compose** (for technical users / offline / privacy-conscious): existing `docker-compose.yml` from Phase 11, polished in Phase 14's launch-package sprint.

### 2.4 Auth Model
**Keep Supabase Auth; ship with public signups disabled by default.**

- Zero code rewrite — Supabase Auth is already integrated throughout the codebase (RLS policies, JWT flow, `get_current_user` dependency)
- On first install, a bootstrap script creates one owner account from env vars (`OWNER_EMAIL`, `OWNER_PASSWORD`)
- Supabase public-signup toggle is **off** in setup docs — only the seeded owner can log in
- Multi-device works for free (log in from laptop AND phone with the same credentials)
- To pivot to cohort-sharing or SaaS later: flip the public-signup toggle back on. No code changes.

### 2.5 License
**MIT License.**

- Shortest license, well-understood, zero compliance burden
- Anyone can fork, modify, redistribute, or monetize; only requirement is preserving the copyright notice
- Matches the "ship it and walk away" ethos — no obligations for Swapneet to enforce or track

### 2.6 Release Model
**No formal release cadence.**

- The GitHub repo is public and anyone can fork
- Swapneet maintains his own copy at his own pace; does not promise versioned releases
- Downstream users pull from GitHub whenever they want; they are responsible for reconciling schema or config changes in their own fork (with Claude's help, which is part of the documented support story)

### 2.7 SaaS-Pivot Readiness
Preserved passively via existing architecture:
- All tables are `user_id`-scoped (RLS enforced)
- `agent_runs` audit table tracks cost per user (needed for metering)
- All config is env-var-driven (no hardcoded secrets or IDs)
- Mock-mode flags (`MOCK_AGENTS`, `USE_MOCK_DATA`) gate any dev-only code paths

One-time audit in Phase 20 confirms these guardrails hold. No new SaaS-specific code is written until/unless the pivot happens.

---

## 3. Phases

Five sequential (with one parallel window) phases enable the distribution flip.

### Phase 20 — Self-Host Foundations
**Goal:** Make the codebase safe to clone, deploy, and operate by someone who is not Swapneet.

**Scope:**
- Generate a consolidated `schema/initial.sql` that creates all tables, RLS policies, pgvector extension, indexes, and any required seed reference data from scratch
- Bootstrap script (`scripts/bootstrap_owner.py`) that reads `OWNER_EMAIL` + `OWNER_PASSWORD` from env and creates a single Supabase Auth user on first boot
- Backend boot-time check: refuse to serve requests if no owner account exists; log a clear instruction to run the bootstrap
- Grep audit: remove any hardcoded user IDs, user names, HEC-specific strings, or absolute paths from non-prompt code paths
- Config audit: verify every API key, URL, and feature flag reads from environment variables
- SaaS-pivot readiness audit: confirm `user_id` scoping is intact, mock flags gate dev-only paths, `agent_runs` still writes on every agent call

**Out of scope:** Railway config (Phase 21), in-app wizards (Phase 22), docs (Phase 23).

### Phase 21 — Railway Deploy Template
**Goal:** "Deploy on Railway" button in README works end-to-end from a fresh fork.

**Scope:**
- `railway.json` (or `railway.toml`) defining services: backend (web), celery-worker, redis, frontend
- Build commands, start commands, and health checks per service
- `railway-env.md` listing every env var Railway needs, with per-variable "where to get this" notes
- Deploy-button markdown snippet for README
- End-to-end smoke test: fresh fork → click deploy → paste env vars → verify all four services come up, frontend loads, signal ingestion runs

**Out of scope:** Docs polish (Phase 23), launch announcement (Phase 24).

### Phase 22 — First-Run Setup Experience
**Goal:** A newly-deployed install tells the user exactly what's missing and how to fix it.

**Scope:**
- `GET /api/v1/system/status` endpoint that tests each integration with a lightweight call (Anthropic `list_models`, NewsData sample fetch, etc.) and returns `{ok | missing_key | invalid_key | unreachable}` per integration
- Frontend "System Status" page accessible from Settings, showing per-integration green/yellow/red
- First-login redirect: if any critical integration is missing/invalid, route to `/setup` instead of Dashboard
- `/setup` wizard: one screen per missing integration with (a) what the key does, (b) link to signup page, (c) instructions to paste into Railway's env var UI, (d) re-check button
- Clear, copy-pasteable error messages when a key is invalid (so the user can paste the full error into Claude for help)

**Parallel with Phase 21** after Phase 20 completes.

**Out of scope:** Runtime key editing (Railway env vars are set in Railway's UI, not mutable at runtime from inside the app).

### Phase 23 — Non-Technical User Documentation
**Goal:** A first-time user with no CS background can deploy and start using Apex from the README in under 45 minutes.

**Scope:**
- `QUICKSTART.md` rewritten with step-by-step instructions and screenshots for: Supabase signup, schema paste, API key signups (all 6), Railway deploy click, env var entry, first-run wizard
- `API-KEYS.md` with signup links and "where to find the key" screenshots for each provider
- `TROUBLESHOOTING.md` with common errors and the "paste the error into Claude" pattern
- `LICENSE` (MIT), `CONTRIBUTING.md`, `SECURITY.md`
- Optional but high-leverage: 5–10 minute screencast walkthrough posted as a repo asset

**Depends on:** Phase 21 (real deploy flow to document) and Phase 22 (real wizard to screenshot).

### Phase 24 — Public Launch Polish
**Goal:** The repo is ready to share publicly with MBA cohorts, social networks, and anyone who finds it.

**Scope:**
- README with hero image/GIF, feature list, "Deploy on Railway" button, screenshots of key pages, install paths (Railway primary / Docker secondary)
- GitHub Issue templates (bug, feature request, question)
- Basic GitHub Actions CI running backend tests on PRs (helps forkers verify their changes)
- Optional opt-in anonymous install counter (one-time ping on first boot, purely for Swapneet's curiosity — easy to disable via env var)
- Demo seed data toggle (`DEMO_MODE=true` loads sample signals, opportunities, actions so first-time users can see it work before wiring up real ingestion)
- Cohort announcement — share with HEC MBA cohort, LinkedIn post, any other channels Swapneet wants

**Depends on:** everything above.

---

## 4. Dependencies

```
Phase 19 (Analytics + Backtesting) — prerequisite
                ↓
        Phase 20 (Self-Host Foundations)
                ↓
        ┌───────┴───────┐
        ↓               ↓
   Phase 21        Phase 22
   (Railway)      (First-Run UX)
        └───────┬───────┘
                ↓
        Phase 23 (Docs + Screenshots)
                ↓
        Phase 24 (Launch Polish)
```

Phase 21 and Phase 22 can run in parallel after Phase 20; both are prerequisites for Phase 23's screenshots. Phases 15–19 must ship first — no point polishing distribution until the product is at Swapneet's satisfaction threshold.

---

## 5. Explicitly Out of Scope

- **SaaS hosting** — deferred indefinitely unless externally funded
- **Paid data integrations** (Crunchbase, LinkedIn API, premium news) — free tier stays
- **Mobile apps, native installers** — Tauri/Electron path rejected as too much work for marginal gain
- **Formal release cadence / versioned updates** — users fork at a point in time
- **Customer support infrastructure** — GitHub Issues only; no Discord, no email support
- **Incremental migration system for downstream users** — only the one-shot `initial.sql` is supported
- **Multi-tenant SaaS plumbing** (billing, metering, tenant isolation) — architecturally possible later, not built now
- **LinkedIn API official integration** — already deferred to v1.5 in CLAUDE.md
- **Adversarial/red-team testing** — deferred to v1.5; not required for self-host MVP since each install's attack surface is tiny

---

## 6. Success Criteria

- A non-technical user (tested with at least one HEC classmate) can go from "never heard of Apex" to "logged in and looking at my first real opportunity" in under 45 minutes, using only the public README as guidance.
- No paid services required from Swapneet — the repo is fully self-supporting.
- The SaaS pivot path remains architecturally viable: if HEC or a sponsor asks to fund hosting, flipping the public-signup toggle and adding an ingress is the only code change needed.

---

## 7. Open Questions (Deferred to Phase 23/24)

- Exactly which screencast tool for the walkthrough video
- Whether to include a demo seed data set tailored to a specific industry (MBA generalist vs PE-focused vs tech-focused) — defer decision to when demo mode is built
- Whether to publish on any specific directories (GitHub Trending, awesome lists, MBA Reddit) — defer to launch phase

These do not affect the design shape and can be decided during implementation.
