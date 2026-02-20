from django.conf import settings
from django.db import models
from django.utils import timezone

class Course(models.Model):
    subject = models.ForeignKey("exams.Subject", on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=200)
    overview = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.PositiveIntegerField(default=1)
    is_published = models.BooleanField(default=True)

class LessonCompletion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user","lesson")]

class LessonQuiz(models.Model):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name="quiz")
    pass_percent = models.PositiveIntegerField(default=60)
    enabled = models.BooleanField(default=True)

class LessonQuizQuestion(models.Model):
    quiz = models.ForeignKey(LessonQuiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    order = models.PositiveIntegerField(default=1)

class LessonQuizChoice(models.Model):
    question = models.ForeignKey(LessonQuizQuestion, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

class LessonQuizAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    quiz = models.ForeignKey(LessonQuiz, on_delete=models.CASCADE)
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveIntegerField(default=0)
    max_score = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)

class LessonQuizAnswer(models.Model):
    attempt = models.ForeignKey(LessonQuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(LessonQuizQuestion, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(LessonQuizChoice, on_delete=models.SET_NULL, null=True, blank=True)

class CourseExamLink(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    exam = models.ForeignKey("exams.Exam", on_delete=models.CASCADE)
    require_quiz_pass = models.BooleanField(default=True)
