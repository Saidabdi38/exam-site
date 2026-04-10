from django.urls import path
from . import views

urlpatterns = [
    path("roles/", views.role_list, name="role_list"),
    path("select-role/<int:role_id>/", views.select_role, name="select_role"),

    path("", views.office_dashboard, name="office_dashboard"),
    path("transactions/", views.transaction_list, name="transaction_list"),
    path("transaction/<int:pk>/", views.transaction_detail, name="transaction_detail"),
    path("workflow/<int:pk>/", views.transaction_workflow, name="transaction_workflow"),
    path("progress/<int:pk>/<int:step_no>/", views.update_progress, name="update_progress"),
]