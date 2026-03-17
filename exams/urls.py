# exams/urls.py
from django.urls import path, include
from . import api
from .api_views import assigned_tests, public_tests
from .views_results import CabinetResultsView, TestAttemptsView, AttemptSummaryView

urlpatterns = [
    path("assigned/", assigned_tests, name="assigned-tests"),
    path("tests/public/", public_tests, name="public-tests"),

    path("<slug:code>/start/", api.start_attempt),
    path("attempts/<int:attempt_id>/", api.attempt_detail),
    path("attempts/<int:attempt_id>/answer/", api.save_answer),
    path("attempts/<int:attempt_id>/submit/", api.submit_attempt),
    path("attempts/in-progress/", api.my_in_progress_attempt),

    path("cabinet/results/", CabinetResultsView.as_view()),
    path("cabinet/results/test/<int:test_id>/attempts/", TestAttemptsView.as_view()),
    path("cabinet/results/attempt/<int:attempt_id>/", AttemptSummaryView.as_view()),

    # ✅ teacher routes
    path("teacher/", include("exams.urls_teacher")),
]
