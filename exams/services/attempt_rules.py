from django.db.models import Sum, Q
from django.utils import timezone

from exams.models import TestRule, AttemptPolicy


def get_applicable_rule(test, user):
    branch = getattr(user, "branch", None)
    department = getattr(user, "department", None)
    role = getattr(user, "role", None)

    base = TestRule.objects.filter(test=test, is_active=True)

    # deadline filter (xohlasang yoqamiz)
    # base = base.filter(Q(deadline__isnull=True) | Q(deadline__gte=timezone.now()))

    candidates = [
        base.filter(branch=branch, department=department, role=role),
        base.filter(branch=branch, department=department, role__isnull=True),
        base.filter(branch=branch, department__isnull=True, role=role),
        base.filter(branch__isnull=True, department=department, role=role),
        base.filter(branch=branch, department__isnull=True, role__isnull=True),
        base.filter(branch__isnull=True, department=department, role__isnull=True),
        base.filter(branch__isnull=True, department__isnull=True, role=role),
        base.filter(branch__isnull=True, department__isnull=True, role__isnull=True),
    ]

    for qs in candidates:
        r = qs.order_by("-id").first()
        if r:
            return r
    return None


def get_extra_attempts(test, user) -> int:
    branch = getattr(user, "branch", None)
    department = getattr(user, "department", None)

    q = AttemptPolicy.objects.filter(test=test)

    total = 0

    if branch:
        total += q.filter(
            scope=AttemptPolicy.SCOPE_BRANCH,
            branch=branch
        ).aggregate(s=Sum("extra_attempts"))["s"] or 0

    if department:
        total += q.filter(
            scope=AttemptPolicy.SCOPE_DEPARTMENT,
            department=department
        ).aggregate(s=Sum("extra_attempts"))["s"] or 0

    total += q.filter(
        scope=AttemptPolicy.SCOPE_USER,
        user=user
    ).aggregate(s=Sum("extra_attempts"))["s"] or 0

    return int(total)


def get_attempts_allowed(test, user):
    """
    views_results.py import qilayotgan nom shu bo‘lsin.
    """
    rule = get_applicable_rule(test, user)
    base_limit = rule.attempts_limit if rule else 1
    extra = get_extra_attempts(test, user)
    return int(base_limit + extra), rule
