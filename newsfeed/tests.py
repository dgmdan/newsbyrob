from datetime import datetime
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from newsfeed.models import Article, Tag
from scripts.feed_config import NewArticle


class NewsfeedViewsTestCase(TestCase):
    def setUp(self):
        self.tag = Tag.objects.create(name="Updates")
        self.other_tag = Tag.objects.create(name="Alerts")
        self.article = Article.objects.create(
            external_id="test-1",
            title="Test Article",
            link="https://example.com/1",
            description="<p>Summary</p>",
            pub_date=timezone.now(),
            pull_date=timezone.now(),
        )
        self.article.tags.add(self.tag)
        self.other_article = Article.objects.create(
            external_id="test-2",
            title="Second Article",
            link="https://example.com/2",
            description="<p>Other Summary</p>",
            pub_date=timezone.now(),
            pull_date=timezone.now(),
        )
        self.other_article.tags.add(self.other_tag)

    def test_homepage_shows_articles(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "newsfeed/article_list.html")
        self.assertContains(response, self.article.title)
        self.assertContains(response, self.other_article.title)

    def test_tag_filter_limits_results(self):
        response = self.client.get("/", {"tag": self.tag.slug})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.article.title)
        self.assertNotContains(response, self.other_article.title)


class CollectNewsCommandTestCase(TestCase):
    @patch("newsfeed.management.commands.collect_news.save_data")
    @patch("newsfeed.management.commands.collect_news.send_email_update", return_value=False)
    def test_collect_news_creates_articles(self, mock_send_email, mock_save_data):
        now = timezone.now()

        dummy_article = NewArticle(
            id="dummy-1",
            title="Dummy title",
            link="https://example.com/dummy",
            description="<p>Dummy description</p>",
            pub_date=now,
            pull_date=now,
            category="Dummy",
            source="Dummy Source",
        )

        class DummyModule:
            def ingest_xml(self, cat, source, NewArticleClass):
                return [dummy_article]

        with patch(
            "newsfeed.management.commands.collect_news.SITES",
            {"Dummy Site": ("https://example.com", DummyModule())},
        ), patch(
            "newsfeed.management.commands.collect_news.CATEGORIES",
            {"Dummy Site": ["Dummy"]},
        ):
            call_command("collect_news")

        self.assertTrue(Article.objects.filter(external_id="dummy-1").exists())
        created_article = Article.objects.get(external_id="dummy-1")
        self.assertEqual(created_article.title, "Dummy title")
        self.assertEqual(created_article.source, "Dummy Source")
        self.assertEqual(created_article.category, "Dummy")
        mock_send_email.assert_called_once()
        mock_save_data.assert_called_once()
