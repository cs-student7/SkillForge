from django.contrib import admin

from .models import Category, Question


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "order", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "level", "is_published")
    list_filter = ("category", "level", "is_published")
    search_fields = ("title", "prompt")
