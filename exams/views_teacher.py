from django.db.models import Count
from rest_framework import viewsets, permissions, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework import filters

from .models import Question, Test
from .serializers_teacher import (
    QuestionTeacherListSerializer,
    QuestionTeacherDetailSerializer,
    QuestionTeacherCreateUpdateSerializer,
    TeacherUserListSerializer,
    TeacherUserCreateSerializer,
)

class TeacherQuestionPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


class IsTeacherOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = getattr(request.user, "role", "")
        return role in ["teacher", "admin"] or request.user.is_staff or request.user.is_superuser


class TeacherQuestionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTeacherOrAdmin]
    pagination_class = TeacherQuestionPagination

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["text", "test__title"]
    ordering_fields = ["id", "test__title", "points"]
    ordering = ["-id"]

    # ✅ teacher list/retrieve/update bo‘lsin
    http_method_names = ["get", "post", "patch", "put", "head", "options"]

    def get_queryset(self):
        qs = (
            Question.objects
            .select_related("test")
            .annotate(choices_count=Count("choices"))
            .prefetch_related("choices")
        )

        qtype = self.request.query_params.get("question_type")
        if qtype:
            qs = qs.filter(question_type=qtype)

        test_id = self.request.query_params.get("test_id")
        if test_id:
            qs = qs.filter(test_id=test_id)

        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return QuestionTeacherDetailSerializer
        if self.action in ["create", "update", "partial_update"]:
            return QuestionTeacherCreateUpdateSerializer
        return QuestionTeacherListSerializer

    @action(detail=False, methods=["get"], url_path="tests")
    def tests(self, request):
        qs = Test.objects.filter(questions__isnull=False).distinct().order_by("title")
        data = [{"id": t.id, "title": t.title} for t in qs]
        return Response(data)




###############################

User = get_user_model()


class TeacherUserPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


class TeacherUserViewSet(viewsets.ModelViewSet):
    """
    Teacher faqat role='user' foydalanuvchilarni ko‘radi va yaratadi
    """
    permission_classes = [IsTeacherOrAdmin]
    pagination_class = TeacherUserPagination
    filter_backends = [filters.SearchFilter]
    search_fields = [
        "username",
        "first_name",
        "last_name",
        "patronymic",
        "phone",
        "email",
    ]

    def get_queryset(self):
        qs = User.objects.select_related("branch", "department").prefetch_related("assigned_tests")

        # teacher faqat student/userlarni ko‘rsin
        qs = qs.filter(role__in=["student", "user"])

        return qs.order_by("-id")

    def get_serializer_class(self):
        if self.action == "create":
            return TeacherUserCreateSerializer
        return TeacherUserListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            TeacherUserListSerializer(user).data,
            status=201
        )

    @action(detail=False, methods=["get"], url_path="meta")
    def meta(self, request):
        from users.models import Branch, Department
        from exams.models import Test

        branches = [{"id": b.id, "name": b.name} for b in Branch.objects.order_by("name")]
        departments = [{"id": d.id, "name": d.name} for d in Department.objects.order_by("name")]
        tests = [{"id": t.id, "title": t.title} for t in Test.objects.order_by("title")]

        return Response({
            "branches": branches,
            "departments": departments,
            "tests": tests,
        })