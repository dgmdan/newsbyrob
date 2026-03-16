from urllib.parse import urljoin, urlparse

from django.core.management.base import BaseCommand

from newsfeed.models import Article
from scripts.feed_config import SITES


class Command(BaseCommand):
    help = "Normalize Boundless article URLs so stored links are absolute."

    def handle(self, *args, **options):
        base_url = SITES["Boundless"][0]
        boundless_articles = (
            Article.objects.filter(site="Boundless")
            .exclude(link__isnull=True)
            .exclude(link__exact="")
        )

        updated = 0
        for article in boundless_articles:
            raw_link = article.link.strip()
            if not raw_link:
                continue

            parsed = urlparse(raw_link)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                continue

            new_link = urljoin(base_url, raw_link)
            if new_link == raw_link:
                continue

            article.link = new_link
            article.save(update_fields=["link"])
            updated += 1
            self.stdout.write(f"Updated {article.external_id}: {new_link}")

        self.stdout.write(self.style.SUCCESS(f"{updated} Boundless article(s) normalized."))
