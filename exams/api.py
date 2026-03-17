from django.db import transaction
from django.utils import timezone
from django.db.models import Q
import random
import re
from decimal import Decimal, InvalidOperation
from datetime import timedelta

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from exams.models import AttemptPolicy
from .models import Test, Attempt, AttemptAnswer, Question, TestRule
from django.db import IntegrityError


# ----------------------------
# Helpers
# ----------------------------

def _max_score(test: Test):
    return sum(q.points for q in test.questions.all())


def _parse_ids_any(v):
    """
    choice_ids ni universal parse qiladi:
      - [1,3]
      - "1;3" / "1,3" / "1 3" / "1|3"
      - 5
    """
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        out = []
        for x in v:
            try:
                out.append(int(x))
            except Exception:
                pass
        return [x for x in out if x > 0]

    if isinstance(v, (int, float)):
        try:
            i = int(v)
            return [i] if i > 0 else []
        except Exception:
            return []

    s = str(v).strip()
    if not s:
        return []
    parts = re.split(r"[^\d]+", s)
    out = []
    for p in parts:
        if p.isdigit():
            out.append(int(p))
    return [x for x in out if x > 0]


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _to_decimal(v):
    if v is None or str(v).strip() == "":
        return None
    try:
        return Decimal(str(v).strip())
    except (InvalidOperation, ValueError):
        return None




def _build_submit_payload(attempt: Attempt):
    """Attemptdan natija payloadini bir xil formatda chiqarish."""
    correct = (
        attempt.answers
        .exclude(question__question_type="essay")
        .filter(is_correct=True)
        .count()
    )
    total = len(attempt.question_order or []) or attempt.answers.count()
    passed = float(attempt.percent or 0) >= float(attempt.test.pass_percent or 0)

    return {
        "finished": True,
        "status": attempt.status,
        "score": str(attempt.score or "0"),
        "max_score": str(attempt.max_score or "0"),
        "percent": str(attempt.percent or "0"),
        "passed": passed,
        "correct": correct,
        "total": total,
    }


def _finalize_attempt(attempt: Attempt):
    """
    IN_PROGRESS yoki EXPIRED attemptni yakunlab, score/percent/status yozadi.
    Essay bo'lsa PENDING_REVIEW, aks holda FINISHED.
    """
    score = Decimal("0")
    correct = 0
    has_essay = False

    answers = attempt.answers.select_related("question")
    for a in answers:
        score += (a.earned_points or Decimal("0"))
        if a.question.question_type == "essay":
            has_essay = True
        if a.question.question_type != "essay" and a.is_correct:
            correct += 1

    max_score = attempt.max_score or _max_score(attempt.test)
    percent = (score / max_score * 100) if max_score else Decimal("0")

    attempt.score = score
    attempt.max_score = max_score
    attempt.percent = percent
    attempt.finished_at = attempt.finished_at or timezone.now()

    if has_essay:
        attempt.status = Attempt.PENDING_REVIEW
    else:
        attempt.status = Attempt.FINISHED

    attempt.save()


# ----------------------------
# API: Assigned tests (Dashboard)
# ----------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def assigned_tests(request):
    u = request.user

    rules = (
        TestRule.objects
        .select_related("test")
        .filter(is_active=True, test__is_active=True)
        .filter(Q(branch__isnull=True) | Q(branch=u.branch))
        .filter(Q(department__isnull=True) | Q(department=u.department))
        .filter(Q(role__isnull=True) | Q(role=u.role))
    )

    best_by_test = {}
    for r in rules:
        score = int(bool(r.branch)) + int(bool(r.department)) + int(bool(r.role))
        prev = best_by_test.get(r.test_id)
        if (prev is None) or (score > prev["score"]):
            best_by_test[r.test_id] = {"rule": r, "score": score}

    test_ids = list(best_by_test.keys())
    inprog = (
        Attempt.objects
        .filter(user=u, test_id__in=test_ids, status=Attempt.IN_PROGRESS)
        .order_by("-started_at")
    )
    inprog_map = {}
    for a in inprog:
        if a.test_id not in inprog_map:
            inprog_map[a.test_id] = a.id

    data = []
    for test_id, item in best_by_test.items():
        rule = item["rule"]
        t = rule.test
        data.append({
            "test": {
                "id": t.id,
                "title": t.title,
                "code": t.code,
                "description": getattr(t, "description", "") or "",
                "duration_minutes": getattr(rule, "duration_minutes", None) or getattr(t, "duration_minutes", None),
                "pass_percent": getattr(t, "pass_percent", None),
                "questions_count": getattr(t, "questions_count", None),
            },
            "deadline": rule.deadline,
            "attempts_limit": rule.attempts_limit,
            "in_progress_attempt_id": inprog_map.get(test_id),
        })

    data.sort(key=lambda x: x["test"]["title"].lower())
    return Response(data)


