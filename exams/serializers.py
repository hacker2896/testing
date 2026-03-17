from rest_framework import serializers
from .models import TestRule, Test
from django.utils import timezone
from django.utils import timezone
from rest_framework import serializers
from .models import TestRule
from exams.services.attempts import used_attempts, allowed_attempts, remaining_attempts
from datetime import timedelta

from rest_framework import serializers
from .models import Test, TestRule  # nomlar siznikiga mos bo‘lsin

class PublicTestSerializer(serializers.ModelSerializer):
    # test ma'lumotlarini ichidan chiqaramiz
    id = serializers.IntegerField(source="test.id")
    title = serializers.CharField(source="test.title")
    code = serializers.CharField(source="test.code")
    pass_percent = serializers.IntegerField(source="test.pass_percent", allow_null=True)

    bank_questions = serializers.IntegerField(read_only=True)

    # ✅ MUHIM: source yozilmaydi!
    duration_minutes = serializers.IntegerField(allow_null=True)

    class Meta:
        model = TestRule
        fields = (
            "id",
            "title",
            "code",
            "duration_minutes",
            "pass_percent",
            "bank_questions",
        )


class AssignedCardSerializer(serializers.ModelSerializer):
    # Test dan keladiganlar
    test_id = serializers.IntegerField(source="test.id", read_only=True)
    code = serializers.CharField(source="test.code", read_only=True)
    title = serializers.CharField(source="test.title", read_only=True)
    description = serializers.CharField(source="test.description", read_only=True)
    duration_minutes = serializers.SerializerMethodField()
    questions_count = serializers.IntegerField(source="test.questions_count", read_only=True)
    pass_percent = serializers.IntegerField(source="test.pass_percent", read_only=True)

    # annotate() bilan view’dan berasiz
    bank_questions = serializers.IntegerField(read_only=True)

    # Rule dan keladiganlar (eski)
    attempts_limit = serializers.IntegerField(read_only=True)
    deadline = serializers.DateTimeField(read_only=True, allow_null=True)

    # ✅ Dynamic urinishlar
    attempts_allowed = serializers.SerializerMethodField()
    attempts_used = serializers.SerializerMethodField()
    attempts_remaining = serializers.SerializerMethodField()

    # UI uchun status
    status = serializers.SerializerMethodField()

    class Meta:
        model = TestRule
        fields = [
            "id",
            "test_id",
            "code", "title", "description",
            "duration_minutes", "questions_count", "bank_questions", "pass_percent",

            # old
            "attempts_limit", "deadline",

            # ✅ new dynamic
            "attempts_allowed", "attempts_used", "attempts_remaining",

            "is_active",
            "status",
        ]

    def _best_rule(self, obj: TestRule) -> TestRule:
        """
        assigned_tests view context'idan kelgan best_rule_by_test bo'lsa, shuni ishlatamiz.
        Aks holda obj'ning o'zini.
        """
        m = self.context.get("best_rule_by_test") or {}
        return m.get(obj.test_id, obj)

    def get_attempts_allowed(self, obj: TestRule):
        u = self.context["request"].user
        rule = self._best_rule(obj)
        return allowed_attempts(rule, u, obj.test)  # None => Cheksiz

    def get_attempts_used(self, obj: TestRule) -> int:
        u = self.context["request"].user
        return used_attempts(u, obj.test)

    def get_attempts_remaining(self, obj: TestRule):
        u = self.context["request"].user
        rule = self._best_rule(obj)
        return remaining_attempts(rule, u, obj.test)  # None => Cheksiz

    def get_status(self, obj: TestRule) -> str:
        """
        active  - qoida faol va deadline o'tmagan (yoki deadline yo'q)
        off     - qoida nofaol yoki deadline o'tgan
        """
        if not obj.is_active:
            return "off"

        if obj.deadline:
            now = timezone.now()
            try:
                if obj.deadline <= now:
                    return "off"
            except TypeError:
                if timezone.make_aware(obj.deadline) <= now:
                    return "off"

        return "active"
    def get_duration_minutes(self, obj):
        # Agar rule’da duration bo‘lsa — o‘sha
        if obj.duration_minutes:
            return obj.duration_minutes

        # Aks holda test default duration
        return obj.test.duration_minutes
