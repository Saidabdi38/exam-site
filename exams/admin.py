from django.contrib import admin

from .models import Answer, Attempt, Choice, Exam, Question, TeacherProfile


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "exam", "qtype", "points")
    list_filter = ("exam", "qtype")
    inlines = [ChoiceInline]


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_by", "duration_minutes", "is_published", "created_at")
    list_filter = ("is_published", "created_at")
    search_fields = ("title", "description", "created_by__username")
admin.site.register(Choice)
admin.site.register(Attempt)
admin.site.register(Answer)
admin.site.register(TeacherProfile)
