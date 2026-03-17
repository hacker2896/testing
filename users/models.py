from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class Branch(models.Model):
    name = models.CharField("Filial", max_length=120, unique=True)

    class Meta:
        verbose_name = "Filial"
        verbose_name_plural = "Filiallar"

    def __str__(self) -> str:
        return self.name


class Department(models.Model):
    name = models.CharField("Bo‘lim", max_length=255)

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["phone"],
                condition=models.Q(phone__isnull=False),
                name="unique_phone_if_not_null",
            ),
            models.UniqueConstraint(
                fields=["email"],
                condition=models.Q(email__isnull=False),
                name="unique_email_if_not_null",
            ),
        ]

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"

    patronymic = models.CharField("Otasining ismi", max_length=120, blank=True)

    branch = models.ForeignKey(
        Branch, on_delete=models.PROTECT, verbose_name="Filial",
        null=True, blank=True
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, verbose_name="Bo‘lim",
        null=True, blank=True
    )

    phone = models.CharField(
        "Telefon",
        max_length=20,
        blank=True,
        null=True,
        validators=[RegexValidator(r"^\+?\d[\d\s\-()]{7,}$", "Telefon raqam noto‘g‘ri formatda.")],
    )
    email = models.EmailField("Email", blank=True, null=True)

    # ✅ faqat 1 marta qoldiriladi
    assigned_tests = models.ManyToManyField(
        "exams.Test",
        verbose_name="Testlar",
        blank=True,
        related_name="users",
    )

    role = models.CharField("Rol", max_length=20, choices=Role.choices, default=Role.STUDENT)
    is_active = models.BooleanField("Active", default=True)

    def save(self, *args, **kwargs):
        # bo'sh stringlarni NULL ga aylantirish
        if self.email == "":
            self.email = None
        if self.phone == "":
            self.phone = None
        super().save(*args, **kwargs)
