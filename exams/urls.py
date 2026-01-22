from django.urls import path
from . import views

urlpatterns = [
    # Home & auth flow
    path("", views.home, name="home"),
    path("after-login/", views.after_login, name="after_login"),
    path("signup/", views.signup, name="signup"),

    # Student
    path("dashboard/", views.student_dashboard, name="student_dashboard"),

    # Exams
    path("exams/", views.exam_list, name="exam_list"),
    path("exam/<int:exam_id>/start/", views.start_exam, name="start_exam"),

    # Attempts
    path("attempt/<int:attempt_id>/take/", views.take_exam, name="take_exam"),
    path("attempt/<int:attempt_id>/submit/", views.submit_exam, name="submit_exam"),
    path("attempt/<int:attempt_id>/result/", views.exam_result, name="exam_result"),

    # Teacher
    path("teacher/dashboard/", views.teacher_dashboard, name="teacher_dashboard"),
]
