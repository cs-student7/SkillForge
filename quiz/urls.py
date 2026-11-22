from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/me/", views.me),
    path("api/categories/", views.categories),
    path("api/questions/", views.questions),
    path("api/questions/<int:qid>/", views.question_detail),
    path("api/questions/<int:qid>/hint/", views.hint),
    path("api/questions/<int:qid>/answer/", views.answer),
    path("api/questions/<int:qid>/reveal/", views.reveal),
]
