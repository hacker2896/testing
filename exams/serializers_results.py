from rest_framework import serializers

class ResultTestRowSerializer(serializers.Serializer):
    test_id = serializers.IntegerField()
    test_title = serializers.CharField()
    last_attempt_id = serializers.IntegerField(allow_null=True)
    last_attempt_at = serializers.DateTimeField(allow_null=True)
    best_percent = serializers.CharField(allow_null=True)  # Decimal -> string chiqadi
    attempts_used = serializers.IntegerField()
    attempts_allowed = serializers.IntegerField()
    deadline = serializers.DateTimeField(allow_null=True)
    rule_is_active = serializers.BooleanField()

class AttemptListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField(allow_null=True)
    ends_at = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField()
    percent = serializers.CharField()
    score = serializers.CharField()
    max_score = serializers.CharField()

class AttemptSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    test_id = serializers.IntegerField()
    test_title = serializers.CharField()
    started_at = serializers.DateTimeField(allow_null=True)
    ended_at = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField(allow_null=True)
    percent = serializers.FloatField(allow_null=True)
    correct = serializers.IntegerField(allow_null=True)
    total = serializers.IntegerField(allow_null=True)
    passed = serializers.BooleanField(allow_null=True)
