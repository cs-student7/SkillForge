import json

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import Category, Question

CFG = settings.DEVQUEST
RANKS = ["New Explorer", "Apprentice", "Learner", "Builder", "Developer",
         "Specialist", "Expert", "Master", "Elite", "Legend"]


def _wallet(request):
    """Progress for this browser, stored in the Django session. No login needed."""
    w = request.session.get("wallet")
    if w is None:
        w = {"points": 0, "tokens": CFG["START_TOKENS"], "solved": [], "hinted": [], "revealed": []}
        request.session["wallet"] = w
    return w


def _save(request, w):
    request.session["wallet"] = w  # assigning the key marks the session as changed


def _summary(w):
    level = min(10, w["points"] // 100 + 1)
    return {"points": w["points"], "tokens": w["tokens"], "level": level, "rank": RANKS[level - 1],
            "solved_count": len(w["solved"]), "reveal_cost": CFG["REVEAL_COST"]}


def _status(q, w):
    return {"solved": q.id in w["solved"], "hinted": q.id in w["hinted"], "revealed": q.id in w["revealed"]}


def _display_answer(q):
    first = q.answer.split("|")[0].strip()
    if q.options and first.isdigit():
        return q.options[int(first)]
    return first


def _json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return None


def _detail(q, w):
    data = {"id": q.id, "category": q.category.slug, "category_name": q.category.name,
            "level": q.level, "level_name": q.get_level_display(), "title": q.title,
            "prompt": q.prompt, "code": q.code, "options": q.options, "points": q.points,
            **_status(q, w)}
    if q.id in w["hinted"]:
        data["hint"] = q.hint
    if q.id in w["solved"] or q.id in w["revealed"]:
        data["answer"] = _display_answer(q)
        data["explanation"] = q.explanation
    return data


@ensure_csrf_cookie
def index(request):
    return render(request, "quiz/index.html")


@require_GET
def me(request):
    return JsonResponse(_summary(_wallet(request)))


@require_GET
def categories(request):
    results = [
        {"slug": c.slug, "name": c.name, "icon": c.icon, "description": c.description,
         "count": c.questions.filter(is_published=True).count()}
        for c in Category.objects.filter(is_active=True)
    ]
    return JsonResponse({"results": results})


@require_GET
def questions(request):
    w = _wallet(request)
    qs = Question.objects.filter(is_published=True).select_related("category")
    if request.GET.get("category"):
        qs = qs.filter(category__slug=request.GET["category"])
    if request.GET.get("level", "").isdigit():
        qs = qs.filter(level=int(request.GET["level"]))
    text = request.GET.get("q", "").strip()
    if text:
        qs = qs.filter(Q(title__icontains=text) | Q(prompt__icontains=text))
    page = Paginator(qs, CFG["PAGE_SIZE"]).get_page(request.GET.get("page"))
    results = [
        {"id": q.id, "category": q.category.slug, "category_name": q.category.name,
         "level": q.level, "level_name": q.get_level_display(), "title": q.title,
         "points": q.points, **_status(q, w)}
        for q in page
    ]
    return JsonResponse({"count": page.paginator.count, "page": page.number,
                         "pages": page.paginator.num_pages, "results": results})


@require_GET
def question_detail(request, qid):
    q = get_object_or_404(Question.objects.select_related("category"), pk=qid, is_published=True)
    return JsonResponse(_detail(q, _wallet(request)))


@require_POST
def hint(request, qid):
    """Free hint. Using it halves the points for this question."""
    q = get_object_or_404(Question, pk=qid, is_published=True)
    w = _wallet(request)
    if q.id not in w["hinted"]:
        w["hinted"].append(q.id)
        _save(request, w)
    return JsonResponse({"hint": q.hint})


@require_POST
def answer(request, qid):
    q = get_object_or_404(Question, pk=qid, is_published=True)
    w = _wallet(request)
    body = _json_body(request)
    if not isinstance(body, dict):
        return JsonResponse({"error": "Send your answer as JSON."}, status=400)
    if q.id in w["solved"] or q.id in w["revealed"]:
        return JsonResponse({"already_done": True, "answer": _display_answer(q), "explanation": q.explanation})
    given = str(body.get("answer", "")).strip().lower()
    if not given:
        return JsonResponse({"error": "Please choose or type an answer."}, status=400)
    accepted = [a.strip().lower() for a in q.answer.split("|")]
    if given not in accepted:
        return JsonResponse({"correct": False, "message": "Not quite. Try again, or open the hint."})
    gained = q.points // 2 if q.id in w["hinted"] else q.points
    w["points"] += gained
    w["tokens"] += gained  # tokens are earned at the same rate as points
    w["solved"].append(q.id)
    _save(request, w)
    return JsonResponse({"correct": True, "points_awarded": gained, **_summary(w)})


@require_POST
def reveal(request, qid):
    """Reveal the answer with tokens, but only after the hint has been opened."""
    q = get_object_or_404(Question, pk=qid, is_published=True)
    w = _wallet(request)
    if q.id not in w["solved"] and q.id not in w["revealed"]:
        if q.id not in w["hinted"]:
            return JsonResponse({"error": "Open the hint first. Answers unlock with tokens after a hint."}, status=400)
        if w["tokens"] < CFG["REVEAL_COST"]:
            return JsonResponse({"error": f"You need {CFG['REVEAL_COST']} tokens to reveal this answer."}, status=402)
        w["tokens"] -= CFG["REVEAL_COST"]
        w["revealed"].append(q.id)
        _save(request, w)
    return JsonResponse({"answer": _display_answer(q), "explanation": q.explanation, **_summary(w)})
