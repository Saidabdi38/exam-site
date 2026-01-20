from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.student_dashboard, name="student_dashboard"),
    path("signup/", views.signup, name="signup"),  # ✅ ADD THIS

    path("exams/", views.exam_list, name="exam_list"),
    path("exam/<int:exam_id>/start/", views.start_exam, name="start_exam"),
    path("attempt/<int:attempt_id>/", views.take_exam, name="take_exam"),
    path("attempt/<int:attempt_id>/submit/", views.submit_exam, name="submit_exam"),
    path("attempt/<int:attempt_id>/result/", views.exam_result, name="exam_result"),

    path("after-login/", views.after_login, name="after_login"),
]