# ----------------------------
# API: Start attempt
# ----------------------------

def calc_extra_attempts(user, test) -> int:
    branch_id = getattr(user, "branch_id", None)
    dept_id = getattr(user, "department_id", None)

    extra = 0
    if branch_id:
        extra += (AttemptPolicy.objects
                  .filter(test=test, scope="branch", branch_id=branch_id)
                  .values_list("extra_attempts", flat=True)
                  .first() or 0)

    if dept_id:
        extra += (AttemptPolicy.objects
                  .filter(test=test, scope="department", department_id=dept_id)
                  .values_list("extra_attempts", flat=True)
                  .first() or 0)

    extra += (AttemptPolicy.objects
              .filter(test=test, scope="user", user_id=user.id)
              .values_list("extra_attempts", flat=True)
              .first() or 0)

    return extra


def _pick_best_rule(user, test: Test):
    rules = (
        TestRule.objects
        .filter(test=test, is_active=True)
        .filter(Q(branch__isnull=True) | Q(branch=user.branch))
        .filter(Q(department__isnull=True) | Q(department=user.department))
        .filter(Q(role__isnull=True) | Q(role=user.role))
    )

    best = None
    best_score = -1
    for r in rules:
        score = int(bool(r.branch)) + int(bool(r.department)) + int(bool(r.role))
        if score > best_score:
            best = r
            best_score = score
    return best


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def start_attempt(request, code: str):
    u = request.user

    # ✅ 0) Shu userda running attempt bormi? BOR bo'lsa qaytaramiz (idempotent)
    running = (
        Attempt.objects
        .select_related("test")
        .filter(user=u, status=Attempt.IN_PROGRESS)
        .order_by("-started_at")
        .first()
    )
    if running:
        # agar aynan shu test bo'lsa — davom ettiramiz
        if running.test and running.test.code == code:
            if not running.ends_at:
                dur = running.duration_minutes or running.test.duration_minutes or 0
                if dur:
                    running.duration_minutes = dur
                    running.ends_at = running.started_at + timedelta(minutes=int(dur))
                    running.save(update_fields=["duration_minutes", "ends_at"])
            return Response({
                "attempt_id": running.id,
                "started_at": running.started_at,
                "ends_at": running.ends_at,
                "duration_minutes": running.duration_minutes,
                "detail": "Davom etayotgan test qaytarildi.",
            })

        # boshqa testni start qilmoqchi bo'lsa — 409
        return Response({
            "detail": f"Yakunlanmagan test bor: {running.test.title}. Avval uni yakunlang.",
            "running_attempt_id": running.id,
            "running_test_code": running.test.code,
            "running_test_title": running.test.title,
        }, status=status.HTTP_409_CONFLICT)

    # 1) Testni topamiz
    test = Test.objects.filter(code=code, is_active=True).first()
    if not test:
        return Response({"detail": "Test topilmadi."}, status=status.HTTP_404_NOT_FOUND)

    # 2) Rule
    rule = _pick_best_rule(u, test)
    if not rule:
        return Response({"detail": "Sizga bu test ruxsat etilmagan."}, status=status.HTTP_403_FORBIDDEN)

    if rule.deadline and timezone.now() > rule.deadline:
        return Response({"detail": "Deadline o'tib ketgan."}, status=status.HTTP_400_BAD_REQUEST)

    # 3) Urinish limiti
    used = (Attempt.objects
            .filter(user=u, test=test)
            .exclude(status=Attempt.IN_PROGRESS)
            .count())

    base_limit = rule.attempts_limit
    extra = calc_extra_attempts(u, test)
    allowed = (base_limit or 0) + extra

    if base_limit is not None and used >= allowed:
        return Response({"detail": "Urinish limiti tugagan."}, status=status.HTTP_400_BAD_REQUEST)

    # 4) Savollar tanlash
    all_ids = list(test.questions.values_list("id", flat=True))
    if not all_ids:
        return Response({"detail": "Bu test uchun savollar yo‘q."}, status=status.HTTP_400_BAD_REQUEST)

    total = len(all_ids)
    n = int(getattr(test, "questions_count", total) or total)
    selected = all_ids if total <= n else random.sample(all_ids, n)
    random.shuffle(selected)

    max_score = sum(q.points for q in Question.objects.filter(id__in=selected))

    duration = rule.duration_minutes or test.duration_minutes or 0
    started = timezone.now()
    ends_at = started + timedelta(minutes=int(duration)) if duration else None

    # ✅ 5) Attempt create: constraint urilishi mumkin (double request bo'lsa) — tutib, runningni qaytaramiz
    try:
        attempt = Attempt.objects.create(
            user=u,
            test=test,
            status=Attempt.IN_PROGRESS,
            started_at=started,
            duration_minutes=duration if duration else None,
            ends_at=ends_at,
            max_score=max_score,
            question_order=selected,
        )
    except IntegrityError:
        # boshqa parallel request IN_PROGRESS yaratib bo'ldi — endi uni qaytaramiz
        running2 = (
            Attempt.objects
            .select_related("test")
            .filter(user=u, status=Attempt.IN_PROGRESS)
            .order_by("-started_at")
            .first()
        )
        if not running2:
            raise
        return Response({
            "attempt_id": running2.id,
            "started_at": running2.started_at,
            "ends_at": running2.ends_at,
            "duration_minutes": running2.duration_minutes,
            "detail": "Davom etayotgan test qaytarildi.",
        })

    return Response({
        "attempt_id": attempt.id,
        "started_at": attempt.started_at,
        "ends_at": attempt.ends_at,
        "duration_minutes": attempt.duration_minutes,
    })
