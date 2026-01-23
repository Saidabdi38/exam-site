from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Answer,
    Attempt,
    Choice,
    Exam,
    ExamResitPermission,
    Question,
    TeacherProfile,
)

# -------------------- Inlines --------------------
class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


class ExamResitPermissionInline(admin.TabularInline):
    model = ExamResitPermission
    extra = 0
    autocomplete_fields = ("user",)
    readonly_fields = ("get_allowed_attempts",)

    def get_allowed_attempts(self, obj):
        return obj.allowed_attempts
    get_allowed_attempts.short_description = "Allowed Attempts"


# -------------------- Question --------------------
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "exam", "qtype", "points")
    list_filter = ("exam", "qtype")
    search_fields = ("text", "exam__title")
    inlines = [ChoiceInline]


# -------------------- Exam --------------------
@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "created_by", "duration_minutes",
        "is_published", "created_at", "resits_link"
    )
    list_filter = ("is_published", "created_at")
    search_fields = ("title", "description", "created_by__username")
    inlines = [ExamResitPermissionInline]

    def resits_link(self, obj):
        """Add a Manage Resits button for each exam"""
        url = reverse("teacher_manage_resits", args=[obj.id])
        return format_html(
            '<a class="button" href="{}" target="_blank">Manage Resits</a>', url
        )
    resits_link.short_description = "Resits"


# -------------------- Attempt --------------------
@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "exam", "attempt_no",
        "started_at", "submitted_at", "score", "max_score"
    )
    list_filter = ("exam", "submitted_at")
    search_fields = ("user__username", "exam__title")
    ordering = ("-started_at",)


# -------------------- Answer --------------------
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id", "attempt", "question", "selected_choice")
    list_filter = ("attempt__exam",)
    search_fields = ("attempt__user__username", "attempt__exam__title", "question__text")


# -------------------- TeacherProfile --------------------
@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "display_name", "created_at")
    search_fields = ("user__username", "display_name")


# -------------------- ExamResitPermission --------------------
@admin.register(ExamResitPermission)
class ExamResitPermissionAdmin(admin.ModelAdmin):
    list_display = ("id", "exam", "user", "extra_attempts", "get_allowed_attempts", "updated_at")
    list_filter = ("exam", "updated_at")
    search_fields = ("exam__title", "user__username")

    def get_allowed_attempts(self, obj):
        return obj.allowed_attempts
    get_allowed_attempts.short_description = "Allowed Attempts"
