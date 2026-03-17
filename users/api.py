from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers

from .models import User, Branch, Department


class BranchMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name"]


class DepartmentMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]


class MeSerializer(serializers.ModelSerializer):
    branch = BranchMiniSerializer(read_only=True)
    department = DepartmentMiniSerializer(read_only=True)

    # adminligini ko‘rsatish uchun
    is_admin = serializers.SerializerMethodField()

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
            "branch",
            "department",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
        ]

    def get_is_admin(self, obj):
        return bool(obj.is_staff or obj.is_superuser)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(MeSerializer(request.user).data)
