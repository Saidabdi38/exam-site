from django.urls import path, include
from . import views

urlpatterns = [
    # Home & auth flow
    path("", views.home, name="home"),
    path("after-login/", views.after_login, name="after_login"),
    path("signup/", views.signup, name="signup"),

    # Student
    path("dashboard/", views.student_dashboard, name="student_dashboard"),
    path("student/exams/", views.student_exams, name="student_exams"),
    path("my-exams/", views.student_exams, name="student_exams"),

    # Exams
    path("exams/", views.exam_list, name="exam_list"),
    path("exam/<int:exam_id>/start/", views.start_exam, name="start_exam"),
    path("subjects/<int:subject_id>/", views.subject_detail, name="subject_detail"),

    # Attempts
    path("attempt/<int:attempt_id>/take/", views.take_exam, name="take_exam"),  # keep
    path("attempt/<int:attempt_id>/q/<int:qno>/", views.take_exam_q, name="take_exam_q"),  # ✅ new
    path("attempt/<int:attempt_id>/q/<int:qno>/autosave/", views.autosave_answer, name="autosave_answer"),
    path("attempt/<int:attempt_id>/submit/", views.submit_exam, name="submit_exam"),
    path("attempt/<int:attempt_id>/result/", views.exam_result, name="exam_result"),

     #Price
    path("prices/", views.exam_prices, name="exam_prices"),
]
