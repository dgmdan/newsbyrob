import datetime
import html
import re

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from newsfeed.models import Article, Tag
from scripts.feed_config import CATEGORIES, NewArticle, SITES
from scripts.support import logger, save_data, send_email_update, urlformat


TAG_SPLIT_RE = re.compile(r"[;,|]")


class Command(BaseCommand):
    help = "Scrape the configured immigration RSS feeds, store new articles, and email the report."

    def handle(self, *args, **options):
        newstories = []
        created_count = 0

        with transaction.atomic():
            for site_name, (base_url, module) in SITES.items():
                categories = CATEGORIES.get(site_name, [])
                for category in categories:
                    try:
                        feed_items = module.ingest_xml(category, base_url, NewArticle)
                    except Exception as exc:  # defensive guard
                        logger.warning(f"Feed {site_name}:{category} failed: {exc}")
                        continue
                    if not feed_items:
                        continue
                    for feed_item in feed_items:
                        article, created = self._save_article(feed_item, site_name, category)
                        if not article:
                            continue
                        if created:
                            created_count += 1
                            if article.link:
                                newstories.append((article.link, site_name, category, article.title))
        save_data(self._build_json_payload())

        if newstories:
            html = urlformat(newstories)
            email_sent = send_email_update(html)
            if email_sent:
                logger.warning(f"{created_count} new article(s) stored and emailed.")
                self.stdout.write(self.style.SUCCESS(f"Emailed {created_count} new article(s)."))
            else:
                logger.warning(f"{created_count} new article(s) stored but email delivery was skipped.")
                self.stdout.write(self.style.WARNING("Email delivery was skipped; configure secret/login.txt to enable it."))
        else:
            logger.info("No new articles found.")
            self.stdout.write("No new articles to report.")

    def _save_article(self, feed_item: NewArticle, site_name: str, category: str):
        external_id = feed_item.id or feed_item.link or feed_item.title
        if not external_id:
            logger.warning("Skipping article without an identifier.")
            return None, False

        title = feed_item.title or ""
        description = self._resolve_description(feed_item.description, title, feed_item.link)
        defaults = {
            "title": title,
            "link": feed_item.link or "",
            "description": description,
            "category": category or feed_item.category or "",
            "site": site_name,
            "source": feed_item.source or "",
            "creator": feed_item.creator or "",
            "author": feed_item.author or "",
            "country": feed_item.country or "",
            "identifier": feed_item.identifier or "",
            "keyword": feed_item.keyword or "",
            "threat_level": feed_item.threat_level or "",
            "pub_date": self._coerce_datetime(feed_item.pub_date),
            "pull_date": self._coerce_datetime(feed_item.pull_date),
        }

        article, created = Article.objects.update_or_create(
            external_id=external_id,
            defaults=defaults,
        )

        tag_names = {site_name, defaults["category"]}
        if feed_item.keyword:
            tag_names.update({part.strip() for part in TAG_SPLIT_RE.split(feed_item.keyword)})
        tag_names = {name.strip() for name in tag_names if name and name.strip()}

        tags = []
        for name in tag_names:
            slug = slugify(name)
            if not slug:
                continue
            tag, _ = Tag.objects.get_or_create(slug=slug, defaults={"name": name})
            tags.append(tag)
        article.tags.set(tags)

        return article, created

    def _resolve_description(self, description: str | None, title: str, link: str | None) -> str:
        description = description or ""
        if description and not self._description_repeats_title(description, title):
            return description
        if description and self._is_anchor_only_description(description, title):
            snippet = self._fetch_first_paragraph(link)
            if snippet:
                return f"<p>{html.escape(snippet)}</p>"

        snippet = self._fetch_first_paragraph(link)
        if snippet:
            return f"<p>{html.escape(snippet)}</p>"
        return description

    def _description_repeats_title(self, description: str, title: str) -> bool:
        if not title:
            return False
        text = BeautifulSoup(description, "html.parser").get_text(" ", strip=True)
        if not text:
            return True
        text_lower = text.lower()
        title_lower = title.lower()
        return text_lower.startswith(title_lower) and len(text_lower) <= len(title_lower) + 15

    def _is_anchor_only_description(self, description: str, title: str) -> bool:
        soup = BeautifulSoup(description, "html.parser")
        anchor = soup.find("a")
        if not anchor:
            return False
        anchor_text = anchor.get_text(" ", strip=True)
        if title and anchor_text.lower().strip() != title.lower().strip():
            return False

        for child in soup.contents:
            if isinstance(child, NavigableString):
                if child.replace("\xa0", "").strip():
                    return False
            elif isinstance(child, Tag):
                if child.name not in {"a", "font"}:
                    return False
        return True

    def _fetch_first_paragraph(self, link: str | None) -> str:
        if not link:
            return ""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            response = requests.get(link, headers=headers, timeout=5)
            response.raise_for_status()
        except Exception as exc:
            logger.debug(f"Unable to fetch article preview from {link}: {exc}")
            return ""

        soup = BeautifulSoup(response.text, "html.parser")
        for paragraph in soup.find_all("p"):
            text = paragraph.get_text(" ", strip=True)
            if len(text) > 30:
                return text
        return ""

    def _build_json_payload(self):
        jsondata = {}
        for article in Article.objects.all():
            pub_date = article.pub_date or article.pull_date or timezone.now()
            pull_date = article.pull_date or timezone.now()
            jsondata[article.external_id] = {
                "author": article.author,
                "category": article.category,
                "country": article.country,
                "creator": article.creator,
                "description": article.description,
                "identifier": article.identifier,
                "keyword": article.keyword,
                "link": article.link,
                "pub_date": pub_date,
                "pull_date": pull_date,
                "source": article.source,
                "threat_level": article.threat_level,
                "title": article.title,
            }
        return jsondata

    def _coerce_datetime(self, value):
        if isinstance(value, datetime.datetime):
            dt = value
        elif isinstance(value, str):
            try:
                dt = datetime.datetime.strptime(value, "%m-%d-%Y_%H-%M-%S")
            except ValueError:
                return None
        else:
            return None

        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_default_timezone())
        return dt
