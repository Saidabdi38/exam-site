from django.conf import settings
from django.db import models


class OfficeRole(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class StudentOfficeProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="office_profile",
    )
    role = models.ForeignKey(
        OfficeRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )

    def __str__(self):
        return f"{self.user.username} - {self.role or 'No Role'}"


class OfficeTransaction(models.Model):
    title = models.CharField(max_length=200)
    role = models.ForeignKey(
        OfficeRole,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_date = models.DateField()
    company_name = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    department = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=50, default="Pending")

    def __str__(self):
        return self.title


class WorkflowStep(models.Model):
    transaction = models.ForeignKey(
        OfficeTransaction,
        on_delete=models.CASCADE,
        related_name="workflow_steps",
    )
    step_no = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    responsible_person = models.CharField(max_length=100, blank=True)
    expected_output = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["step_no"]
        unique_together = ("transaction", "step_no")

    def __str__(self):
        return f"{self.transaction.title} - Step {self.step_no}"


class TransactionDocument(models.Model):
    transaction = models.ForeignKey(
        OfficeTransaction,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    name = models.CharField(max_length=200)
    document_type = models.CharField(max_length=100, blank=True)
    content = models.TextField(blank=True)
    file = models.FileField(upload_to="office_docs/", blank=True, null=True)

    def __str__(self):
        return self.name


class StudentTransactionProgress(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transaction_progress",
    )
    transaction = models.ForeignKey(
        OfficeTransaction,
        on_delete=models.CASCADE,
        related_name="student_progress",
    )
    current_step = models.PositiveIntegerField(default=1)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("student", "transaction")

    def __str__(self):
        return f"{self.student.username} - {self.transaction.title}"

class WorkflowNode(models.Model):
    NODE_TYPES = [
        ("start", "Start"),
        ("process", "Process"),
        ("decision", "Decision"),
        ("end", "End"),
    ]

    transaction = models.ForeignKey(
        "OfficeTransaction",
        on_delete=models.CASCADE,
        related_name="nodes",
    )
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    node_type = models.CharField(max_length=20, choices=NODE_TYPES, default="process")
    position = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["position", "id"]
        unique_together = ("transaction", "code")

    def __str__(self):
        return f"{self.transaction.title} - {self.code}"
    

class WorkflowConnection(models.Model):
    transaction = models.ForeignKey(
        "OfficeTransaction",
        on_delete=models.CASCADE,
        related_name="connections",
    )
    from_node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name="outgoing_connections",
    )
    to_node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name="incoming_connections",
    )
    label = models.CharField(max_length=50, blank=True)
    position = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        label = f" ({self.label})" if self.label else ""
        return f"{self.from_node.code} -> {self.to_node.code}{label}"