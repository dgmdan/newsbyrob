import datetime
import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from newsfeed.models import Article, Tag


TAG_SPLIT_RE = re.compile(r"[;,|]")
TIMESTAMP_FORMAT = "%m-%d-%Y_%H-%M-%S"


def _parse_datetime(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        candidate = datetime.datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError:
        return None

    if timezone.is_naive(candidate):
        return timezone.make_aware(candidate, timezone.get_default_timezone())
    return candidate


class Command(BaseCommand):
    help = "Load the existing JSON data dump into the local database (development only)."

    def handle(self, *args, **options):
        environment = getattr(settings, "ENVIRONMENT", "development").strip().lower()
        if environment == "production":
            raise CommandError("This import is only allowed in development environments.")

        data_file = Path(settings.BASE_DIR, "data", "im_updates.json")
        if not data_file.exists():
            raise CommandError("data/im_updates.json is missing; run the scraper first.")

        with data_file.open() as handle:
            raw = json.load(handle)

        created = 0
        updated = 0

        with transaction.atomic():
            for external_id, payload in raw.items():
                article_defaults = {
                    "title": payload.get("title") or "",
                    "link": payload.get("link") or "",
                    "description": payload.get("description") or "",
                    "category": payload.get("category") or "",
                    "site": payload.get("source") or "",
                    "source": payload.get("source") or "",
                    "creator": payload.get("creator") or "",
                    "author": payload.get("author") or "",
                    "country": payload.get("country") or "",
                    "identifier": payload.get("identifier") or "",
                    "keyword": payload.get("keyword") or "",
                    "threat_level": payload.get("threat_level") or "",
                    "pub_date": _parse_datetime(payload.get("pub_date")),
                    "pull_date": _parse_datetime(payload.get("pull_date")),
                }

                article, created_flag = Article.objects.update_or_create(
                    external_id=external_id,
                    defaults=article_defaults,
                )

                tag_names = {article_defaults["site"], article_defaults["category"]}
                keyword = article_defaults["keyword"]
                if keyword:
                    tag_names.update({part.strip() for part in TAG_SPLIT_RE.split(keyword)})
                tag_names = {name for name in tag_names if name}

                tags = []
                for name in tag_names:
                    slug = slugify(name)
                    if not slug:
                        continue
                    tag, _ = Tag.objects.get_or_create(slug=slug, defaults={"name": name})
                    tags.append(tag)
                article.tags.set(tags)

                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Imported {created} new article(s) and updated {updated} existing ones."
        ))
