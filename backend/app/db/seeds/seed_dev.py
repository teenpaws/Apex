"""
Development seed data script for the Apex platform.

Inserts:
  - 1 test user (test@apex.dev, fixed UUID for reproducibility)
  - 5 companies (mix of tech and consulting)
  - 10 signals across FUNDING, EXEC_HIRE, EXPANSION types
  - 3 opportunities (HIGH / MEDIUM / SPECULATIVE confidence)
  - 5 actions in various statuses

Usage:
    # Dry run — prints SQL without executing
    python -m app.db.seeds.seed_dev --dry-run

    # Live run — requires a real DATABASE_URL in .env
    python -m app.db.seeds.seed_dev

NOTE: Uses asyncpg directly (no SQLAlchemy overhead). Requires asyncpg to be
installed and DATABASE_URL to point at a live Postgres instance.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from datetime import datetime, timezone, timedelta

# ── Fixed test UUIDs (reproducible across runs) ────────────────────────────────

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"

COMPANY_IDS = [
    "10000000-0000-0000-0000-000000000001",
    "10000000-0000-0000-0000-000000000002",
    "10000000-0000-0000-0000-000000000003",
    "10000000-0000-0000-0000-000000000004",
    "10000000-0000-0000-0000-000000000005",
]

SIGNAL_IDS = [str(uuid.uuid4()) for _ in range(10)]
OPP_IDS = [str(uuid.uuid4()) for _ in range(3)]
ACTION_IDS = [str(uuid.uuid4()) for _ in range(5)]

now = datetime.now(timezone.utc)


# ── Seed data definitions ──────────────────────────────────────────────────────

USERS = [
    {
        "id": TEST_USER_ID,
        "email": "test@apex.dev",
        "full_name": "Apex Test User",
        "profile_json": "{}",
        "preferences_json": "{}",
    }
]

COMPANIES = [
    {
        "id": COMPANY_IDS[0],
        "name": "Mistral AI",
        "domain": "mistral.ai",
        "industry": "Artificial Intelligence",
        "size_range": "51-200",
        "location": "Paris, France",
        "linkedin_url": "https://linkedin.com/company/mistral-ai",
    },
    {
        "id": COMPANY_IDS[1],
        "name": "McKinsey & Company",
        "domain": "mckinsey.com",
        "industry": "Management Consulting",
        "size_range": "10001+",
        "location": "New York, USA",
        "linkedin_url": "https://linkedin.com/company/mckinsey",
    },
    {
        "id": COMPANY_IDS[2],
        "name": "Dataiku",
        "domain": "dataiku.com",
        "industry": "Enterprise Software",
        "size_range": "501-1000",
        "location": "New York, USA",
        "linkedin_url": "https://linkedin.com/company/dataiku",
    },
    {
        "id": COMPANY_IDS[3],
        "name": "Contentsquare",
        "domain": "contentsquare.com",
        "industry": "Analytics",
        "size_range": "1001-5000",
        "location": "Paris, France",
        "linkedin_url": "https://linkedin.com/company/contentsquare",
    },
    {
        "id": COMPANY_IDS[4],
        "name": "Ledger",
        "domain": "ledger.com",
        "industry": "Fintech / Crypto",
        "size_range": "501-1000",
        "location": "Paris, France",
        "linkedin_url": "https://linkedin.com/company/ledger-sas",
    },
]

SIGNALS = [
    {
        "id": SIGNAL_IDS[0],
        "user_id": TEST_USER_ID,
        "company_id": COMPANY_IDS[0],
        "type": "FUNDING",
        "source": "TechCrunch",
        "title": "Mistral AI raises €600M Series B",
        "description": "Paris-based LLM startup Mistral raises record Series B to expand enterprise sales team.",
        "raw_data_json": '{"url": "https://techcrunch.com/2024/06/11/mistral-ai-funding", "amount_eur": 600000000}',
        "signal_date": (now - timedelta(days=5)).isoformat(),
        "relevance_score": 0.92,
        "is_duplicate": False,
        "dedup_hash": "hash_mistral_funding_2024",
    },
    {
        "id": SIGNAL_IDS[1],
        "user_id": TEST_USER_ID,
        "company_id": COMPANY_IDS[0],
        "type": "EXEC_HIRE",
        "source": "LinkedIn",
        "title": "Mistral AI hires VP of Strategy from Google DeepMind",
        "description": "New VP of Strategy joining from DeepMind suggests enterprise expansion push.",
        "raw_data_json": '{"linkedin_url": "https://linkedin.com/in/example-vp"}',
        "signal_date": (now - timedelta(days=3)).isoformat(),
        "relevance_score": 0.78,
        "is_duplicate": False,
        "dedup_hash": "hash_mistral_exec_hire_2024",
    },
    {
        "id": SIGNAL_IDS[2],
        "user_id": TEST_USER_ID,
        "company_id": COMPANY_IDS[1],
        "type": "EXPANSION",
        "source": "McKinsey Press Release",
        "title": "McKinsey opens AI Center of Excellence in Paris",
        "description": "New QuantumBlack AI hub in Paris targeting 150 hires over 18 months.",
        "raw_data_json": '{"source_url": "https://mckinsey.com/press/2024"}',
        "signal_date": (now - timedelta(days=10)).isoformat(),
        "relevance_score": 0.85,
        "is_duplicate": False,
        "dedup_hash": "hash_mckinsey_expansion_2024",
    },
    {
        "id": SIGNAL_IDS[3],
        "user_id": TEST_USER_ID,
        "company_id": COMPANY_IDS[1],
        "type": "JOB_POSTING_PATTERN",
        "source": "LinkedIn Jobs",
        "title": "McKinsey posting 12 AI/ML strategy roles in 30 days",
        "description": "Spike in AI-adjacent postings signals new practice area buildout.",
        "raw_data_json": '{"job_count": 12, "period_days": 30}',
        "signal_date": (now - timedelta(days=2)).isoformat(),
        "relevance_score": 0.71,
        "is_duplicate": False,
        "dedup_hash": "hash_mckinsey_jobs_2024",
    },
    {
        "id": SIGNAL_IDS[4],
        "user_id": TEST_USER_ID,
        "company_id": COMPANY_IDS[2],
        "type": "FUNDING",
        "source": "Crunchbase",
        "title": "Dataiku closes $200M Series F",
        "description": "Dataiku raises Series F to accelerate go-to-market in Europe.",
        "raw_data_json": '{"amount_usd": 200000000, "lead_investor": "Tiger Global"}',
        "signal_date": (now - timedelta(days=15)).isoformat(),
        "relevance_score": 0.88,
        "is_duplicate": False,
        "dedup_hash": "hash_dataiku_funding_2024",
    },
    {
        "id": SIGNAL_IDS[5],
        "user_id": TEST_USER_ID,
        "company_id": COMPANY_IDS[2],
        "type": "EXEC_HIRE",
        "source": "LinkedIn",
        "title": "Dataiku appoints new Chief Revenue Officer from Salesforce",
        "description": "Enterprise sales leadership change following Series F close.",
        "raw_data_json": '{"prev_company": "Salesforce", "title": "CRO"}',
        "signal_date": (now - timedelta(days=7)).isoformat(),
        "relevance_score": 0.80,
        "is_duplicate": False,
        "dedup_hash": "hash_dataiku_exec_hire_2024",
    },
    {
        "id": SIGNAL_IDS[6],
        "user_id": TEST_USER_ID,
        "company_id": COMPANY_IDS[3],
        "type": "EXPANSION",
        "source": "Les Echos",
        "title": "Contentsquare expanding into APAC — opening Singapore office",
        "description": "New APAC HQ in Singapore; hiring 50 across sales, CS, and product.",
        "raw_data_json": '{"region": "APAC", "headcount_target": 50}',
        "signal_date": (now - timedelta(days=20)).isoformat(),
        "relevance_score": 0.65,
        "is_duplicate": False,
        "dedup_hash": "hash_contentsquare_expansion_2024",
    },
    {
        "id": SIGNAL_IDS[7],
        "user_id": TEST_USER_ID,
        "company_id": COMPANY_IDS[4],
        "type": "FUNDING",
        "source": "Dealroom",
        "title": "Ledger raises $100M to expand B2B custody offering",
        "description": "Ledger enterprise division targets institutional crypto custody market.",
        "raw_data_json": '{"amount_usd": 100000000, "focus": "B2B custody"}',
        "signal_date": (now - timedelta(days=8)).isoformat(),
        "relevance_score": 0.74,
        "is_duplicate": False,
        "dedup_hash": "hash_ledger_funding_2024",
    },
    {
        "id": SIGNAL_IDS[8],
        "user_id": TEST_USER_ID,
        "company_id": COMPANY_IDS[4],
        "type": "EXEC_HIRE",
        "source": "LinkedIn",
        "title": "Ledger hires Head of Institutional Sales from BNP Paribas",
        "description": "Senior hire from traditional finance signals institutional pivot.",
        "raw_data_json": '{"prev_company": "BNP Paribas", "title": "Head of Institutional Sales"}',
        "signal_date": (now - timedelta(days=4)).isoformat(),
        "relevance_score": 0.69,
        "is_duplicate": False,
        "dedup_hash": "hash_ledger_exec_hire_2024",
    },
    {
        "id": SIGNAL_IDS[9],
        "user_id": TEST_USER_ID,
        "company_id": COMPANY_IDS[0],
        "type": "CONTRACT",
        "source": "SEC EDGAR",
        "title": "Mistral AI signs enterprise licensing deal with French government",
        "description": "Government contract validates enterprise readiness — hiring for public sector team.",
        "raw_data_json": '{"contract_value_eur": "undisclosed", "client": "French Government"}',
        "signal_date": (now - timedelta(days=1)).isoformat(),
        "relevance_score": 0.90,
        "is_duplicate": False,
        "dedup_hash": "hash_mistral_contract_2024",
    },
]

OPPORTUNITIES = [
    {
        "id": OPP_IDS[0],
        "user_id": TEST_USER_ID,
        "company_id": COMPANY_IDS[0],
        "predicted_role": "Head of Strategy & Business Development",
        "confidence": "HIGH",
        "timeline_weeks": 6,
        "why_fit": "Post-funding growth + enterprise push perfectly aligns with MBA strategy + tech background.",
        "approach_angle": "Lead with enterprise GTM experience; highlight cross-functional leadership at scale.",
        "predicted_salary_range": "€120,000 – €160,000 + equity",
        "fit_score": 87.5,
        "signal_ids": f"{{{SIGNAL_IDS[0]},{SIGNAL_IDS[1]},{SIGNAL_IDS[9]}}}",
        "status": "PREDICTED",
    },
    {
        "id": OPP_IDS[1],
        "user_id": TEST_USER_ID,
        "company_id": COMPANY_IDS[1],
        "predicted_role": "AI Strategy Consultant (Engagement Manager track)",
        "confidence": "MEDIUM",
        "timeline_weeks": 10,
        "why_fit": "Paris AI CoE expansion creates demand for bilingual MBA candidates with AI fluency.",
        "approach_angle": "Emphasize Paris network + AI coursework; mention HEC connection to QuantumBlack alumni.",
        "predicted_salary_range": "€95,000 – €130,000 + bonus",
        "fit_score": 72.0,
        "signal_ids": f"{{{SIGNAL_IDS[2]},{SIGNAL_IDS[3]}}}",
        "status": "PREDICTED",
    },
    {
        "id": OPP_IDS[2],
        "user_id": TEST_USER_ID,
        "company_id": COMPANY_IDS[2],
        "predicted_role": "Strategic Partnerships Manager",
        "confidence": "SPECULATIVE",
        "timeline_weeks": 14,
        "why_fit": "Series F GTM acceleration may create partnership roles but timeline is uncertain.",
        "approach_angle": "Warm intro path via HEC alumni at Dataiku — check LinkedIn before cold outreach.",
        "predicted_salary_range": "€85,000 – €110,000",
        "fit_score": 58.0,
        "signal_ids": f"{{{SIGNAL_IDS[4]},{SIGNAL_IDS[5]}}}",
        "status": "PREDICTED",
    },
]

ACTIONS = [
    {
        "id": ACTION_IDS[0],
        "user_id": TEST_USER_ID,
        "opportunity_id": OPP_IDS[0],
        "company_id": COMPANY_IDS[0],
        "title": "Send introduction email to Mistral AI VP of Strategy",
        "description": "Draft personalized outreach referencing the €600M raise and enterprise government contract.",
        "type": "OUTREACH",
        "priority": "HIGH",
        "status": "TODO",
        "due_date": (now + timedelta(days=2)).isoformat(),
        "ai_draft_json": "{}",
    },
    {
        "id": ACTION_IDS[1],
        "user_id": TEST_USER_ID,
        "opportunity_id": OPP_IDS[0],
        "company_id": COMPANY_IDS[0],
        "title": "Research Mistral AI enterprise product roadmap",
        "description": "Review Mistral blog + GitHub releases to understand product direction before outreach.",
        "type": "RESEARCH",
        "priority": "HIGH",
        "status": "IN_PROGRESS",
        "due_date": (now + timedelta(days=1)).isoformat(),
        "ai_draft_json": "{}",
    },
    {
        "id": ACTION_IDS[2],
        "user_id": TEST_USER_ID,
        "opportunity_id": OPP_IDS[1],
        "company_id": COMPANY_IDS[1],
        "title": "Connect with McKinsey QuantumBlack alumni on LinkedIn",
        "description": "Send connection requests to 3 HEC alumni working at McKinsey QuantumBlack Paris.",
        "type": "OUTREACH",
        "priority": "MEDIUM",
        "status": "TODO",
        "due_date": (now + timedelta(days=5)).isoformat(),
        "ai_draft_json": "{}",
    },
    {
        "id": ACTION_IDS[3],
        "user_id": TEST_USER_ID,
        "opportunity_id": OPP_IDS[1],
        "company_id": COMPANY_IDS[1],
        "title": "Follow up with McKinsey recruiter from HEC careers fair",
        "description": "Follow up email referencing AI CoE announcement to check on open roles.",
        "type": "FOLLOW_UP",
        "priority": "MEDIUM",
        "status": "SNOOZED",
        "due_date": (now + timedelta(days=14)).isoformat(),
        "ai_draft_json": "{}",
    },
    {
        "id": ACTION_IDS[4],
        "user_id": TEST_USER_ID,
        "opportunity_id": OPP_IDS[2],
        "company_id": COMPANY_IDS[2],
        "title": "Schedule informational call with Dataiku HEC alumnus",
        "description": "Warm intro call to understand team structure before formal application.",
        "type": "CALL",
        "priority": "LOW",
        "status": "DONE",
        "due_date": (now - timedelta(days=1)).isoformat(),
        "ai_draft_json": "{}",
    },
]


# ── SQL helpers ────────────────────────────────────────────────────────────────

def build_seed_statements() -> list[tuple[str, list]]:
    """
    Return a list of (sql_template, params) tuples for all seed data.
    Used in both dry-run (print) and live (execute) modes.
    """
    stmts: list[tuple[str, list]] = []

    for u in USERS:
        stmts.append((
            """
            INSERT INTO users (id, email, full_name, profile_json, preferences_json)
            VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
            ON CONFLICT (id) DO NOTHING
            """,
            [u["id"], u["email"], u["full_name"], u["profile_json"], u["preferences_json"]],
        ))

    for c in COMPANIES:
        stmts.append((
            """
            INSERT INTO companies (id, name, domain, industry, size_range, location, linkedin_url)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (id) DO NOTHING
            """,
            [c["id"], c["name"], c["domain"], c["industry"], c["size_range"], c["location"], c["linkedin_url"]],
        ))

    for s in SIGNALS:
        stmts.append((
            """
            INSERT INTO signals (id, user_id, company_id, type, source, title, description,
                                 raw_data_json, signal_date, relevance_score, is_duplicate, dedup_hash)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::timestamptz, $10, $11, $12)
            ON CONFLICT (dedup_hash) DO NOTHING
            """,
            [
                s["id"], s["user_id"], s["company_id"], s["type"], s["source"],
                s["title"], s["description"], s["raw_data_json"], s["signal_date"],
                s["relevance_score"], s["is_duplicate"], s["dedup_hash"],
            ],
        ))

    for o in OPPORTUNITIES:
        stmts.append((
            """
            INSERT INTO opportunities (id, user_id, company_id, predicted_role, confidence,
                                       timeline_weeks, why_fit, approach_angle,
                                       predicted_salary_range, fit_score, signal_ids, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::uuid[], $12)
            ON CONFLICT (id) DO NOTHING
            """,
            [
                o["id"], o["user_id"], o["company_id"], o["predicted_role"], o["confidence"],
                o["timeline_weeks"], o["why_fit"], o["approach_angle"],
                o["predicted_salary_range"], o["fit_score"], o["signal_ids"], o["status"],
            ],
        ))

    for a in ACTIONS:
        stmts.append((
            """
            INSERT INTO actions (id, user_id, opportunity_id, company_id, title, description,
                                 type, priority, status, due_date, ai_draft_json)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::timestamptz, $11::jsonb)
            ON CONFLICT (id) DO NOTHING
            """,
            [
                a["id"], a["user_id"], a["opportunity_id"], a["company_id"],
                a["title"], a["description"], a["type"], a["priority"],
                a["status"], a["due_date"], a["ai_draft_json"],
            ],
        ))

    return stmts


def print_dry_run():
    """Print all seed SQL statements with their parameters."""
    print("=" * 70)
    print("DRY RUN — Apex dev seed data")
    print("=" * 70)
    stmts = build_seed_statements()
    for i, (sql, params) in enumerate(stmts, 1):
        print(f"\n-- Statement {i} --")
        print(sql.strip())
        print(f"   Params: {params}")
    print(f"\n{'=' * 70}")
    print(f"Total statements: {len(stmts)}")
    print(f"  Users:         {len(USERS)}")
    print(f"  Companies:     {len(COMPANIES)}")
    print(f"  Signals:       {len(SIGNALS)}")
    print(f"  Opportunities: {len(OPPORTUNITIES)}")
    print(f"  Actions:       {len(ACTIONS)}")
    print("=" * 70)


async def run_seed(database_url: str):
    """Execute all seed statements against the database."""
    try:
        import asyncpg
    except ImportError as e:
        print(f"ERROR: asyncpg is required. Run: pip install asyncpg\n{e}", file=sys.stderr)
        sys.exit(1)

    # Convert SQLAlchemy-style URL to raw asyncpg URL if needed
    db_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    print(f"Connecting to: {db_url[:40]}...")
    conn = await asyncpg.connect(db_url)

    stmts = build_seed_statements()
    inserted = 0
    errors = 0

    async with conn.transaction():
        for sql, params in stmts:
            try:
                await conn.execute(sql, *params)
                inserted += 1
            except Exception as exc:
                print(f"  WARNING: {exc}", file=sys.stderr)
                errors += 1

    await conn.close()
    print(f"Seed complete. {inserted} statements executed, {errors} warnings.")


async def main():
    parser = argparse.ArgumentParser(description="Apex dev seed data script")
    parser.add_argument("--dry-run", action="store_true", help="Print SQL without executing")
    args = parser.parse_args()

    if args.dry_run:
        print_dry_run()
        return

    # Load settings for DATABASE_URL
    import os
    import sys
    # Allow running as a module from backend/
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

    from app.core.config import get_settings
    settings = get_settings()

    if "placeholder" in settings.DATABASE_URL or "password@localhost" in settings.DATABASE_URL:
        print(
            "ERROR: DATABASE_URL is still a placeholder. "
            "Set a real Supabase connection string in .env before running the live seed.",
            file=sys.stderr,
        )
        sys.exit(1)

    await run_seed(settings.DATABASE_URL)


if __name__ == "__main__":
    asyncio.run(main())