# ----------------------------
# API: Attempt detail
# ----------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def attempt_detail(request, attempt_id: int):
    attempt = (
        Attempt.objects
        .select_related("test")
        .filter(id=attempt_id, user=request.user)
        .first()
    )
    if not attempt:
        return Response({"detail": "Attempt topilmadi."}, status=404)

    dur = attempt.duration_minutes or attempt.test.duration_minutes or 0

    # ends_at bo'lmasa 1 marta yozib qo'yamiz
    if attempt.status == Attempt.IN_PROGRESS and dur and not attempt.ends_at:
        attempt.ends_at = attempt.started_at + timedelta(minutes=int(dur))
        attempt.save(update_fields=["ends_at"])

    # vaqt tugasa EXPIRED qilib qo'yamiz (ammo score/percentni submit hisoblaydi)
    if attempt.status == Attempt.IN_PROGRESS and attempt.is_time_over():
        attempt.status = Attempt.EXPIRED
        attempt.finished_at = timezone.now()
        attempt.save(update_fields=["status", "finished_at"])

    ordered_ids = attempt.question_order or []

    # answers_map
    answers_map = {}
    for a in attempt.answers.select_related("question", "choice"):
        qt = a.question.question_type
        if qt in ("single", "true_false"):
            if a.choice_id:
                answers_map[str(a.question_id)] = a.choice_id
            elif a.selected_choice_ids:
                answers_map[str(a.question_id)] = int(a.selected_choice_ids[0])
        elif qt == "multiple":
            answers_map[str(a.question_id)] = list(a.selected_choice_ids or [])
        elif qt in ("short", "essay"):
            answers_map[str(a.question_id)] = a.text_answer or ""
        elif qt == "numeric":
            answers_map[str(a.question_id)] = str(a.numeric_answer) if a.numeric_answer is not None else ""

    payload_questions = []
    if ordered_ids:
        qs = (
            Question.objects
            .filter(id__in=ordered_ids, test=attempt.test)
            .prefetch_related("choices")
        )
        q_map = {q.id: q for q in qs}
        ordered_questions = [q_map[qid] for qid in ordered_ids if qid in q_map]

        for q in ordered_questions:
            item = {"id": q.id, "text": q.text, "question_type": q.question_type}
            if q.question_type in ("single", "multiple", "true_false"):
                item["choices"] = [{"id": c.id, "text": c.text} for c in q.choices.all()]
            payload_questions.append(item)

    # result (agar submitdan keyin hisoblangan bo'lsa)
    result = None
    if attempt.status != Attempt.IN_PROGRESS and attempt.percent is not None:
        result = _build_submit_payload(attempt)

    return Response({
        "id": attempt.id,
        "started_at": attempt.started_at,
        "ends_at": attempt.ends_at,
        "duration_minutes": dur or None,
        "test": {
            "title": attempt.test.title,
            "duration_minutes": dur or None,
            "pass_percent": attempt.test.pass_percent,
            "questions_count": attempt.test.questions_count,
        },
        "questions": payload_questions,
        "answers": answers_map,
        "status": attempt.status,
        "result": result,
    })


