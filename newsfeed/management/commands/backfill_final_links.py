import time
from urllib.parse import urlparse

from django.core.management.base import BaseCommand

from newsfeed.models import Article
from newsfeed.url_resolver import resolve_final_url
from scripts.support import logger

def is_gov_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url.strip())
    hostname = (parsed.hostname or "").lower()
    return hostname.endswith(".gov")


class Command(BaseCommand):
    help = "Rewrite stored article links to their final destination URLs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--delay",
            type=float,
            default=0.5,
            help="Seconds to sleep between requests while backfilling links.",
        )

    def handle(self, *args, **options):
        delay = options["delay"]
        queryset = Article.objects.exclude(link__isnull=True).exclude(link__exact="").order_by("id")
        updated = 0
        skipped = 0
        total = queryset.count()

        for article in queryset.iterator(chunk_size=50):
            if is_gov_url(article.link):
                self.stdout.write(f"Skipped {article.external_id} because it is already a .gov URL.")
                if delay > 0:
                    time.sleep(delay)
                continue
            resolved = resolve_final_url(article.link)
            if resolved.rate_limited:
                skipped += 1
                self.stdout.write(f"Skipped {article.external_id} due to rate limiting.")
            elif resolved.url and resolved.url != article.link:
                article.link = resolved.url
                article.save(update_fields=["link"])
                updated += 1
                self.stdout.write(f"Updated {article.external_id} -> {resolved.url}")
            if delay > 0:
                time.sleep(delay)

        if skipped:
            logger.warning(f"Backfill completed with {skipped} rate-limited article(s) skipped.")
        self.stdout.write(f"Processed {total} article(s); updated {updated}; skipped {skipped}.")
