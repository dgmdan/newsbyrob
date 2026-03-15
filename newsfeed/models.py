from django.db import models
from django.utils.text import slugify


class Tag(models.Model):
    name = models.CharField(max_length=128, unique=True)
    slug = models.SlugField(max_length=128, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Article(models.Model):
    external_id = models.CharField(max_length=512, unique=True)
    title = models.CharField(max_length=1024, blank=True)
    link = models.URLField(max_length=2048, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=256, blank=True)
    site = models.CharField(max_length=128, blank=True)
    source = models.CharField(max_length=512, blank=True)
    creator = models.CharField(max_length=256, blank=True)
    author = models.CharField(max_length=256, blank=True)
    country = models.CharField(max_length=256, blank=True)
    identifier = models.CharField(max_length=256, blank=True)
    keyword = models.CharField(max_length=512, blank=True)
    threat_level = models.CharField(max_length=128, blank=True)
    pub_date = models.DateTimeField(null=True, blank=True)
    pull_date = models.DateTimeField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="articles")

    class Meta:
        ordering = ["-pub_date", "-pull_date"]

    def __str__(self):
        return self.title
