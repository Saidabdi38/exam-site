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

class Subject(models.Model):
    name = models.CharField(max_length=120, unique=True)

    def __str__(self):
        return self.name


class BankQuestion(models.Model):
    MCQ = "MCQ"
    TF = "TF"
    TYPES = [(MCQ, "Multiple Choice"), (TF, "True/False")]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="bank_questions")
    text = models.TextField()
    qtype = models.CharField(max_length=10, choices=TYPES, default=MCQ)

    def __str__(self):
        return f"{self.subject.name} - Q{self.id}"


class BankChoice(models.Model):
    question = models.ForeignKey(BankQuestion, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class AttemptQuestion(models.Model):
    attempt = models.ForeignKey("Attempt", on_delete=models.CASCADE, related_name="attempt_questions")
    bank_question = models.ForeignKey(BankQuestion, on_delete=models.CASCADE)

    order = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("attempt", "bank_question")
        ordering = ["order"]

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
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_minutes = models.PositiveIntegerField(default=30)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    subject = models.ForeignKey(Subject, null=True, blank=True, on_delete=models.SET_NULL)
    use_question_bank = models.BooleanField(default=False)
    question_count = models.PositiveIntegerField(default=50)

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

    PASS_PERCENTAGE = 50

    class Meta:
        ordering = ["-started_at"]

    # ✅ ADD THIS BACK
    def time_left_seconds(self):
        if self.submitted_at:
            return 0

        elapsed = (timezone.now() - self.started_at).total_seconds()
        remaining = self.duration_seconds - int(elapsed)
        return max(0, remaining)

    def calculate_score(self):
        total = 0
        max_score = 0

        for answer in self.answers.select_related("selected_choice"):
            max_score += 2
            if answer.selected_choice and answer.selected_choice.is_correct:
                total += 2

        self.score = total
        self.max_score = max_score

    @property
    def percentage(self):
        if self.max_score == 0:
            return 0
        return round((self.score / self.max_score) * 100, 2)

    @property
    def result(self):
        return "PASS" if self.percentage >= self.PASS_PERCENTAGE else "FAIL"

    @property
    def is_submitted(self):
        return self.submitted_at is not None

    def save(self, *args, **kwargs):
        if self.submitted_at:
            self.calculate_score()
        super().save(*args, **kwargs)

class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")

    # one of these used
    question = models.ForeignKey(Question, on_delete=models.CASCADE, null=True, blank=True)
    bank_question = models.ForeignKey(BankQuestion, on_delete=models.CASCADE, null=True, blank=True)

    # old exam selection (keep for backward compatibility)
    selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True, blank=True)

    # ✅ NEW: bank selection
    selected_bank_choice = models.ForeignKey(BankChoice, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                condition=models.Q(question__isnull=False),
                name="unique_attempt_exam_question",
            ),
            models.UniqueConstraint(
                fields=["attempt", "bank_question"],
                condition=models.Q(bank_question__isnull=False),
                name="unique_attempt_bank_question",
            ),
        ]


