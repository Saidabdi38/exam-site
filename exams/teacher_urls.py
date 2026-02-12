# exams/teacher_urls.py
from django.urls import path
from . import teacher_views as tv

urlpatterns = [
    # Dashboard
    path("", tv.teacher_dashboard, name="teacher_dashboard"),

    # Exams
    path("exams/<int:exam_id>/", tv.exam_detail, name="teacher_exam_detail"),
    path("exam/create/", tv.exam_create, name="exam_create"),
    path("exams/<int:exam_id>/attempts/", tv.teacher_add_attempt, name="teacher_exam_attempts"),
    path("exams/<int:exam_id>/view-permissions/", tv.manage_view_permissions, name="teacher_manage_view_permissions"),
    path("exams/<int:exam_id>/resits/", tv.manage_resits, name="teacher_manage_resits"),
    path("exams/<int:exam_id>/edit/", tv.exam_edit, name="teacher_exam_edit"),
    path("exams/<int:exam_id>/delete/", tv.exam_delete, name="teacher_exam_delete"),

    # Subjects list (Question Bank home)
    path("bank/", tv.subject_list, name="teacher_subject_list"),

    # Bank Questions (per subject)
    path("bank/<int:subject_id>/", tv.bank_question_list, name="teacher_bank_question_list"),
    path("bank/<int:subject_id>/new/", tv.bank_question_create, name="teacher_bank_question_create"),
    path("bank/<int:subject_id>/<int:pk>/edit/", tv.bank_question_edit, name="teacher_bank_question_edit"),
    path("bank/<int:subject_id>/<int:pk>/delete/", tv.bank_question_delete, name="teacher_bank_question_delete"),

    # Attempts
    path("exams/<int:exam_id>/attempts/", tv.exam_attempts, name="teacher_exam_attempts"),
    path("exams/<int:exam_id>/attempts/<int:attempt_id>/", tv.attempt_detail, name="teacher_attempt_detail"),

    # Questions (if you still allow exam questions)
    path("exams/<int:exam_id>/questions/new/", tv.question_create, name="teacher_question_create"),
    path("exams/<int:exam_id>/questions/<int:question_id>/edit/", tv.question_edit, name="teacher_question_edit"),
    path("exams/<int:exam_id>/questions/<int:question_id>/delete/", tv.question_delete, name="teacher_question_delete"),

    # RESITS
    path("exams/<int:exam_id>/resits/", tv.manage_resits, name="teacher_manage_resits"),
    path("exams/<int:exam_id>/resits/<int:user_id>/set/", tv.teacher_set_resit, name="teacher_set_resit"),

    # VIEW PERMISSIONS
    path("exams/<int:exam_id>/view-permissions/", tv.manage_view_permissions, name="teacher_manage_view_permissions"),
    path("exams/<int:exam_id>/view-permissions/<int:user_id>/set/", tv.set_view_permission, name="teacher_set_view_permission"),
]
