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
    list_display = ("name",)


@admin.register(StudentOfficeProfile)
class StudentOfficeProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")


@admin.register(OfficeTransaction)
class OfficeTransactionAdmin(admin.ModelAdmin):
    list_display = ("title", "role", "transaction_date", "company_name", "amount", "status")
    list_filter = ("role", "status", "transaction_date")
    search_fields = ("title", "company_name", "description")
    inlines = [WorkflowStepInline, WorkflowNodeInline, WorkflowConnectionInline, TransactionDocumentInline]


@admin.register(StudentTransactionProgress)
class StudentTransactionProgressAdmin(admin.ModelAdmin):
    list_display = ("student", "transaction", "current_step", "is_completed")


@admin.register(WorkflowNode)
class WorkflowNodeAdmin(admin.ModelAdmin):
    list_display = ("transaction", "code", "title", "node_type", "position")
    list_filter = ("node_type", "transaction")
    search_fields = ("code", "title")


@admin.register(WorkflowConnection)
class WorkflowConnectionAdmin(admin.ModelAdmin):
    list_display = ("transaction", "from_node", "to_node", "label", "position")
    list_filter = ("transaction",)