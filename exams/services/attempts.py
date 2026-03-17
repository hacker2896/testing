from exams.models import Attempt, AttemptPolicy

# exams/services/attempts.py
from exams.models import Attempt

def used_attempts(user, test) -> int:
    return (
        Attempt.objects
        .filter(user=user, test=test)
        .exclude(status=Attempt.IN_PROGRESS)
        .count()
    )

def allowed_attempts(best_rule, user, test) -> int | None:
    if best_rule.attempts_limit is None:
        return None  # cheksiz
    return best_rule.attempts_limit + extra_attempts(user, test)

def remaining_attempts(best_rule, user, test) -> int | None:
    allowed = allowed_attempts(best_rule, user, test)
    if allowed is None:
        return None
    rem = allowed - used_attempts(user, test)
    return max(rem, 0)


def extra_attempts(user, test) -> int:
    extra = 0
    extra += (AttemptPolicy.objects
              .filter(test=test, scope=AttemptPolicy.SCOPE_USER, user=user)
              .values_list("extra_attempts", flat=True).first() or 0)

    branch_id = getattr(user, "branch_id", None)
    if branch_id:
        extra += (AttemptPolicy.objects
                  .filter(test=test, scope=AttemptPolicy.SCOPE_BRANCH, branch_id=branch_id)
                  .values_list("extra_attempts", flat=True).first() or 0)

    dept_id = getattr(user, "department_id", None)
    if dept_id:
        extra += (AttemptPolicy.objects
                  .filter(test=test, scope=AttemptPolicy.SCOPE_DEPARTMENT, department_id=dept_id)
                  .values_list("extra_attempts", flat=True).first() or 0)

    return extra
