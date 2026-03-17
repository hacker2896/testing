from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from .models import Test
from .serializers_teacher import TeacherTestSerializer

class TeacherTestsListAPIView(ListAPIView):
    serializer_class = TeacherTestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Test.objects.all().order_by("-id")