# ----------------------------
# API: Save answer
# ----------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def save_answer(request, attempt_id: int):
    attempt = (
        Attempt.objects
        .select_related("test")
        .filter(id=attempt_id, user=request.user)
        .first()
    )
    if not attempt:
        return Response({"detail": "Attempt topilmadi."}, status=404)

    if attempt.status != Attempt.IN_PROGRESS:
        return Response({"detail": "Attempt yakunlangan."}, status=400)

    if attempt.is_time_over():
        attempt.status = Attempt.EXPIRED
        attempt.finished_at = timezone.now()
        attempt.save(update_fields=["status", "finished_at"])
        return Response({"detail": "Vaqt tugagan."}, status=400)

    data = request.data.copy()

    try:
        qid = int(data.get("question_id"))
    except Exception:
        return Response({"detail": "question_id noto‘g‘ri."}, status=400)

    q = (
        Question.objects
        .filter(id=qid, test=attempt.test)
        .prefetch_related("choices")
        .first()
    )
    if not q:
        return Response({"detail": "Savol topilmadi."}, status=404)

    qtype = q.question_type

    # value -> legacy mapping
    if "value" in data and (
        "choice_id" not in data and "choice_ids" not in data
        and "text_answer" not in data and "numeric_answer" not in data
    ):
        v = data.get("value")
        if qtype in ("single", "true_false"):
            data["choice_id"] = v
        elif qtype == "multiple":
            data["choice_ids"] = v
        elif qtype == "numeric":
            data["numeric_answer"] = v
        else:
            data["text_answer"] = v

    # ---- choice questions
    if qtype in ("single", "true_false", "multiple"):
        raw = data.get("choice_ids", None)
        if raw is None:
            raw = data.get("choice_id", None)

        choice_ids = _parse_ids_any(raw)

        if qtype in ("single", "true_false") and len(choice_ids) != 1:
            return Response({"detail": "Bu turda 1 ta variant tanlanadi."}, status=400)

        if qtype == "multiple" and len(choice_ids) < 1:
            return Response({"detail": "Kamida 1 ta variant tanlang."}, status=400)

        allowed_ids = set(q.choices.values_list("id", flat=True))
        if any(cid not in allowed_ids for cid in choice_ids):
            return Response({"detail": "Variant topilmadi."}, status=404)

        correct_ids = set(q.choices.filter(is_correct=True).values_list("id", flat=True))
        selected_set = set(choice_ids)

        if qtype in ("single", "true_false"):
            is_correct = choice_ids[0] in correct_ids
        else:
            is_correct = (selected_set == correct_ids) and (len(correct_ids) > 0)

        earned = q.points if is_correct else Decimal("0")

        legacy_choice = None
        if qtype in ("single", "true_false"):
            legacy_choice = q.choices.filter(id=choice_ids[0]).first()

        ans, _ = AttemptAnswer.objects.update_or_create(
            attempt=attempt,
            question=q,
            defaults={
                "choice": legacy_choice,
                "selected_choice_ids": choice_ids if qtype == "multiple" else [],
                "text_answer": None,
                "numeric_answer": None,
                "is_correct": bool(is_correct),
                "earned_points": earned,
            }
        )

        return Response({
            "saved": True,
            "question_id": q.id,
            "type": qtype,
            "is_correct": bool(is_correct),
            "earned_points": str(ans.earned_points),
        })

    # ---- short
    if qtype == "short":
        text_answer = data.get("text_answer", "")
        if text_answer is None or str(text_answer).strip() == "":
            return Response({"detail": "text_answer kerak."}, status=400)

        correct = _norm_text(getattr(q, "correct_answer", "") or "")
        given = _norm_text(str(text_answer))
        is_correct = bool(correct) and (given == correct)
        earned = q.points if is_correct else Decimal("0")

        ans, _ = AttemptAnswer.objects.update_or_create(
            attempt=attempt,
            question=q,
            defaults={
                "choice": None,
                "selected_choice_ids": [],
                "text_answer": str(text_answer).strip(),
                "numeric_answer": None,
                "is_correct": bool(is_correct),
                "earned_points": earned,
            }
        )

        return Response({
            "saved": True,
            "question_id": q.id,
            "type": qtype,
            "is_correct": bool(is_correct),
            "earned_points": str(ans.earned_points),
        })

    # ---- numeric
    if qtype == "numeric":
        given = _to_decimal(data.get("numeric_answer", None))
        correct = _to_decimal(getattr(q, "correct_answer", None))

        if given is None:
            return Response({"detail": "numeric_answer noto‘g‘ri."}, status=400)
        if correct is None:
            return Response({"detail": "Savol uchun correct_answer (son) yo‘q."}, status=400)

        eps = Decimal("0.0001")
        is_correct = abs(given - correct) <= eps
        earned = q.points if is_correct else Decimal("0")

        ans, _ = AttemptAnswer.objects.update_or_create(
            attempt=attempt,
            question=q,
            defaults={
                "choice": None,
                "selected_choice_ids": [],
                "text_answer": None,
                "numeric_answer": given,
                "is_correct": bool(is_correct),
                "earned_points": earned,
            }
        )

        return Response({
            "saved": True,
            "question_id": q.id,
            "type": qtype,
            "is_correct": bool(is_correct),
            "earned_points": str(ans.earned_points),
        })

    # ---- essay
    if qtype == "essay":
        text_answer = data.get("text_answer", "")
        if text_answer is None or str(text_answer).strip() == "":
            return Response({"detail": "text_answer kerak."}, status=400)

        ans, _ = AttemptAnswer.objects.update_or_create(
            attempt=attempt,
            question=q,
            defaults={
                "choice": None,
                "selected_choice_ids": [],
                "text_answer": str(text_answer).strip(),
                "numeric_answer": None,
                "is_correct": False,
                "earned_points": Decimal("0"),
            }
        )

        return Response({
            "saved": True,
            "question_id": q.id,
            "type": qtype,
            "is_correct": None,
            "earned_points": str(ans.earned_points),
        })

    return Response({"detail": "Bu savol turi qo‘llab-quvvatlanmaydi."}, status=400)


