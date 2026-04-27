"""
Seed 15 target companies tailored to Swapneet Lahoti's profile.

Wipes existing companies first (safe — no signals/opps reference them yet).
Run from backend/: C:\\Python314\\python.exe scripts/seed_swapneet_companies.py
"""
import asyncio, asyncpg, os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

COMPANIES = [
    # ── Fintech / Neobanks (direct Axis-adjacent — 6) ─────────────────────────
    {"name": "Revolut",     "domain": "revolut.com",     "industry": "Fintech / Neobank",         "size_range": "5001-10000", "location": "London, UK",            "linkedin_url": "https://linkedin.com/company/revolut"},
    {"name": "N26",         "domain": "n26.com",         "industry": "Fintech / Neobank",         "size_range": "1001-5000",  "location": "Berlin, Germany",       "linkedin_url": "https://linkedin.com/company/n26-bank"},
    {"name": "Qonto",       "domain": "qonto.com",       "industry": "Fintech / B2B SMB",         "size_range": "501-1000",   "location": "Paris, France",         "linkedin_url": "https://linkedin.com/company/qonto"},
    {"name": "Wise",        "domain": "wise.com",        "industry": "Fintech / Cross-border",    "size_range": "5001-10000", "location": "London, UK",            "linkedin_url": "https://linkedin.com/company/wise"},
    {"name": "Klarna",      "domain": "klarna.com",      "industry": "Fintech / BNPL",            "size_range": "5001-10000", "location": "Stockholm, Sweden",     "linkedin_url": "https://linkedin.com/company/klarna"},
    {"name": "Adyen",       "domain": "adyen.com",       "industry": "Fintech / Payments",        "size_range": "5001-10000", "location": "Amsterdam, Netherlands","linkedin_url": "https://linkedin.com/company/adyen"},

    # ── E-commerce + Consumer tech (Europe + ME — 3) ──────────────────────────
    {"name": "Booking.com", "domain": "booking.com",     "industry": "E-commerce / Travel",       "size_range": "10001+",     "location": "Amsterdam, Netherlands","linkedin_url": "https://linkedin.com/company/booking-com"},
    {"name": "Noon",        "domain": "noon.com",        "industry": "E-commerce",                "size_range": "1001-5000",  "location": "Dubai, UAE",            "linkedin_url": "https://linkedin.com/company/noon"},
    {"name": "Careem",      "domain": "careem.com",      "industry": "Super-app / Mobility",      "size_range": "1001-5000",  "location": "Dubai, UAE",            "linkedin_url": "https://linkedin.com/company/careem"},

    # ── Food delivery + Quick commerce (ME + India — 4) ──────────────────────
    {"name": "Talabat",     "domain": "talabat.com",     "industry": "Food Delivery",             "size_range": "1001-5000",  "location": "Dubai, UAE",            "linkedin_url": "https://linkedin.com/company/talabat"},
    {"name": "Swiggy",      "domain": "swiggy.com",      "industry": "Food + Quick Commerce",     "size_range": "5001-10000", "location": "Bangalore, India",      "linkedin_url": "https://linkedin.com/company/swiggy-in"},
    {"name": "Zomato",      "domain": "zomato.com",      "industry": "Food Delivery",             "size_range": "5001-10000", "location": "Gurgaon, India",        "linkedin_url": "https://linkedin.com/company/zomato"},
    {"name": "Zepto",       "domain": "zeptonow.com",    "industry": "Quick Commerce",            "size_range": "1001-5000",  "location": "Mumbai, India",         "linkedin_url": "https://linkedin.com/company/zepto"},

    # ── AI / Consumer tech (2) ────────────────────────────────────────────────
    {"name": "Mistral AI",  "domain": "mistral.ai",      "industry": "AI / Foundation Models",    "size_range": "201-500",    "location": "Paris, France",         "linkedin_url": "https://linkedin.com/company/mistral-ai"},
    {"name": "Uber",        "domain": "uber.com",        "industry": "Mobility / Consumer Tech",  "size_range": "10001+",     "location": "San Francisco, USA",    "linkedin_url": "https://linkedin.com/company/uber-com"},
]


async def main():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'), statement_cache_size=0)
    try:
        # Wipe existing companies (safe — earlier truncate cleared signals/opps too)
        deleted = await conn.fetchval("SELECT COUNT(*) FROM companies")
        await conn.execute("DELETE FROM companies")
        print(f"Wiped {deleted} existing company rows.")

        for c in COMPANIES:
            await conn.execute(
                """INSERT INTO companies (name, domain, industry, size_range, location, linkedin_url, enrichment_json)
                   VALUES ($1, $2, $3, $4, $5, $6, '{}'::jsonb)""",
                c['name'], c['domain'], c['industry'], c['size_range'], c['location'], c['linkedin_url'],
            )
        count = await conn.fetchval("SELECT COUNT(*) FROM companies")
        print(f"\nSeeded {count} target companies tailored to Swapneet's profile:\n")
        rows = await conn.fetch("SELECT name, location, industry FROM companies ORDER BY industry, name")
        for r in rows:
            print(f"  {r['name']:18} {r['location']:30} {r['industry']}")
    finally:
        await conn.close()


asyncio.run(main())
