from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [
    # ===============================
    # PUBLIC / PRICES
    # ===============================
    path("prices/", views.course_prices, name="course_prices"),

    # ===============================
    # STUDENT
    # ===============================
    path("", views.course_list, name="course_list"),
    path("<int:course_id>/detail/", views.course_detail, name="course_detail"),
    path("<int:course_id>/", views.course_dashboard, name="course_dashboard"),

    path("<int:course_id>/lesson/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),
    path("<int:course_id>/lesson/<int:lesson_id>/quiz/create/", views.lesson_quiz_create, name="lesson_quiz_create"),
    path("<int:course_id>/lesson/<int:lesson_id>/quiz/", views.lesson_quiz, name="lesson_quiz"),

    # ===============================
    # TEACHER PANEL
    # ===============================
    path("teacher/", views.teacher_course_list, name="teacher_course_list"),
    path("teacher/<int:course_id>/visibility/", views.manage_course_visibility, name="manage_course_visibility"),
    path("teacher/<int:course_id>/toggle-publish/", views.course_toggle_publish, name="course_toggle_publish"),

    # ===============================
    # TEACHER COURSE MANAGEMENT
    # ===============================
    path("create/", views.course_create, name="course_create"),
    path("<int:course_id>/edit/", views.course_edit, name="course_edit"),
    path("<int:course_id>/delete/", views.course_delete, name="course_delete"),

    # ===============================
    # CHAPTERS
    # ===============================
    path("<int:course_id>/chapters/add/", views.chapter_create, name="chapter_create"),
    path("<int:course_id>/chapters/<int:chapter_id>/edit/", views.chapter_edit, name="chapter_edit"),

    # ===============================
    # LESSONS
    # ===============================
    path("<int:course_id>/lesson/add/", views.lesson_create, name="lesson_create"),
    path("<int:course_id>/lesson/<int:lesson_id>/edit/", views.lesson_edit, name="lesson_edit"),
    path("<int:course_id>/lesson/<int:lesson_id>/delete/", views.lesson_delete, name="lesson_delete"),
]