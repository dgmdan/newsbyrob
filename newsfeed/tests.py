from datetime import datetime
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from bs4 import BeautifulSoup
from newsfeed.management.commands.collect_news import normalize_external_id
from newsfeed.models import Article, Tag
from scripts.aila import get_articles
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
    @patch("newsfeed.management.commands.collect_news.send_email_update", return_value=False)
    def test_collect_news_creates_articles(self, mock_send_email):
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

    @patch("newsfeed.management.commands.collect_news.send_email_update", return_value=False)
    def test_collect_news_normalizes_long_external_id(self, mock_send_email):
        now = timezone.now()
        long_id = "x" * 1024

        dummy_article = NewArticle(
            id=long_id,
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

        expected_external_id = normalize_external_id(long_id)
        self.assertTrue(Article.objects.filter(external_id=expected_external_id).exists())
        created_article = Article.objects.get(external_id=expected_external_id)
        max_length = Article._meta.get_field("external_id").max_length
        self.assertLessEqual(len(created_article.external_id), max_length)
        self.assertEqual(created_article.external_id, expected_external_id)
        mock_send_email.assert_called_once()


class AilaScraperTestCase(TestCase):
    def test_description_prefers_article_text_over_section_label(self):
        html = """
        <div class="typography text rte">
            <h2><em>National</em></h2>
            <p>
                <em>NPR</em>
                <a href="https://www.npr.org/article">ICE's detention expansion meets resistance</a>
                <br/>
                By Jasmine Garsd
            </p>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        articles = get_articles(
            soup.find("div", class_="typography text rte"),
            "AILA Daily News Update",
            "https://www.aila.org",
            NewArticle,
        )
        self.assertEqual(len(articles), 1)
        article = articles[0]
        self.assertEqual(article.description, "ICE's detention expansion meets resistance")
        self.assertNotEqual(article.description.lower(), "national")
