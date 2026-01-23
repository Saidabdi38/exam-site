from django.urls import path
from . import teacher_views as tv

urlpatterns = [
    # Dashboard
    path("teacher/", tv.teacher_dashboard, name="teacher_dashboard"),

    # Exams
    path("teacher/exams/new/", tv.exam_create, name="teacher_exam_create"),
    path("teacher/exams/<int:exam_id>/", tv.exam_detail, name="teacher_exam_detail"),
    path("teacher/exams/<int:exam_id>/edit/", tv.exam_edit, name="teacher_exam_edit"),
    path("teacher/exams/<int:exam_id>/delete/", tv.exam_delete, name="teacher_exam_delete"),

    # Attempts
    path("teacher/exams/<int:exam_id>/attempts/", tv.exam_attempts, name="teacher_exam_attempts"),
    path("teacher/exams/<int:exam_id>/attempts/<int:attempt_id>/", tv.attempt_detail, name="teacher_attempt_detail"),

    # Questions
    path("teacher/exams/<int:exam_id>/questions/new/", tv.question_create, name="teacher_question_create"),
    path("teacher/exams/<int:exam_id>/questions/<int:question_id>/edit/", tv.question_edit, name="teacher_question_edit"),
    path("teacher/exams/<int:exam_id>/questions/<int:question_id>/delete/", tv.question_delete, name="teacher_question_delete"),

    # RESITS
    path("teacher/exams/<int:exam_id>/resits/", tv.manage_resits, name="teacher_manage_resits"),
    path("teacher/exams/<int:exam_id>/resits/<int:user_id>/set/", tv.set_resit, name="teacher_set_resit"),
]
