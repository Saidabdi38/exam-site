from django.contrib import admin

from .models import (
    Answer,
    Attempt,
    Choice,
    Exam,
    ExamResitPermission,   # ✅ add
    Question,
    TeacherProfile,
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "exam", "qtype", "points")
    list_filter = ("exam", "qtype")
    search_fields = ("text", "exam__title")
    inlines = [ChoiceInline]


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_by", "duration_minutes", "is_published", "created_at")
    list_filter = ("is_published", "created_at")
    search_fields = ("title", "description", "created_by__username")


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "exam", "attempt_no", "started_at", "submitted_at", "score", "max_score")
    list_filter = ("exam", "submitted_at")
    search_fields = ("user__username", "exam__title")
    ordering = ("-started_at",)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "question", "selected_choice")
    list_filter = ("attempt__exam",)
    search_fields = ("attempt__user__username", "attempt__exam__title", "question__text")


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "display_name", "created_at")
    search_fields = ("user__username", "display_name")


@admin.register(ExamResitPermission)
class ExamResitPermissionAdmin(admin.ModelAdmin):
    list_display = ("id", "exam", "user", "extra_attempts", "allowed_attempts", "updated_at")
    list_filter = ("exam", "updated_at")
    search_fields = ("exam__title", "user__username")
