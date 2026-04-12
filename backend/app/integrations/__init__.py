"""
Apex external API integration clients.

All clients are async, use httpx, and share the SignalEvent dataclass as
their common output type.  Import from the individual modules for full
type information; this __init__ re-exports the primary surface for
convenience.
"""

from app.integrations.newsdata_client import NewsDataClient, SignalEvent
from app.integrations.gnews_client import GNewsClient
from app.integrations.sec_edgar_client import SECEdgarClient
from app.integrations.rss_client import RSSClient

__all__ = [
    "NewsDataClient",
    "GNewsClient",
    "SECEdgarClient",
    "RSSClient",
    "SignalEvent",
]
