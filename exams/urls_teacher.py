# exams/urls_teacher.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_teacher import TeacherTestsListAPIView
from .views_teacher import TeacherQuestionViewSet, TeacherUserViewSet

router = DefaultRouter()
router.register(r"questions", TeacherQuestionViewSet, basename="teacher-questions")
router.register(r"users", TeacherUserViewSet, basename="teacher-users")

urlpatterns = [
    path("tests/", TeacherTestsListAPIView.as_view(), name="teacher-tests"),
    path("", include(router.urls)),  # ✅ MUHIM: router shu yerda ulanadi
]
