from django.urls import path
from . import views

urlpatterns = [
    path("roles/", views.role_list, name="role_list"),
    path("select-role/<int:role_id>/", views.select_role, name="select_role"),
    path("welcome/", views.office_role_welcome, name="office_role_welcome"),

    path("", views.office_dashboard, name="office_dashboard"),

    # ✅ TRANSACTIONS
    path("transactions/", views.transaction_list, name="transaction_list"),
    path("transactions/add/", views.add_transaction, name="add_transaction"),  # 🔥 ADD THIS
    path("transaction/<int:pk>/", views.transaction_detail, name="transaction_detail"),

    # ✅ WORKFLOW
    path("workflow/<int:pk>/steps/", views.workflow_steps, name="workflow_steps"),
    path("workflow/<int:pk>/swimlane/", views.workflow_swimlane, name="workflow_swimlane"),

    # ✅ PROGRESS
    path("progress/<int:pk>/<int:step_no>/", views.update_progress, name="update_progress"),

    # ✅ ROLE
    path("office/role/<int:role_id>/contract/", views.role_contract_view, name="office_role_contract"),
    path("office/role/<int:role_id>/job-description/", views.role_job_description_view, name="office_role_job_description"),
    path("office/role/<int:role_id>/welcome/", views.role_welcome_view, name="office_role_welcome"),

    # ✅ COMPANIES
    path("office/companies/", views.office_company_list, name="office_company_list"),
    path("office/companies/<str:company_name>/transactions/", views.office_company_transactions, name="office_company_transactions"),

    path("transactions/upload/", views.upload_transactions, name="upload_transactions"),
]