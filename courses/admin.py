from django.contrib import admin
from .models import Course, Lesson, Chapter


# ===============================
# COURSE ADMIN
# ===============================
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "subject",
        "price",                 # ✅ NEW
        "is_published",
        "allow_students_view",
        "created_at",
    )

    list_filter = (
        "subject",
        "is_published",
        "allow_students_view",
    )

    search_fields = (
        "title",
        "subject__name",
    )

    list_editable = (
        "price",                 # ✅ editable directly
        "is_published",
        "allow_students_view",
    )

    ordering = ("-created_at",)


# ===============================
# CHAPTER ADMIN
# ===============================
@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "course",
        "order",
    )

    list_filter = ("course",)

    ordering = (
        "course",
        "order",
        "id",
    )

    search_fields = ("title",)


# ===============================
# LESSON ADMIN
# ===============================
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "course",
        "chapter",          # ✅ NEW
        "order",
        "is_published",
        "allow_students_view",
    )

    list_filter = (
        "course",
        "chapter",          # ✅ NEW
        "is_published",
        "allow_students_view",
    )

    list_editable = (
        "is_published",
        "allow_students_view",
    )

    ordering = (
        "course",
        "chapter__order",
        "order",
        "id",
    )

    search_fields = ("title",)