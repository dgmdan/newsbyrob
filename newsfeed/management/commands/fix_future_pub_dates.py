import datetime
from email.utils import parsedate_to_datetime

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.utils import timezone

from newsfeed.models import Article
from scripts.support import logger

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:148.0) Gecko/20100101 Firefox/148.0"
REQUEST_HEADERS = {"User-Agent": USER_AGENT}


class Command(BaseCommand):
    help = (
        "Fix articles whose publication date is in the future by re-fetching the source"
        " page and parsing the corrected date."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of future-dated articles to update in a single run.",
        )

    def handle(self, *args, **options):
        run_date = timezone.now()
        limit = options.get("limit")
        queryset = Article.objects.filter(pub_date__gt=run_date).order_by("pub_date")
        total_future = queryset.count()
        if not total_future:
            self.stdout.write("No future-dated articles found.")
            return
        if limit:
            queryset = queryset[:limit]
        articles = list(queryset)
        updated = 0
        for article in articles:
            scraped_date = self._scrape_article_date(article.link)
            final_date = scraped_date if scraped_date and scraped_date <= run_date else run_date
            if final_date != article.pub_date:
                article.pub_date = final_date
                article.save(update_fields=["pub_date"])
                updated += 1
                self.stdout.write(f"Updated {article.external_id} -> {final_date}")
        self.stdout.write(f"Fixed {updated} of {len(articles)} future-dated articles (out of {total_future} total).")

    def _scrape_article_date(self, url: str | None) -> datetime.datetime | None:
        if not url:
            return None
        try:
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
            response.raise_for_status()
        except Exception as exc:
            logger.warning(f"Unable to fetch {url} for date correction: {exc}")
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        parsed_dates = list(self._extract_candidate_dates(soup))
        if not parsed_dates:
            return None
        return min(parsed_dates)

    def _extract_candidate_dates(self, soup: BeautifulSoup):
        for meta in soup.find_all("meta"):
            for attr in ("name", "property", "itemprop", "http-equiv"):
                value = meta.get(attr)
                if not value:
                    continue
                lowered = value.lower()
                if "date" not in lowered and "time" not in lowered and "pub" not in lowered:
                    continue
                content = meta.get("content") or meta.get("value")
                parsed = self._parse_datetime(content)
                if parsed:
                    yield parsed

        for time_tag in soup.find_all("time"):
            for candidate in (time_tag.get("datetime"), time_tag.get_text(" ", strip=True)):
                parsed = self._parse_datetime(candidate)
                if parsed:
                    yield parsed

    def _parse_datetime(self, value: str | None) -> datetime.datetime | None:
        if not value:
            return None
        text = value.strip()
        if not text:
            return None
        iso_text = text.replace("Z", "+00:00") if text.endswith("Z") else text
        parsed = None
        try:
            parsed = datetime.datetime.fromisoformat(iso_text)
        except ValueError:
            try:
                parsed = parsedate_to_datetime(text)
            except (TypeError, ValueError):
                return None
        if parsed is None:
            return None
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_default_timezone())
        return parsed
