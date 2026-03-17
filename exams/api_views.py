from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Test, TestRule
from .serializers import PublicTestSerializer, AssignedCardSerializer
from .services.attempts import used_attempts, allowed_attempts, remaining_attempts



@api_view(["GET"])
@permission_classes([AllowAny])
def public_tests(request):
    qs = (
        TestRule.objects
        .select_related("test")
        .filter(is_active=True, test__is_active=True)
        .annotate(bank_questions=Count("test__questions", distinct=True))
        .order_by("-id")
    )
    return Response(PublicTestSerializer(qs, many=True).data)

from django.db.models import Q, Count
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import TestRule
from .serializers import AssignedCardSerializer


def _pick_best_rule(rules):
    """
    Bitta testga bir nechta rule mos kelsa:
    - branch mos bo‘lsa ustun
    - department mos bo‘lsa ustun
    - role mos bo‘lsa ustun
    - keyin eng oxirgi yaratilgani (id katta) ustun
    """
    def score(r: TestRule):
        return (
            1 if r.branch_id is not None else 0,
            1 if r.department_id is not None else 0,
            1 if r.role is not None else 0,
            r.id,
        )
    return max(rules, key=score)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def assigned_tests(request):
    u = request.user
    now = timezone.now()

    branch_id = getattr(u, "branch_id", None)
    dept_id = getattr(u, "department_id", None)
    role = getattr(u, "role", None)

    base = (
        TestRule.objects
        .select_related("test")
        .filter(is_active=True, test__is_active=True)
        .filter(Q(deadline__isnull=True) | Q(deadline__gte=now))
        .filter(Q(branch__isnull=True) | Q(branch_id=branch_id))
        .filter(Q(department__isnull=True) | Q(department_id=dept_id))
        .filter(Q(role__isnull=True) | Q(role=role))
    )

    # 1) Har test uchun eng mos bitta rule tanlaymiz
    by_test = {}
    for r in base.only("id", "test_id", "branch_id", "department_id", "role", "attempts_limit"):
        by_test.setdefault(r.test_id, []).append(r)

    chosen_ids = []
    best_rule_by_test = {}
    for test_id, rules in by_test.items():
        best = _pick_best_rule(rules)
        chosen_ids.append(best.id)
        best_rule_by_test[test_id] = best

    # 2) Faqat tanlangan rule larni olamiz
    qs = (
        TestRule.objects
        .select_related("test")
        .filter(id__in=chosen_ids)   # ✅ SHU
        .annotate(bank_questions=Count("test__questions", distinct=True))
        .order_by("-id")
    )

    ser = AssignedCardSerializer(qs, many=True, context={
        "request": request,
        "best_rule_by_test": best_rule_by_test,
    })
    return Response(ser.data)