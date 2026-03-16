from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Rss201rev2Feed

from .models import Article


class TextXmlRssFeed(Rss201rev2Feed):
    content_type = "text/xml"


class LatestArticlesFeed(Feed):
    feed_type = TextXmlRssFeed
    title = "News by Rob aggregated immigration news"
    link = "/"
    description = "Latest immigration articles collected across government and advocacy sources."

    def items(self):
        return Article.objects.order_by("-pub_date", "-pull_date")[:50]

    def item_title(self, item):
        return item.title or "Immigration update"

    def item_description(self, item):
        return item.description or ""

    def item_link(self, item):
        return item.link or reverse("newsfeed:article_list")

    def item_pubdate(self, item):
        return item.pub_date or item.pull_date

    def item_author_name(self, item):
        return item.creator or item.author or "News by Rob"

    def item_categories(self, item):
        return [tag.name for tag in item.tags.all()]
