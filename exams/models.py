from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q

class Test(models.Model):
    title = models.CharField("Test nomi", max_length=200)
    description = models.TextField("Tavsif", blank=True)
    is_active = models.BooleanField("Active", default=True)
    code = models.SlugField("Code", max_length=64, unique=True, blank=True, null=True)
    pass_percent = models.PositiveIntegerField("O‘tish foizi (%)", default=60)
    questions_count = models.PositiveIntegerField(
        "Nechta savol (10–50)",
        default=10,
        validators=[MinValueValidator(10), MaxValueValidator(50)],
        help_text="Har attemptda savollar bankidan random tanlanadi (10–50)."
    )

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"

    def __str__(self):
        return self.title

class TestRule(models.Model):
    test = models.ForeignKey("exams.Test", related_name="rules", on_delete=models.CASCADE, verbose_name="Test")

    branch = models.ForeignKey("users.Branch", null=True, blank=True, on_delete=models.CASCADE, verbose_name="Filial")
    department = models.ForeignKey("users.Department", null=True, blank=True, on_delete=models.CASCADE, verbose_name="Bo‘lim")
    role = models.CharField(max_length=30, null=True, blank=True)

    # ✅ AssignedTest o‘rniga
    attempts_limit = models.PositiveIntegerField(default=1, verbose_name="Urinishlar soni")
    deadline = models.DateTimeField(null=True, blank=True, verbose_name="Muddat")

    is_active = models.BooleanField(default=True, verbose_name="Faol")
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Test davomiyligi (daqiqalarda). Bo'sh bo'lsa Test dagi umumiy vaqt ishlatiladi."
    )

    class Meta:
        verbose_name = "Test qoidasi"
        verbose_name_plural = "Test qoidalari"

    def __str__(self):
        return f"{self.test} / {self.branch or 'Hamma filial'} / {self.department or 'Hamma bo‘lim'} / {self.role or 'Hamma rol'}"



class Question(models.Model):
    TYPE_SINGLE = "single"          # 1 ta to'g'ri javob
    TYPE_MULTIPLE = "multiple"      # bir nechta to'g'ri javob
    TYPE_TRUE_FALSE = "true_false"
    TYPE_SHORT = "short"
    TYPE_NUMERIC = "numeric"
    TYPE_ESSAY = "essay"

    QUESTION_TYPES = [
        (TYPE_SINGLE, "Bittasi to'g'ri"),
        (TYPE_MULTIPLE, "Bir nechtasi to'g'ri"),
        (TYPE_TRUE_FALSE, "To'g'ri / Noto'g'ri"),
        (TYPE_SHORT, "Qisqa javob"),
        (TYPE_NUMERIC, "Numeric"),
        (TYPE_ESSAY, "Essay"),
    ]
    test = models.ForeignKey(Test, on_delete=models.CASCADE,related_name="questions")
    text = models.TextField("Savol matni")
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default=TYPE_SINGLE,)
    points = models.DecimalField("Ball", max_digits=5, decimal_places=2, default=1)
    correct_answer = models.TextField("To'g'ri javob (matn/son)", blank=True, null=True)
    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar banki"

    def __str__(self):
        return f"{self.test.title} - {self.text[:60]}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField("Javob varianti", max_length=500)
    is_correct = models.BooleanField("To‘g‘ri javob", default=False)


    class Meta:
        verbose_name = "Javob varianti"
        verbose_name_plural = "Javob variantlari"

    def __str__(self):
        return f"Q{self.question_id}: {self.text[:40]}"


class Attempt(models.Model):
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    EXPIRED = "expired"
    PENDING_REVIEW = "pending_review"

    STATUS = [
        (IN_PROGRESS, "In progress"),
        (FINISHED, "Finished"),
        (EXPIRED, "Expired"),
        (PENDING_REVIEW, "Pending review"),
    ]

    question_order = models.JSONField(null=True, blank=True)

    status = models.CharField(max_length=32, choices=STATUS, default=IN_PROGRESS)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="attempts")

    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="attempts")



    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    percent = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    def is_time_over(self):
        if self.status != self.IN_PROGRESS:
            return False

        # ✅ eng ishonchli: ends_at bo'lsa shuni ishlatamiz
        if self.ends_at:
            return timezone.now() >= self.ends_at

        # fallback (agar eski attemptlarda ends_at bo'lmasa)
        if self.started_at and self.test and self.test.duration_minutes:
            return timezone.now() >= (self.started_at + timezone.timedelta(minutes=self.test.duration_minutes))

        return False


    def __str__(self):
        return f"{self.user_id} - {self.test.title} ({self.status})"
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status="in_progress"),
                name="uniq_in_progress_attempt_per_user",
            )
        ]

class AttemptAnswer(models.Model):
    attempt = models.ForeignKey("Attempt", on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey("Question", on_delete=models.CASCADE)

    # MUHIM: endi nullable bo'lsin (short/numeric/essay uchun choice bo'lmaydi)
    choice = models.ForeignKey("Choice", on_delete=models.SET_NULL, null=True, blank=True)

    # Oldingi maydonlaringiz qolsin
    is_correct = models.BooleanField(default=False)
    earned_points = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ✅ YANGI (barchasi nullable, eski kodni buzmaydi)
    selected_choice_ids = models.JSONField(default=list, blank=True)   # multiple uchun
    text_answer = models.TextField(null=True, blank=True)             # short/essay uchun
    numeric_answer = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)  # numeric uchun

    class Meta:
        unique_together = ("attempt", "question")



from django.conf import settings
from django.db import models

class AttemptPolicy(models.Model):
    SCOPE_BRANCH = "branch"
    SCOPE_DEPARTMENT = "department"
    SCOPE_USER = "user"
    SCOPE_CHOICES = (
        (SCOPE_BRANCH, "Branch"),
        (SCOPE_DEPARTMENT, "Department"),
        (SCOPE_USER, "User"),
    )

    test = models.ForeignKey("exams.Test", on_delete=models.CASCADE, related_name="attempt_policies")

    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)

    # Qaysi obyektga tegishli (faqat bittasi to'ldiriladi)
    branch = models.ForeignKey("users.Branch", null=True, blank=True, on_delete=models.CASCADE)
    department = models.ForeignKey("users.Department", null=True, blank=True, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE)

    extra_attempts = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["test", "scope", "branch"], name="uniq_test_branch_policy"),
            models.UniqueConstraint(fields=["test", "scope", "department"], name="uniq_test_department_policy"),
            models.UniqueConstraint(fields=["test", "scope", "user"], name="uniq_test_user_policy"),
        ]

    def clean(self):
        # ixtiyoriy: scope ga qarab faqat bittasini talab qilish
        pass

    def __str__(self):
        target = self.user or self.department or self.branch
        return f"{self.test} / {self.scope} / {target} (+{self.extra_attempts})"

