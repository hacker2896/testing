from django.db.models import Max, Count
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied

from exams.models import Attempt, Test
from .serializers_results import ResultTestRowSerializer, AttemptListSerializer
from exams.services.attempt_rules import get_attempts_allowed

class CabinetResultsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        qs = Attempt.objects.filter(user=user).select_related("test")

        grouped = (
            qs.values("test_id", "test__title")
              .annotate(
                  last_attempt_at=Max("finished_at"),
                  best_percent=Max("percent"),
                  attempts_used=Count("id"),
              )
              .order_by("-last_attempt_at")
        )

        test_ids = [r["test_id"] for r in grouped]
        tests = {t.id: t for t in Test.objects.filter(id__in=test_ids)}

        # last_attempt_id map
        last_attempt_map = {}
        for r in grouped:
            t_id = r["test_id"]
            last = (
                Attempt.objects
                .filter(user=user, test_id=t_id)
                .order_by("-finished_at", "-started_at", "-id")
                .values("id")
                .first()
            )
            last_attempt_map[t_id] = last["id"] if last else None

        data = []
        for r in grouped:
            t_id = r["test_id"]
            t = tests.get(t_id)

            attempts_allowed, rule = get_attempts_allowed(t, user) if t else (1, None)

            data.append({
                "test_id": t_id,
                "test_title": r["test__title"],
                "last_attempt_id": last_attempt_map.get(t_id),
                "last_attempt_at": r["last_attempt_at"],
                "best_percent": str(r["best_percent"]) if r["best_percent"] is not None else None,
                "attempts_used": r["attempts_used"],
                "attempts_allowed": attempts_allowed,
                "deadline": getattr(rule, "deadline", None) if rule else None,
                "rule_is_active": bool(getattr(rule, "is_active", True)) if rule else True,
            })

        return Response(ResultTestRowSerializer(data, many=True).data)


class TestAttemptsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, test_id: int):
        user = request.user

        if not Test.objects.filter(id=test_id).exists():
            raise NotFound("Test topilmadi.")

        attempts = (
            Attempt.objects
            .filter(user=user, test_id=test_id)
            .order_by("-finished_at", "-started_at", "-id")
        )

        data = [{
            "id": a.id,
            "started_at": a.started_at,
            "finished_at": a.finished_at,
            "ends_at": a.ends_at,
            "status": a.status,
            "percent": str(a.percent),
            "score": str(a.score),
            "max_score": str(a.max_score),
        } for a in attempts]

        return Response(AttemptListSerializer(data, many=True).data)


class AttemptSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, attempt_id: int):
        user = request.user
        a = Attempt.objects.select_related("test").filter(id=attempt_id).first()
        if not a:
            raise NotFound("Attempt topilmadi.")
        if a.user_id != user.id:
            raise PermissionDenied("Ruxsat yo‘q.")

        return Response({
            "id": a.id,
            "test_id": a.test_id,
            "test_title": a.test.title,
            "status": a.status,
            "started_at": a.started_at,
            "finished_at": a.finished_at,
            "ends_at": a.ends_at,
            "score": str(a.score),
            "max_score": str(a.max_score),
            "percent": str(a.percent),
        })
