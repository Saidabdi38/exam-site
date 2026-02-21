from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [

    # =====================================================
    # STUDENT AREA
    # =====================================================
    path(
        "",
        views.course_list,
        name="course_list"
    ),

    path(
        "<int:course_id>/",
        views.course_dashboard,
        name="course_dashboard"
    ),

    path(
        "<int:course_id>/lesson/<int:lesson_id>/",
        views.lesson_detail,
        name="lesson_detail"
    ),

    path(
        "<int:course_id>/lesson/<int:lesson_id>/quiz/",
        views.lesson_quiz,
        name="lesson_quiz"
    ),


    # =====================================================
    # TEACHER COURSE MANAGEMENT
    # =====================================================
    path(
        "create/",
        views.course_create,
        name="course_create"
    ),

    path(
        "<int:course_id>/lesson/add/",
        views.lesson_create,
        name="lesson_create"
    ),


    # =====================================================
    # TEACHER CONTROL PANEL
    # =====================================================
    path(
        "teacher/",
        views.teacher_course_list,
        name="teacher_course_list"
    ),

    # ✅ Publish / Hide course globally
    path(
        "teacher/<int:course_id>/toggle-publish/",
        views.course_toggle_publish,
        name="course_toggle_publish"
    ),

    # ✅ NEW — Student visibility control
    path(
        "teacher/<int:course_id>/visibility/",
        views.manage_course_visibility,
        name="manage_course_visibility"
    ),

    # ✅ Allow / Remove student access
    path(
        "teacher/<int:course_id>/toggle-view/<int:user_id>/",
        views.course_toggle_view,
        name="course_toggle_view"
    ),
]