from rest_framework import serializers
from .models import Question, Test
from django.contrib.auth import get_user_model

class TeacherTestSerializer(serializers.ModelSerializer):
    questions_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Test
        fields = ["id", "title", "code", "questions_count", "pass_percent", "is_active"]

# ⚠️ Choice modelingiz nomi boshqacha bo‘lsa moslang:
from .models import Choice
class ChoiceWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Choice
        fields = ["id", "text", "is_correct"]

class QuestionTeacherListSerializer(serializers.ModelSerializer):
    test_id = serializers.IntegerField(source="test.id", read_only=True)
    test_title = serializers.CharField(source="test.title", read_only=True)
    choices_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Question
        fields = ["id", "test_id", "test_title", "text", "question_type", "points", "choices_count"]


class QuestionTeacherDetailSerializer(serializers.ModelSerializer):
    test_id = serializers.IntegerField(source="test.id", read_only=True)
    test_title = serializers.CharField(source="test.title", read_only=True)
    choices = ChoiceWriteSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ["id", "test_id", "test_title", "text", "question_type", "points", "correct_answer", "choices"]


class QuestionTeacherCreateUpdateSerializer(serializers.ModelSerializer):
    # ✅ create paytida test tanlash uchun
    test_id = serializers.PrimaryKeyRelatedField(
        source="test", queryset=Test.objects.all(), write_only=True
    )

    # ✅ detail/listda ko‘rinishi uchun
    test_title = serializers.CharField(source="test.title", read_only=True)
    choices = ChoiceWriteSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            "id",
            "test_id",
            "test_title",
            "text",
            "question_type",
            "points",
            "correct_answer",
            "choices",
        ]

    def validate(self, attrs):
        instance: Question | None = getattr(self, "instance", None)

        qtype = attrs.get("question_type", instance.question_type if instance else None)
        choices = attrs.get("choices", None)

        # Choice turlarida correct_answer ishlatilmaydi
        if qtype in ["single", "multiple", "true_false"]:
            attrs["correct_answer"] = None

            if choices is not None:
                for c in choices:
                    if not (c.get("text") or "").strip():
                        raise serializers.ValidationError({"choices": "Variant matni bo‘sh bo‘lmasin."})

                correct_count = sum(1 for c in choices if c.get("is_correct"))
                if qtype == "multiple":
                    if correct_count < 1:
                        raise serializers.ValidationError({"choices": "Kamida 1 ta to‘g‘ri variant belgilang."})
                else:
                    if correct_count != 1:
                        raise serializers.ValidationError({"choices": "Aynan 1 ta to‘g‘ri variant bo‘lishi kerak."})

        return attrs

    def create(self, validated_data):
        choices_data = validated_data.pop("choices", [])
        q = Question.objects.create(**validated_data)

        for c in choices_data:
            Choice.objects.create(
                question=q,
                text=(c.get("text") or "").strip(),
                is_correct=bool(c.get("is_correct", False)),
            )
        return q

    def update(self, instance, validated_data):
        choices_data = validated_data.pop("choices", None)

        for f in ["text", "question_type", "points", "correct_answer", "test"]:
            if f in validated_data:
                setattr(instance, f, validated_data[f])
        instance.save()

        if choices_data is not None:
            existing = {c.id: c for c in instance.choices.all()}
            seen = set()

            for c in choices_data:
                cid = c.get("id")
                text = (c.get("text") or "").strip()
                is_correct = bool(c.get("is_correct", False))

                if cid and cid in existing:
                    obj = existing[cid]
                    obj.text = text
                    obj.is_correct = is_correct
                    obj.save()
                    seen.add(cid)
                else:
                    obj = Choice.objects.create(question=instance, text=text, is_correct=is_correct)
                    seen.add(obj.id)

            for cid, obj in existing.items():
                if cid not in seen:
                    obj.delete()

        return instance




User = get_user_model()


class TeacherUserListSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "patronymic",
            "phone",
            "email",
            "role",
            "is_active",
            "branch",
            "branch_name",
            "department",
            "department_name",
        ]


class TeacherUserCreateSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    last_name = serializers.CharField()
    first_name = serializers.CharField()
    patronymic = serializers.CharField()

    branch_id = serializers.IntegerField()
    department_id = serializers.IntegerField()

    assigned_test_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )

    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Bu username band.")
        return value

    def create(self, validated_data):
        assigned_ids = validated_data.pop("assigned_test_ids", [])
        password = validated_data.pop("password")

        validated_data["role"] = "user"

        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        # Agar User modelida assigned_tests ManyToMany bo‘lsa
        if hasattr(user, "assigned_tests"):
            user.assigned_tests.set(Test.objects.filter(id__in=assigned_ids))

        return user
