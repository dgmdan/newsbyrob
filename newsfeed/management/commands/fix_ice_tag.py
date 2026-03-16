from django.core.management.base import BaseCommand
from django.db.models import Q

from newsfeed.models import Article, Tag
from scripts.feed_config import SITES


class Command(BaseCommand):
    help = "Add the ICE tag to every article pulled from ICE feeds."

    def handle(self, *args, **options):
        base_url, _ = SITES["ICE"]
        ice_tag, _ = Tag.objects.get_or_create(slug="ice", defaults={"name": "ICE"})

        targets = Article.objects.filter(
            Q(site__iexact="ICE")
            | Q(site__iexact=base_url)
            | Q(site__istartswith=base_url.rstrip("/"))
            | Q(site__icontains="ice.gov")
        ).distinct()

        to_tag = targets.exclude(tags=ice_tag)

        updated = 0
        for article in to_tag:
            article.tags.add(ice_tag)
            updated += 1
            self.stdout.write(f"Added ICE tag to {article.external_id}")

        self.stdout.write(self.style.SUCCESS(f"{updated} ICE article(s) tagged."))
