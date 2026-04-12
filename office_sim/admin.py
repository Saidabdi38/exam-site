from django.contrib import admin
from .models import (
    OfficeRole,
    StudentOfficeProfile,
    OfficeTransaction,
    WorkflowStep,
    TransactionDocument,
    StudentTransactionProgress,
    WorkflowNode,
    WorkflowConnection,
)


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 0


class TransactionDocumentInline(admin.TabularInline):
    model = TransactionDocument
    extra = 0


class WorkflowNodeInline(admin.TabularInline):
    model = WorkflowNode
    extra = 0


class WorkflowConnectionInline(admin.TabularInline):
    model = WorkflowConnection
    extra = 0
    fk_name = "transaction"


@admin.register(OfficeRole)
class OfficeRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "office_display_name")
    search_fields = ("name", "office_display_name")


@admin.register(StudentOfficeProfile)
class StudentOfficeProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username",)


@admin.register(OfficeTransaction)
class OfficeTransactionAdmin(admin.ModelAdmin):
    list_display = ("title", "role", "transaction_date", "company_name", "amount", "status")
    list_filter = ("role", "status", "transaction_date")
    search_fields = ("title", "company_name", "description")
    inlines = [
        WorkflowStepInline,
        WorkflowNodeInline,
        WorkflowConnectionInline,
        TransactionDocumentInline,
    ]


@admin.register(StudentTransactionProgress)
class StudentTransactionProgressAdmin(admin.ModelAdmin):
    list_display = ("student", "transaction", "current_step", "is_completed")
    list_filter = ("is_completed", "transaction")
    search_fields = ("student_username", "transaction_title")


@admin.register(WorkflowNode)
class WorkflowNodeAdmin(admin.ModelAdmin):
    list_display = ("transaction", "code", "title", "lane", "row", "node_type")
    list_filter = ("transaction", "lane", "node_type")
    search_fields = ("code", "title")
    ordering = ("transaction", "row", "code")


@admin.register(WorkflowConnection)
class WorkflowConnectionAdmin(admin.ModelAdmin):
    list_display = ("transaction", "from_node", "to_node", "label", "position")
    list_filter = ("transaction",)
    search_fields = ("from_node_code", "to_node_code", "label")
    ordering = ("transaction", "position", "id")