# ----------------------------
# API: Submit attempt (IDEMPOTENT + works for EXPIRED)
# ----------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def submit_attempt(request, attempt_id: int):
    attempt = (
        Attempt.objects
        .select_related("test")
        .filter(id=attempt_id, user=request.user)
        .first()
    )
    if not attempt:
        return Response({"detail": "Attempt topilmadi."}, status=404)

    # ✅ allaqachon yakunlangan bo'lsa natijani qaytar
    if attempt.status not in (Attempt.IN_PROGRESS, Attempt.EXPIRED):
        return Response(_build_submit_payload(attempt))

    # ✅ IN_PROGRESS bo'lsa va vaqt tugagan bo'lsa EXPIRED qilib qo'yamiz
    if attempt.status == Attempt.IN_PROGRESS and attempt.is_time_over():
        attempt.status = Attempt.EXPIRED
        attempt.finished_at = timezone.now()
        attempt.save(update_fields=["status", "finished_at"])

    # ✅ hisoblab yakunlaymiz (IN_PROGRESS ham, EXPIRED ham)
    _finalize_attempt(attempt)

    return Response(_build_submit_payload(attempt))


# ----------------------------
# API: My results
# ----------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_results(request):
    attempts = (
        Attempt.objects
        .filter(user=request.user)
        .exclude(status=Attempt.IN_PROGRESS)
        .select_related("test")
        .order_by("-finished_at")
    )

    data = []
    for a in attempts:
        data.append({
            "id": a.id,
            "test_title": a.test.title,
            "score": str(a.score),
            "max_score": str(a.max_score),
            "percent": str(a.percent),
            "status": a.status,
            "finished_at": a.finished_at,
        })

    return Response(data)


# ----------------------------
# API: My in-progress attempt
# ----------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_in_progress_attempt(request):
    a = (
        Attempt.objects
        .filter(user=request.user, status=Attempt.IN_PROGRESS)
        .select_related("test")
        .order_by("-started_at")
        .first()
    )
    if not a:
        return Response({"has_in_progress": False})

    return Response({
        "has_in_progress": True,
        "attempt_id": a.id,
        "test_id": a.test_id,
        "test_title": a.test.title,
        "code": a.test.code,
        "started_at": a.started_at,
        "ends_at": a.ends_at,
    })
