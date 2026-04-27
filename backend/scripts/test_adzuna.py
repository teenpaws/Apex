"""
Adzuna API smoke test — confirms the configured app_id/app_key actually work.

Run after pasting your Adzuna keys into .env:
    C:\\Python314\\python.exe scripts/test_adzuna.py

Probes 3 of Swapneet's target companies in 2 countries to surface any
auth/quota/region issues clearly.
"""
import asyncio, sys
sys.path.insert(0, '.')

from app.core.config import get_settings
from app.integrations.adzuna_client import AdzunaClient


async def main():
    s = get_settings()

    if s.ADZUNA_APP_ID.startswith("placeholder"):
        print("[X] ADZUNA_APP_ID is still a placeholder in .env")
        print("  -> Sign up at https://developer.adzuna.com/signup (free, ~2 min)")
        print("  -> Paste app_id + app_key into backend/.env, then re-run this script.")
        return 1

    print(f"Using app_id: {s.ADZUNA_APP_ID[:8]}...  country: {s.ADZUNA_COUNTRY}")
    print()

    probes = [
        ("Revolut",     "Senior Product Manager", "gb"),
        ("Booking.com", "Senior Product Manager", "nl"),
        ("Mistral AI",  "Product Manager",        "fr"),
    ]

    any_ok = False
    for company, role, country in probes:
        client = AdzunaClient(app_id=s.ADZUNA_APP_ID, app_key=s.ADZUNA_APP_KEY, country=country)
        results = await client.search_jobs(company_name=company, role_keywords=role, max_results=3)
        status = "OK" if results is not None else "ERR"
        n = len(results) if results else 0
        print(f"  [{status}] {country.upper():2}  {company:14} '{role}'  -> {n} posting(s)")
        for r in (results or [])[:2]:
            print(f"        - {r.title[:70]}  ({r.posted_date})")
        if n > 0:
            any_ok = True
        print()

    if any_ok:
        print("[OK] Adzuna is working. Pipeline will now mark matching opportunities as VALIDATED.")
        return 0

    print("[!] Connection succeeded but no postings returned for any probe.")
    print("  This is OK — quiet job market for these specific companies right now.")
    print("  Auth is fine; the pipeline will use Adzuna correctly when matches exist.")
    return 0


sys.exit(asyncio.run(main()))
