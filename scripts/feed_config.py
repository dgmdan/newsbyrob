import datetime
from dataclasses import dataclass

from . import uscis, travel, ice, g_news, aila, boundless


@dataclass
class NewArticle:
    author: str | None = None
    category: str | None = None
    country: str = ""
    creator: str | None = None
    description: str | None = None
    id: str | None = None
    identifier: str = ""
    keyword: str = ""
    link: str | None = None
    pub_date: datetime.datetime | str = ""
    pull_date: datetime.datetime | str = ""
    source: str | None = None
    threat_level: str = ""
    title: str | None = None


SITES = {
    "USCIS": ("https://www.uscis.gov", uscis),
    "DOS": ("https://travel.state.gov", travel),
    "Boundless": ("https://www.boundless.com", boundless),
    "Google": ("https://www.news.google.com", g_news),
    "AILA": ("https://www.aila.org", aila),
    "ICE": ("https://www.ice.gov", ice),
}

CATEGORIES = {
    "USCIS": ["Fact Sheets", "News Releases", "Stakeholder Messages", "Alerts", "Forms Updates"],
    "DOS": ["main_feed"],
    "Boundless": ["Boundless Blog"],
    "Google": ["US Immigration Changes", "USCIS Updates"],
    "AILA": ["AILA Daily News Update"],
    "ICE": [
        "Management and Administration",
        "Operational",
        "Profesional Responsibility",
        "National Security",
        "Partnership and Engagement",
        "Enforcement and Removal",
        "Transnational Gangs",
    ],
}
