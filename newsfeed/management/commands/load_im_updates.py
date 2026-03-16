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


def _truncate_for_field(field_name: str, raw_value: str | None) -> str:
    if not raw_value:
        return ""
    field = Article._meta.get_field(field_name)
    max_length = getattr(field, "max_length", None)
    text = str(raw_value)
    if max_length and len(text) > max_length:
        return text[:max_length]
    return text


class Command(BaseCommand):
    help = "Load the existing JSON data dump into the database; usable in any environment."

    def handle(self, *args, **options):
        data_file = Path(settings.BASE_DIR, "data", "im_updates.json")
        if not data_file.exists():
            raise CommandError("data/im_updates.json is missing; run the scraper first.")

        with transaction.atomic():
            raw = json.load(data_file.open())
            created = 0
            updated = 0

            for external_id, payload in raw.items():
                article_defaults = {
                    "title": _truncate_for_field("title", payload.get("title")),
                    "link": _truncate_for_field("link", payload.get("link")),
                    "description": payload.get("description") or "",
                    "category": _truncate_for_field("category", payload.get("category")),
                    "site": _truncate_for_field("site", payload.get("source")),
                    "source": _truncate_for_field("source", payload.get("source")),
                    "creator": _truncate_for_field("creator", payload.get("creator")),
                    "author": _truncate_for_field("author", payload.get("author")),
                    "country": _truncate_for_field("country", payload.get("country")),
                    "identifier": _truncate_for_field("identifier", payload.get("identifier")),
                    "keyword": _truncate_for_field("keyword", payload.get("keyword")),
                    "threat_level": _truncate_for_field("threat_level", payload.get("threat_level")),
                    "pub_date": _parse_datetime(payload.get("pub_date")),
                    "pull_date": _parse_datetime(payload.get("pull_date")),
                }

                article, created_flag = Article.objects.update_or_create(
                    external_id=_truncate_for_field("external_id", external_id),
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
