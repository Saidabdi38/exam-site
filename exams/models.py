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
    name = models.CharField(max_length=200)

    level = models.CharField(max_length=50, blank=True, default="Beginner")
    overview = models.TextField(blank=True)

    learning_objectives = models.TextField(blank=True, help_text="One per line")
    topics_covered = models.TextField(blank=True, help_text="One per line")

    assessment_format = models.TextField(blank=True)
    exam_structure = models.TextField(blank=True)
    preparation_tips = models.TextField(blank=True)

    prerequisites = models.TextField(blank=True, help_text="One per line")
    study_materials = models.TextField(blank=True, help_text="One per line")

    def __str__(self):
        return self.name


class BankQuestion(models.Model):
    MCQ = "MCQ"
    TF = "TF"
    STRUCT = "STRUCT"
    SEQ = "SEQ"

    TYPES = [
        (MCQ, "Multiple Choice"),
        (TF, "True/False"),
        (STRUCT, "Structured Question"),
        (SEQ, "Sequencing"),
    ]

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="bank_questions",
    )

    text = models.TextField()
    qtype = models.CharField(
        max_length=10,
        choices=TYPES,
        default=MCQ,
    )

    # Optional score per question
    points = models.PositiveIntegerField(default=2)

    # Structured correct answers
    correct_part_a = models.CharField(max_length=150, blank=True, null=True)
    correct_part_b = models.CharField(max_length=150, blank=True, null=True)
    correct_part_c = models.CharField(max_length=150, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def _str_(self):
        return f"{self.subject.name} - Q{self.id}"


class BankChoice(models.Model):
    question = models.ForeignKey(
        BankQuestion,
        on_delete=models.CASCADE,
        related_name="choices",
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


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

    subject = models.ForeignKey(
        Subject,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    use_question_bank = models.BooleanField(default=True)
    question_count = models.PositiveIntegerField(default=50)

    def __str__(self):
        return self.title


class Question(models.Model):
    """
    Old direct exam question model.
    Keep it only if you still use legacy exams.
    """
    MCQ = "MCQ"
    TF = "TF"
    STRUCT = "STRUCT"
    SEQ = "SEQ"

    TYPES = [
        (MCQ, "Multiple Choice"),
        (TF, "True/False"),
        (STRUCT, "Structured Question"),
        (SEQ, "Sequencing"),
    ]

    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    text = models.TextField()
    qtype = models.CharField(max_length=10, choices=TYPES, default=MCQ)
    points = models.PositiveIntegerField(default=2)

    correct_part_a = models.CharField(max_length=150, blank=True, null=True)
    correct_part_b = models.CharField(max_length=150, blank=True, null=True)
    correct_part_c = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return f"{self.exam.title} - Q{self.id}"


class Choice(models.Model):
    """
    Old direct exam choice model.
    Keep it only if you still use legacy exams.
    """
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="choices",
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class SequencingItem(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="sequence_items",
        null=True,
        blank=True,
    )
    bank_question = models.ForeignKey(
        BankQuestion,
        on_delete=models.CASCADE,
        related_name="sequence_items",
        null=True,
        blank=True,
    )
    text = models.CharField(max_length=255)
    correct_order = models.PositiveIntegerField()

    class Meta:
        ordering = ["correct_order"]

    def __str__(self):
        owner = self.question or self.bank_question
        return f"{owner} - {self.correct_order}. {self.text}"


class ExamResitPermission(models.Model):
    """
    Teacher-controlled resit and visibility.
    extra_attempts = 0  -> total allowed attempts = 1
    can_view = True     -> student can see the exam
    """
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="resit_permissions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resit_permissions",
    )

    extra_attempts = models.PositiveIntegerField(default=0)
    can_view = models.BooleanField(default=True)
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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="attempts",
    )

    attempt_no = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)

    duration_seconds = models.PositiveIntegerField(default=0)
    score = models.FloatField(default=0)
    max_score = models.FloatField(default=0)

    PASS_PERCENTAGE = 50

    class Meta:
        ordering = ["-started_at"]

    def time_left_seconds(self):
        if self.submitted_at:
            return 0

        elapsed = (timezone.now() - self.started_at).total_seconds()
        remaining = self.duration_seconds - int(elapsed)
        return max(0, remaining)

    def calculate_score(self):
        """
        Main scoring logic for bank-question system.
        """
        total = 0
        max_score = 0

        answers = self.answers.select_related(
            "bank_question",
            "selected_bank_choice",
        ).all()

        for answer in answers:
            q = answer.bank_question
            if not q:
                continue

            # MCQ / TF
            if q.qtype in ["MCQ", "TF"]:
                q_points = q.points or 2
                max_score += q_points

                if answer.selected_bank_choice and answer.selected_bank_choice.is_correct:
                    total += q_points

            # STRUCT
            elif q.qtype == "STRUCT":
                # Default 3 marks, one per part
                q_points = q.points or 3
                max_score += q_points

                part_score = 0

                if (
                    answer.structured_part_a
                    and q.correct_part_a
                    and answer.structured_part_a.strip().lower() == q.correct_part_a.strip().lower()
                ):
                    part_score += 1

                if (
                    answer.structured_part_b
                    and q.correct_part_b
                    and answer.structured_part_b.strip().lower() == q.correct_part_b.strip().lower()
                ):
                    part_score += 1

                if (
                    answer.structured_part_c
                    and q.correct_part_c
                    and answer.structured_part_c.strip().lower() == q.correct_part_c.strip().lower()
                ):
                    part_score += 1

                total += part_score

            elif q.qtype == "SEQ":
                correct_items = list(q.sequence_items.all().order_by("correct_order"))
                correct_ids = [str(item.id) for item in correct_items]
                submitted = [str(x) for x in (answer.sequencing_answer or [])]

                q_points = float(q.points or 2)
                max_score += q_points

                if correct_ids:
                    correct_positions = 0
                    for i, correct_id in enumerate(correct_ids):
                        if i < len(submitted) and submitted[i] == correct_id:
                            correct_positions += 1

                    earned = (correct_positions / len(correct_ids)) * q_points
                    total += earned
        self.score = round(total, 2)
        self.max_score = round(max_score, 2)

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

    def __str__(self):
        return f"{self.user} - {self.exam} - Attempt {self.attempt_no}"


class AttemptQuestion(models.Model):
    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name="attempt_questions",
    )
    bank_question = models.ForeignKey(
        BankQuestion,
        on_delete=models.CASCADE,
    )
    order = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("attempt", "bank_question")
        ordering = ["order"]

    def __str__(self):
        return f"Attempt {self.attempt_id} - Q{self.order}"


class Answer(models.Model):
    attempt = models.ForeignKey(
        Attempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )

    # Old exam system
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    selected_choice = models.ForeignKey(
        Choice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # Bank-question system
    bank_question = models.ForeignKey(
        BankQuestion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    selected_bank_choice = models.ForeignKey(
        BankChoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # Structured answers
    structured_part_a = models.CharField(max_length=150, blank=True, null=True)
    structured_part_b = models.CharField(max_length=150, blank=True, null=True)
    structured_part_c = models.CharField(max_length=150, blank=True, null=True)

    # Sequencing
    sequencing_answer = models.JSONField(null=True, blank=True)

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

    def __str__(self):
        if self.bank_question_id:
            return f"Attempt {self.attempt_id} - BankQuestion {self.bank_question_id}"
        if self.question_id:
            return f"Attempt {self.attempt_id} - Question {self.question_id}"
        return f"Attempt {self.attempt_id} - Answer"