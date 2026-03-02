from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model


User = get_user_model()

class Course(models.Model):
    subject = models.ForeignKey("exams.Subject", on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=200)
    overview = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    is_published = models.BooleanField(default=True)
    allow_students_view = models.BooleanField(default=False, verbose_name="Allow Students View")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

class Chapter(models.Model):

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="chapters"
    )

    title = models.CharField(max_length=200)

    # ✅ ADD THIS
    order = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class CourseAccess(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    can_view = models.BooleanField(default=False)
    lessons_can_view = models.BooleanField(default=True)

    class Meta:
        unique_together = ("course", "user")

class Lesson(models.Model):
    course = models.ForeignKey(
        "Course",
        on_delete=models.CASCADE,
        related_name="lessons",
    )

    chapter = models.ForeignKey(
        "Chapter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lessons",
    )

    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=1)

    is_published = models.BooleanField(default=True)
    allow_students_view = models.BooleanField(default=True)  # ✅ default ON (recommended)

    class Meta:
        # ✅ if chapter is NULL it won’t crash; keeps a stable order
        ordering = ["course_id", "chapter_id", "order", "id"]

    def _str_(self):  # ✅ correct magic method
        ch = f"Ch {self.chapter.order} - " if self.chapter else ""
        return f"{self.course.title} - {ch}{self.order}. {self.title}"
        
class LessonCompletion(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_completions",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="completions",
    )
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-completed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "lesson"],
                name="uniq_completion_user_lesson",
            )
        ]

    def __str__(self):
        return f"{self.user} completed {self.lesson}"


class LessonQuiz(models.Model):
    lesson = models.OneToOneField(
        Lesson,
        on_delete=models.CASCADE,
        related_name="quiz",
    )
    pass_percent = models.PositiveIntegerField(default=60)
    enabled = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["enabled"]),
        ]

    def clean(self):
        if not (0 <= self.pass_percent <= 100):
            raise ValidationError({"pass_percent": "pass_percent must be between 0 and 100."})

    def __str__(self):
        return f"Quiz: {self.lesson}"


class LessonQuizQuestion(models.Model):
    TYPE_MCQ = "MCQ"
    TYPE_TF = "TF"
    TYPE_STRUCT = "STRUCT"

    QUESTION_TYPES = [
        (TYPE_MCQ, "Multiple Choice"),
        (TYPE_TF, "True / False"),
        (TYPE_STRUCT, "Structured"),
    ]

    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVELS = [
        (LEVEL_1, "Level 1"),
        (LEVEL_2, "Level 2"),
        (LEVEL_3, "Level 3"),
    ]

    quiz = models.ForeignKey(
        "LessonQuiz",
        on_delete=models.CASCADE,
        related_name="questions",
    )
    qtype = models.CharField(max_length=10, choices=QUESTION_TYPES, default=TYPE_MCQ)

    # ✅ 3 levels only (used mainly for STRUCT, but can be used for all)
    level = models.PositiveSmallIntegerField(choices=LEVELS, default=LEVEL_1)

    text = models.TextField()
    order = models.PositiveIntegerField(default=1)

    # ✅ For STRUCT: store expected answer + marking guide
    expected_answer = models.TextField(blank=True, default="")
    marking_guide = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["quiz", "order", "id"]

    def clean(self):
        # If structured => should have expected_answer (optional but recommended)
        if self.qtype == self.TYPE_STRUCT and not self.expected_answer.strip():
            # You can remove this if you want expected answer optional
            pass

    def _str_(self):
        return f"Q{self.order} ({self.qtype}) - {self.quiz.lesson.title}"

class LessonQuizChoice(models.Model):
    question = models.ForeignKey(
        LessonQuizQuestion,
        on_delete=models.CASCADE,
        related_name="choices",
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["question"]),
            models.Index(fields=["is_correct"]),
        ]

    def clean(self):
        # Ensure only ONE correct choice per question
        if self.is_correct:
            qs = LessonQuizChoice.objects.filter(question=self.question, is_correct=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("Only one choice can be marked correct per question.")

    def __str__(self):
        return f"Choice for Q{self.question.order}"


class LessonQuizAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_quiz_attempts",
    )
    quiz = models.ForeignKey(
        LessonQuiz,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveIntegerField(default=0)
    max_score = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "quiz"]),
            models.Index(fields=["passed"]),
        ]

    def __str__(self):
        return f"{self.user} attempt on {self.quiz}"


class LessonQuizAnswer(models.Model):
    attempt = models.ForeignKey(
        "LessonQuizAttempt",
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        "LessonQuizQuestion",
        on_delete=models.CASCADE,
        related_name="answers",
    )
    selected_choice = models.ForeignKey(
        "LessonQuizChoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="selected_in_answers",
    )

    # ✅ NEW: for STRUCT
    text_answer = models.TextField(blank=True, default="")

    # ✅ optional: for manual marking later
    awarded_score = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="uniq_answer_per_question_per_attempt",
            )
        ]

class CourseExamLink(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="exam_links",
    )
    exam = models.ForeignKey(
        "exams.Exam",
        on_delete=models.CASCADE,
        related_name="course_links",
    )
    require_quiz_pass = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "exam"],
                name="uniq_course_exam_link",
            )
        ]

    def __str__(self):
        return f"{self.course} -> {self.exam}"