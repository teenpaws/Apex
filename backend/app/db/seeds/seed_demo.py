"""
Demo seed data — 5 companies, 5 signals, 3 opportunities.

Run via: python -m app.db.seeds.seed_demo
Or via Docker: docker-compose exec backend python -m app.db.seeds.seed_demo

Idempotent: checks for existing demo data before inserting.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"

DEMO_COMPANIES = [
    {
        "id": "10000000-0000-0000-0000-000000000001",
        "name": "Stripe",
        "domain": "stripe.com",
        "industry": "Fintech",
        "size_range": "1000-5000",
        "location": "San Francisco, CA",
    },
    {
        "id": "10000000-0000-0000-0000-000000000002",
        "name": "Revolut",
        "domain": "revolut.com",
        "industry": "Fintech",
        "size_range": "5000-10000",
        "location": "London, UK",
    },
    {
        "id": "10000000-0000-0000-0000-000000000003",
        "name": "McKinsey & Company",
        "domain": "mckinsey.com",
        "industry": "Consulting",
        "size_range": "10000+",
        "location": "New York, NY",
    },
    {
        "id": "10000000-0000-0000-0000-000000000004",
        "name": "Sequoia Capital",
        "domain": "sequoiacap.com",
        "industry": "Private Equity",
        "size_range": "100-500",
        "location": "Menlo Park, CA",
    },
    {
        "id": "10000000-0000-0000-0000-000000000005",
        "name": "Palantir Technologies",
        "domain": "palantir.com",
        "industry": "Technology",
        "size_range": "1000-5000",
        "location": "Denver, CO",
    },
]

DEMO_SIGNALS = [
    {
        "id": "20000000-0000-0000-0000-000000000001",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000001",
        "type": "FUNDING",
        "source": "demo-seed",
        "title": "Stripe raises $6.5B at $50B valuation to expand globally",
        "description": "Stripe, the payments infrastructure company, closed a $6.5B funding round. The company plans to hire 1,000 engineers and expand its enterprise sales and strategy divisions across EMEA and APAC.",
        "relevance_score": 0.92,
        "signal_date": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
    },
    {
        "id": "20000000-0000-0000-0000-000000000002",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000001",
        "type": "EXEC_HIRE",
        "source": "demo-seed",
        "title": "Stripe hires new Chief Strategy Officer from Goldman Sachs",
        "description": "Stripe announced the appointment of a new CSO with 15 years of investment banking experience. The hire signals a push into enterprise financial services and M&A advisory capabilities.",
        "relevance_score": 0.88,
        "signal_date": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
    },
    {
        "id": "20000000-0000-0000-0000-000000000003",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000002",
        "type": "EXPANSION",
        "source": "demo-seed",
        "title": "Revolut receives banking licence, expands to 10 new EU markets",
        "description": "Revolut has received its European banking licence and is rapidly expanding into Central and Eastern European markets. The company is hiring 500 people in operations, compliance, and business development roles.",
        "relevance_score": 0.85,
        "signal_date": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
    },
    {
        "id": "20000000-0000-0000-0000-000000000004",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000003",
        "type": "CONTRACT",
        "source": "demo-seed",
        "title": "McKinsey wins $200M digital transformation contract with EU government",
        "description": "McKinsey secured a major multi-year contract with the European Commission for digital public services transformation. The practice is hiring senior project managers and strategy consultants with public sector experience.",
        "relevance_score": 0.79,
        "signal_date": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
    },
    {
        "id": "20000000-0000-0000-0000-000000000005",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000004",
        "type": "FUNDING",
        "source": "demo-seed",
        "title": "Sequoia Capital closes $2.85B global growth fund",
        "description": "Sequoia Capital announced the close of its latest global growth equity fund. The firm is expanding its portfolio operations team and hiring investment associates with operational consulting backgrounds.",
        "relevance_score": 0.81,
        "signal_date": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
    },
]

DEMO_OPPORTUNITIES = [
    {
        "id": "30000000-0000-0000-0000-000000000001",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000001",
        "predicted_role": "Head of EMEA Strategy",
        "confidence": "HIGH",
        "timeline_weeks": 6,
        "why_fit": "Stripe's $6.5B raise and CSO hire from Goldman signals a build-out of their enterprise strategy function. Your MBA + consulting background positions you well for a regional strategy leadership role.",
        "approach_angle": "Lead with PE deal experience and EMEA market knowledge from your MBA exchanges.",
        "fit_score": 82.0,
        "status": "PREDICTED",
        "signal_ids": [
            "20000000-0000-0000-0000-000000000001",
            "20000000-0000-0000-0000-000000000002",
        ],
        "predicted_salary_range": "£120,000-£160,000 + equity",
    },
    {
        "id": "30000000-0000-0000-0000-000000000002",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000002",
        "predicted_role": "Business Development Manager — Eastern Europe",
        "confidence": "MEDIUM",
        "timeline_weeks": 8,
        "why_fit": "Revolut's EU banking licence and 10-market expansion creates immediate need for BizDev managers with local market knowledge. MBA from HEC gives you European market credibility.",
        "approach_angle": "Highlight European market entry experience from coursework and any exchange experience.",
        "fit_score": 71.0,
        "status": "PREDICTED",
        "signal_ids": ["20000000-0000-0000-0000-000000000003"],
        "predicted_salary_range": "£80,000-£110,000 + bonus",
    },
    {
        "id": "30000000-0000-0000-0000-000000000003",
        "user_id": DEMO_USER_ID,
        "company_id": "10000000-0000-0000-0000-000000000004",
        "predicted_role": "Investment Associate — Portfolio Operations",
        "confidence": "MEDIUM",
        "timeline_weeks": 12,
        "why_fit": "Sequoia's new $2.85B fund means portfolio expansion. Operations associates help portfolio companies scale — a role that maps directly to consulting + MBA skill sets.",
        "approach_angle": "Frame consulting as portfolio operations experience — operational improvement, not just advice.",
        "fit_score": 68.0,
        "status": "PREDICTED",
        "signal_ids": ["20000000-0000-0000-0000-000000000005"],
        "predicted_salary_range": "£90,000-£130,000 + carry",
    },
]


async def seed_demo() -> None:
    """Insert demo data into Supabase. Idempotent — skips existing rows."""
    import asyncpg  # noqa: PLC0415
    from app.db.session import get_asyncpg_db_url  # noqa: PLC0415

    db_url = get_asyncpg_db_url()
    conn = await asyncpg.connect(db_url, statement_cache_size=0)

    try:
        # User must exist before signals/opportunities (FK constraint)
        await conn.execute(
            """
            INSERT INTO users (id, email, full_name, profile_json, preferences_json)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO NOTHING
            """,
            uuid.UUID(DEMO_USER_ID),
            "demo@apex.dev",
            "Demo User",
            "{}",
            "{}",
        )
        logger.info("Seeded demo user")

        # Companies
        for co in DEMO_COMPANIES:
            await conn.execute(
                """
                INSERT INTO companies (id, name, domain, industry, size_range, location)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO NOTHING
                """,
                uuid.UUID(co["id"]), co["name"], co["domain"],
                co["industry"], co["size_range"], co["location"],
            )
        logger.info("Seeded %d demo companies", len(DEMO_COMPANIES))

        # Signals
        for sig in DEMO_SIGNALS:
            await conn.execute(
                """
                INSERT INTO signals (id, user_id, company_id, type, source, title,
                                     description, relevance_score, signal_date)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (id) DO NOTHING
                """,
                uuid.UUID(sig["id"]),
                uuid.UUID(sig["user_id"]),
                uuid.UUID(sig["company_id"]),
                sig["type"],
                sig["source"],
                sig["title"],
                sig["description"],
                sig["relevance_score"],
                datetime.fromisoformat(sig["signal_date"]),
            )
        logger.info("Seeded %d demo signals", len(DEMO_SIGNALS))

        # Opportunities — DB column is approach_angle (renamed from positioning_notes in Migration 017)
        for opp in DEMO_OPPORTUNITIES:
            await conn.execute(
                """
                INSERT INTO opportunities (id, user_id, company_id, predicted_role,
                                           confidence, timeline_weeks, why_fit,
                                           approach_angle, fit_score, status,
                                           signal_ids, predicted_salary_range)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (id) DO NOTHING
                """,
                uuid.UUID(opp["id"]),
                uuid.UUID(opp["user_id"]),
                uuid.UUID(opp["company_id"]),
                opp["predicted_role"],
                opp["confidence"],
                opp["timeline_weeks"],
                opp["why_fit"],
                opp.get("approach_angle", ""),
                opp["fit_score"],
                opp["status"],
                [uuid.UUID(sid) for sid in opp["signal_ids"]],
                opp.get("predicted_salary_range", ""),
            )
        logger.info("Seeded %d demo opportunities", len(DEMO_OPPORTUNITIES))

        logger.info("Demo seed complete")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(seed_demo())
