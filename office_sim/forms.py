from django import forms
from django.forms import inlineformset_factory, modelformset_factory
from .models import (
    OfficeTransaction,
    WorkflowStep,
    WorkflowNode,
    WorkflowConnection,
    TransactionDocument,
)


class OfficeTransactionForm(forms.ModelForm):
    class Meta:
        model = OfficeTransaction
        fields = [
            "title",
            "role",
            "transaction_date",
            "company_name",
            "amount",
            "description",
            "department",
            "status",
        ]
        widgets = {
            "transaction_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def _init_(self, *args, **kwargs):
        super()._init_(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


class WorkflowStepForm(forms.ModelForm):
    class Meta:
        model = WorkflowStep
        fields = [
            "step_no",
            "title",
            "description",
            "responsible_person",
            "expected_output",
            "role",
            "node_type",
        ]

    def _init_(self, *args, **kwargs):
        super()._init_(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


class WorkflowNodeForm(forms.ModelForm):
    class Meta:
        model = WorkflowNode
        fields = ["code", "title", "description", "node_type", "lane", "row"]

    def _init_(self, *args, **kwargs):
        super()._init_(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


class WorkflowConnectionForm(forms.ModelForm):
    class Meta:
        model = WorkflowConnection
        fields = ["from_node", "to_node", "label", "position"]

    def _init_(self, *args, **kwargs):
        transaction = kwargs.pop("transaction", None)
        super()._init_(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})

        if transaction:
            self.fields["from_node"].queryset = transaction.nodes.all()
            self.fields["to_node"].queryset = transaction.nodes.all()
        else:
            self.fields["from_node"].queryset = WorkflowNode.objects.none()
            self.fields["to_node"].queryset = WorkflowNode.objects.none()


class TransactionDocumentForm(forms.ModelForm):
    class Meta:
        model = TransactionDocument
        fields = ["name", "document_type", "content", "file"]

    def _init_(self, *args, **kwargs):
        super()._init_(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


WorkflowStepFormSet = inlineformset_factory(
    OfficeTransaction, WorkflowStep, form=WorkflowStepForm, extra=1, can_delete=True
)

WorkflowNodeFormSet = inlineformset_factory(
    OfficeTransaction, WorkflowNode, form=WorkflowNodeForm, extra=1, can_delete=True
)

TransactionDocumentFormSet = inlineformset_factory(
    OfficeTransaction, TransactionDocument, form=TransactionDocumentForm, extra=1, can_delete=True
)

WorkflowConnectionFormSet = modelformset_factory(
    WorkflowConnection, form=WorkflowConnectionForm, extra=1, can_delete=True
)

class FullWorkflowUploadForm(forms.Form):
    transactions_file = forms.FileField(required=True)
    steps_file = forms.FileField(required=True)
    nodes_file = forms.FileField(required=True)
    connections_file = forms.FileField(required=True)