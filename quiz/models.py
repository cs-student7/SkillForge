from django.conf import settings
from django.db import models


class Category(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    icon = models.CharField(max_length=8, default="📘")
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Question(models.Model):
    LEVELS = [(0, "Beginner"), (1, "Elementary"), (2, "Intermediate"), (3, "Advanced"), (4, "Professional")]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="questions")
    level = models.PositiveSmallIntegerField(choices=LEVELS, default=0)
    title = models.CharField(max_length=160)
    prompt = models.TextField()
    code = models.TextField(blank=True)
    options = models.JSONField(null=True, blank=True, help_text="Choices as a list. Leave empty for a typed answer.")
    answer = models.CharField(
        max_length=300,
        help_text="Choice number (e.g. 2) for multiple choice, or the text answer. Separate alternatives with |.",
    )
    hint = models.TextField()
    explanation = models.TextField(help_text="Plain-language explanation shown after a correct answer or a reveal.")
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category__order", "level", "id"]
        indexes = [models.Index(fields=["category", "level"])]

    def __str__(self):
        return self.title

    @property
    def points(self):
        return settings.DEVQUEST["POINTS_BY_LEVEL"][self.level]
