import json
from pathlib import Path

from django.core.management.base import BaseCommand

from quiz.models import Category, Question


class Command(BaseCommand):
    help = "Load categories and questions from quiz/data/questions.json. Safe to run again."

    def handle(self, *args, **options):
        path = Path(__file__).resolve().parents[2] / "data" / "questions.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for c in data["categories"]:
            Category.objects.update_or_create(
                slug=c["slug"],
                defaults={k: c[k] for k in ("name", "icon", "description", "order")},
            )
        for q in data["questions"]:
            cat = Category.objects.get(slug=q["category"])
            defaults = {k: q.get(k, "") for k in ("prompt", "code", "hint", "explanation")}
            defaults.update(level=q["level"], options=q.get("options"), answer=q["answer"])
            Question.objects.update_or_create(category=cat, title=q["title"], defaults=defaults)
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {len(data['categories'])} categories and {len(data['questions'])} questions."))
