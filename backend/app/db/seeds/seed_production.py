"""
Production seed script for Swapneet Lahoti's Apex instance.

Steps:
  1. Creates Supabase Auth user (via Admin API) → gets real UUID
  2. Inserts user row into public.users
  3. Inserts career_profiles row with real aspirations/targets
  4. Seeds 16 target companies

Usage (from backend/ directory):
    python -m app.db.seeds.seed_production
    python -m app.db.seeds.seed_production --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone

# ── User data ─────────────────────────────────────────────────────────────────

USER_EMAIL    = "Swapneet.lahoti@gmail.com"
USER_PASSWORD = "Apex@2026!"          # change after first login
USER_NAME     = "Swapneet Lahoti"

CAREER_PROFILE = {
    "current_role"    : "MBA Student at HEC Paris",
    "target_roles"    : [
        "AI Product Manager",
        "Senior Product Manager",
        "Senior Product Strategy Manager",
        "Corporate Strategy Manager",
        "CEO's Office / Chief of Staff",
        "Founder's Office",
    ],
    "industries"      : ["AI / Tech", "Fintech", "E-commerce", "Big Tech", "Consumer Tech"],
    "aspirations_text": (
        "I want to go into consumer tech and use technology and AI to create and scale "
        "digital products or companies that are consumer facing. My goal is to build a "
        "career at the intersection of product strategy and AI — either leading product "
        "at a fast-growing tech company or eventually founding my own. I bring 4 years "
        "of fintech product management (Axis Bank digital banking), an IIT Kharagpur "
        "engineering foundation, and an HEC Paris MBA (graduating December 2026). "
        "I am actively building agentic AI skills. "
        "Geographic focus: English-speaking roles in Paris, Amsterdam, and London."
    ),
}

# ── Target companies ──────────────────────────────────────────────────────────

COMPANIES = [
    # AI / Foundation Models
    {"name": "Anthropic",      "domain": "anthropic.com",   "industry": "AI / Foundation Models",    "size_range": "201-500",    "location": "San Francisco, USA", "linkedin_url": "https://linkedin.com/company/anthropic"},
    {"name": "OpenAI",         "domain": "openai.com",      "industry": "AI / Foundation Models",    "size_range": "501-1000",   "location": "San Francisco, USA", "linkedin_url": "https://linkedin.com/company/openai"},
    # Fintech
    {"name": "Revolut",        "domain": "revolut.com",     "industry": "Fintech",                   "size_range": "5001-10000", "location": "London, UK",         "linkedin_url": "https://linkedin.com/company/revolut"},
    {"name": "N26",            "domain": "n26.com",         "industry": "Fintech / Neobank",         "size_range": "1001-5000",  "location": "Berlin, Germany",    "linkedin_url": "https://linkedin.com/company/n26-bank"},
    {"name": "Qonto",          "domain": "qonto.com",       "industry": "Fintech / B2B",             "size_range": "501-1000",   "location": "Paris, France",      "linkedin_url": "https://linkedin.com/company/qonto"},
    # Big Tech
    {"name": "Google",         "domain": "google.com",      "industry": "Big Tech",                  "size_range": "10001+",     "location": "Mountain View, USA", "linkedin_url": "https://linkedin.com/company/google"},
    {"name": "Meta",           "domain": "meta.com",        "industry": "Big Tech / Social",         "size_range": "10001+",     "location": "Menlo Park, USA",    "linkedin_url": "https://linkedin.com/company/meta"},
    {"name": "Microsoft",      "domain": "microsoft.com",   "industry": "Big Tech / Enterprise",     "size_range": "10001+",     "location": "Redmond, USA",       "linkedin_url": "https://linkedin.com/company/microsoft"},
    {"name": "Apple",          "domain": "apple.com",       "industry": "Big Tech / Consumer",       "size_range": "10001+",     "location": "Cupertino, USA",     "linkedin_url": "https://linkedin.com/company/apple"},
    {"name": "Netflix",        "domain": "netflix.com",     "industry": "Streaming / Consumer Tech", "size_range": "10001+",     "location": "Los Gatos, USA",     "linkedin_url": "https://linkedin.com/company/netflix"},
    # E-commerce / Marketplace
    {"name": "Booking.com",    "domain": "booking.com",     "industry": "E-commerce / Travel",       "size_range": "10001+",     "location": "Amsterdam, Netherlands", "linkedin_url": "https://linkedin.com/company/booking-com"},
    {"name": "Deliveroo",      "domain": "deliveroo.com",   "industry": "Food Delivery / Consumer",  "size_range": "5001-10000", "location": "London, UK",         "linkedin_url": "https://linkedin.com/company/deliveroo"},
    {"name": "Uber",           "domain": "uber.com",        "industry": "Mobility / Consumer Tech",  "size_range": "10001+",     "location": "San Francisco, USA", "linkedin_url": "https://linkedin.com/company/uber-com"},
    # Micro-mobility / Growth
    {"name": "Bolt",           "domain": "bolt.eu",         "industry": "Mobility / Consumer Tech",  "size_range": "1001-5000",  "location": "Tallinn, Estonia",   "linkedin_url": "https://linkedin.com/company/bolt-eu"},
    {"name": "Lime",           "domain": "li.me",           "industry": "Micro-mobility",            "size_range": "501-1000",   "location": "San Francisco, USA", "linkedin_url": "https://linkedin.com/company/limebike"},
    # Bonus: Paris/EU AI scale-ups relevant to profile
    {"name": "Mistral AI",     "domain": "mistral.ai",      "industry": "AI / Foundation Models",    "size_range": "201-500",    "location": "Paris, France",      "linkedin_url": "https://linkedin.com/company/mistral-ai"},
]


# ── Supabase Admin: create auth user ─────────────────────────────────────────

async def create_supabase_auth_user(supabase_url: str, service_role_key: str) -> str:
    """
    Create (or fetch existing) Supabase Auth user via the Admin API.
    Returns the user UUID.
    """
    try:
        import httpx
    except ImportError:
        print("ERROR: httpx required. Run: pip install httpx", file=sys.stderr)
        sys.exit(1)

    admin_url = f"{supabase_url}/auth/v1/admin/users"
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        # Try to create
        resp = await client.post(
            admin_url,
            headers=headers,
            json={
                "email": USER_EMAIL,
                "password": USER_PASSWORD,
                "email_confirm": True,
            },
            timeout=15.0,
        )

        if resp.status_code == 200:
            user_id = resp.json()["id"]
            print(f"  [OK] Supabase Auth user created: {user_id}")
            return user_id

        # Already exists — fetch by listing users and matching email
        if resp.status_code == 422 and "already" in resp.text.lower():
            list_resp = await client.get(admin_url, headers=headers, timeout=15.0)
            if list_resp.status_code == 200:
                users = list_resp.json().get("users", [])
                for u in users:
                    if u.get("email", "").lower() == USER_EMAIL.lower():
                        user_id = u["id"]
                        print(f"  [EXISTS] Supabase Auth user already exists: {user_id}")
                        return user_id

        print(f"  ERROR creating auth user: {resp.status_code} — {resp.text}", file=sys.stderr)
        sys.exit(1)


# ── SQL seed builders ─────────────────────────────────────────────────────────

def build_statements(user_id: str) -> list[tuple[str, list]]:
    stmts: list[tuple[str, list]] = []
    now = datetime.now(timezone.utc)

    # 1. users row
    stmts.append((
        """
        INSERT INTO users (id, email, full_name, profile_json, preferences_json)
        VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
        ON CONFLICT (id) DO UPDATE SET full_name = EXCLUDED.full_name
        """,
        [user_id, USER_EMAIL, USER_NAME, "{}", "{}"],
    ))

    # 2. career_profiles row — delete existing first (no UNIQUE on user_id)
    stmts.append((
        "DELETE FROM career_profiles WHERE user_id = $1",
        [user_id],
    ))
    stmts.append((
        """
        INSERT INTO career_profiles
            (user_id, "current_role", target_roles, industries, aspirations_text, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6::timestamptz)
        """,
        [
            user_id,
            CAREER_PROFILE["current_role"],
            CAREER_PROFILE["target_roles"],
            CAREER_PROFILE["industries"],
            CAREER_PROFILE["aspirations_text"],
            now,
        ],
    ))

    # 3. companies — skip if name already exists (no UNIQUE on domain)
    for c in COMPANIES:
        company_id = str(uuid.uuid4())
        stmts.append((
            """
            INSERT INTO companies (id, name, domain, industry, size_range, location, linkedin_url)
            SELECT $1, $2, $3, $4, $5, $6, $7
            WHERE NOT EXISTS (SELECT 1 FROM companies WHERE name = $2)
            """,
            [company_id, c["name"], c["domain"], c["industry"],
             c["size_range"], c["location"], c["linkedin_url"]],
        ))

    return stmts


# ── Dry run ───────────────────────────────────────────────────────────────────

def print_dry_run():
    fake_uid = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    print("=" * 70)
    print("DRY RUN — Apex production seed")
    print(f"User:    {USER_NAME} <{USER_EMAIL}>")
    print(f"Profile: {len(CAREER_PROFILE['target_roles'])} target roles, "
          f"{len(CAREER_PROFILE['industries'])} industries")
    print(f"Companies: {len(COMPANIES)}")
    print("=" * 70)
    for i, (sql, params) in enumerate(build_statements(fake_uid), 1):
        print(f"\n-- Statement {i} --")
        print(sql.strip())
        print(f"   Params: {params}")
    print("=" * 70)


# ── Live run ──────────────────────────────────────────────────────────────────

async def run(database_url: str, supabase_url: str, service_role_key: str):
    try:
        import asyncpg
    except ImportError:
        print("ERROR: asyncpg required. Run: pip install asyncpg", file=sys.stderr)
        sys.exit(1)

    print("\n[1/3] Creating Supabase Auth user...")
    user_id = await create_supabase_auth_user(supabase_url, service_role_key)

    print("\n[2/3] Connecting to database...")
    db_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    # statement_cache_size=0 required for Supabase pgbouncer (transaction pooling mode)
    conn = await asyncpg.connect(db_url, statement_cache_size=0)

    print("\n[3/3] Seeding user, career profile, and companies...")
    stmts = build_statements(user_id)
    ok = err = 0
    for sql, params in stmts:
        try:
            async with conn.transaction():
                await conn.execute(sql, *params)
            ok += 1
        except Exception as exc:
            print(f"  WARNING: {exc}", file=sys.stderr)
            err += 1

    await conn.close()
    print(f"\nSeed complete -- {ok} OK, {err} warnings")
    print(f"\n" + "-"*70)
    print(f"  User ID    : {user_id}")
    print(f"  Email      : {USER_EMAIL}")
    print(f"  Password   : {USER_PASSWORD}")
    print("-"*70)
    print(f"\nNext steps:")
    print(f"  1. cd backend && uvicorn app.main:app --reload --port 8000")
    print(f"  2. POST http://localhost:8000/api/v1/auth/login")
    print(f"       {{\"email\": \"{USER_EMAIL}\", \"password\": \"{USER_PASSWORD}\"}}")
    print(f"  3. POST http://localhost:8000/api/v1/signals/ingest  (Bearer <token>)")
    print(f"  4. POST http://localhost:8000/api/v1/profile/analyze (Bearer <token>)")


async def main():
    parser = argparse.ArgumentParser(description="Apex production seed")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        print_dry_run()
        return

    import os, sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from app.core.config import get_settings
    s = get_settings()

    await run(s.DATABASE_URL, s.SUPABASE_URL, s.SUPABASE_SERVICE_ROLE_KEY)


if __name__ == "__main__":
    asyncio.run(main())
