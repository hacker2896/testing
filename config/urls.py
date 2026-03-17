from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from users.api import me

urlpatterns = [
    path("admin/", admin.site.urls),

    # ✅ barcha exams API shu yerda bo‘ladi
    path("api/exams/", include("exams.urls")),

    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/me/", me, name="me"),
    
    path("api/teacher/", include("exams.urls_teacher")),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
