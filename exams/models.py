from django.conf import settings
from django.db import models
from django.utils import timezone


class TeacherProfile(models.Model):
    """
    Optional profile model for teachers.
    Permissions still come from Groups, but this makes a real teacher record.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_profile",
    )
    display_name = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name or getattr(self.user, "username", str(self.user))


class Exam(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_exams",
        help_text="Teacher who created/owns this exam.",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    MCQ = "MCQ"
    TF = "TF"
    TYPES = [(MCQ, "Multiple Choice"), (TF, "True/False")]

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    qtype = models.CharField(max_length=10, choices=TYPES, default=MCQ)
    points = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.exam.title} - Q{self.id}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class ExamResitPermission(models.Model):
    """
    Teacher-controlled resit and visibility.
    extra_attempts = 0  -> total allowed attempts = 1
    can_view = True     -> student can see the exam
    """
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="resit_permissions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resit_permissions")

    extra_attempts = models.PositiveIntegerField(default=0)
    can_view = models.BooleanField(default=True)  # ✅ new field
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("exam", "user")
        indexes = [models.Index(fields=["exam", "user"])]

    @property
    def allowed_attempts(self):
        return 1 + self.extra_attempts

    def __str__(self):
        return f"{self.user} - {self.exam} (allowed={self.allowed_attempts}, visible={self.can_view})"

class Attempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="attempts")

    attempt_no = models.PositiveIntegerField(default=1)

    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)

    duration_seconds = models.PositiveIntegerField(default=0)
    score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]
        unique_together = ("user", "exam", "attempt_no")
        indexes = [
            models.Index(fields=["user", "exam"]),
            models.Index(fields=["exam"]),
            models.Index(fields=["submitted_at"]),
        ]

    @property
    def is_submitted(self):
        return self.submitted_at is not None

    def time_left_seconds(self):
        if self.is_submitted:
            return 0
        elapsed = (timezone.now() - self.started_at).total_seconds()
        left = self.duration_seconds - int(elapsed)
        return max(0, left)

    def __str__(self):
        return f"{self.user} - {self.exam} (Attempt {self.attempt_no})"


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ("attempt", "question")
        indexes = [models.Index(fields=["attempt", "question"])]

    def __str__(self):
        return f"{self.attempt} - Q{self.question_id}"
