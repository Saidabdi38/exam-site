from django.urls import path
from . import teacher_views as tv  # keep alias consistent

urlpatterns = [
    # Dashboard
    path("teacher/", tv.teacher_dashboard, name="teacher_dashboard"),

    # Exams
    path("teacher/exams/<int:exam_id>/", tv.exam_detail, name="teacher_exam_detail"),
    
    # Question Bank (per subject)

    path("teacher/bank/", tv.subject_list, name="teacher_subject_list"),

    path(
        "teacher/bank/<int:subject_id>/",
        tv.bank_question_list,
        name="teacher_bank_question_list",
    ),

    path(
        "teacher/bank/<int:subject_id>/new/",
        tv.bank_question_create,
        name="teacher_bank_question_create",
    ),

    path(
        "teacher/bank/<int:subject_id>/<int:pk>/edit/",
        tv.bank_question_edit,
        name="teacher_bank_question_edit",
    ),

    path(
        "teacher/bank/<int:subject_id>/<int:pk>/delete/",
        tv.bank_question_delete,
        name="teacher_bank_question_delete",
    ),


    # Attempts
    path("teacher/exams/<int:exam_id>/attempts/", tv.exam_attempts, name="teacher_exam_attempts"),
    path("teacher/exams/<int:exam_id>/attempts/<int:attempt_id>/", tv.attempt_detail, name="teacher_attempt_detail"),

    # Questions
    path("teacher/exams/<int:exam_id>/questions/new/", tv.question_create, name="teacher_question_create"),
    path("teacher/exams/<int:exam_id>/questions/<int:question_id>/edit/", tv.question_edit, name="teacher_question_edit"),
    path("teacher/exams/<int:exam_id>/questions/<int:question_id>/delete/", tv.question_delete, name="teacher_question_delete"),

    # RESITS
    path("teacher/exams/<int:exam_id>/resits/", tv.manage_resits, name="teacher_manage_resits"),
    path("teacher/exams/<int:exam_id>/resits/<int:user_id>/set/", tv.teacher_set_resit, name="teacher_set_resit"),
    
    # VIEW PERMISSIONS
    path("teacher/exams/<int:exam_id>/view-permissions/", tv.manage_view_permissions, name="teacher_manage_view_permissions"),
    path("teacher/exams/<int:exam_id>/view-permissions/<int:user_id>/set/", tv.set_view_permission, name="teacher_set_view_permission"),
]
