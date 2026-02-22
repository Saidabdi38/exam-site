from django.contrib import admin
from .models import Course, Lesson


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "subject",
        "is_published",
        "allow_students_view",
        "created_at",
    )

    list_filter = (
        "is_published",
        "allow_students_view",
        "subject",
    )

    search_fields = ("title",)

    list_editable = (
        "is_published",
        "allow_students_view",
    )


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order", "is_published", "allow_students_view")
    list_editable = ("is_published", "allow_students_view")
    list_filter = ("course", "is_published", "allow_students_view")
    ordering = ("course", "order", "id")