from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [
    path("", views.course_list, name="course_list"),
    path("create/", views.course_create, name="course_create"),  # ✅ NEW
    path("<int:course_id>/", views.course_dashboard, name="course_dashboard"),
    path("<int:course_id>/lesson/add/", views.lesson_create, name="lesson_create"),
    path("<int:course_id>/lesson/<int:lesson_id>/", views.lesson_detail, name="lesson_detail"),
    path("<int:course_id>/lesson/<int:lesson_id>/quiz/", views.lesson_quiz, name="lesson_quiz"),
]