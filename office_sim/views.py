from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
import csv
import io
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages

from .models import (
    OfficeRole,
    StudentOfficeProfile,
    OfficeTransaction,
    StudentTransactionProgress,
    OfficeTransaction, 
    WorkflowConnection
)

from .forms import (
    OfficeTransactionForm,
    WorkflowStepFormSet,
    WorkflowNodeFormSet,
    WorkflowConnectionFormSet,
    TransactionDocumentFormSet,
    FullWorkflowUploadForm,
)


@login_required
def role_list(request):
    roles = OfficeRole.objects.all().order_by("name")
    return render(request, "office_sim/role_list.html", {"roles": roles})


@login_required
def select_role(request, role_id):
    role = get_object_or_404(OfficeRole, id=role_id)
    profile, _ = StudentOfficeProfile.objects.get_or_create(user=request.user)
    profile.role = role
    profile.save()
    return redirect("office_role_welcome")


@login_required
def office_role_welcome(request):
    profile = getattr(request.user, "office_profile", None)

    if not profile or not profile.role:
        return redirect("role_list")

    return render(
        request,
        "office_sim/role_welcome.html",
        {
            "profile": profile,
            "role": profile.role,
        },
    )


@login_required
def office_dashboard(request):
    profile = getattr(request.user, "office_profile", None)

    if not profile or not profile.role:
        return redirect("role_list")

    transactions = OfficeTransaction.objects.filter(
        role=profile.role
    ).order_by("-transaction_date")

    return render(
        request,
        "office_sim/dashboard.html",
        {
            "profile": profile,
            "transactions": transactions[:5],
        },
    )


@login_required
def transaction_list(request):
    transactions = OfficeTransaction.objects.select_related("role").all().order_by("-id")
    return render(request, "office_sim/transaction_list.html", {"transactions": transactions})

@login_required
def transaction_detail(request, pk):
    transaction = get_object_or_404(
        OfficeTransaction.objects.prefetch_related(
            "workflow_steps",
            "documents",
            "nodes",
            "connections__from_node",
            "connections__to_node",
        ),
        id=pk,
    )

    progress, _ = StudentTransactionProgress.objects.get_or_create(
        student=request.user,
        transaction=transaction,
    )

    return render(
        request,
        "office_sim/transaction_detail.html",
        {
            "transaction": transaction,
            "progress": progress,
            "steps": transaction.workflow_steps.all(),
            "documents": transaction.documents.all(),
            "nodes": transaction.nodes.all(),
            "connections": transaction.connections.all(),
        },
    )


@login_required
def workflow_steps(request, pk):
    transaction = get_object_or_404(
        OfficeTransaction.objects.prefetch_related("workflow_steps"),
        id=pk,
    )

    progress, _ = StudentTransactionProgress.objects.get_or_create(
        student=request.user,
        transaction=transaction,
    )

    return render(
        request,
        "office_sim/workflow_steps.html",
        {
            "transaction": transaction,
            "steps": transaction.workflow_steps.all(),
            "progress": progress,
        },
    )


@login_required
def workflow_swimlane(request, pk):
    transaction = get_object_or_404(
        OfficeTransaction.objects.prefetch_related(
            "nodes",
            "connections__from_node",
            "connections__to_node",
        ),
        id=pk,
    )

    progress, _ = StudentTransactionProgress.objects.get_or_create(
        student=request.user,
        transaction=transaction,
    )

    roles = [
        ("admin", "Admin"),
        ("clerk", "Accounting Clerk"),
        ("accountant", "Accountant"),
        ("manager", "Manager"),
        ("cashier", "Cashier"),
        ("supplier", "Supplier"),
    ]

    nodes = transaction.nodes.all().order_by("row", "id")
    connections = transaction.connections.all().order_by("position", "id")

    connections_data = [
        {
            "from_node": c.from_node.id,
            "to_node": c.to_node.id,
            "label": c.label,
        }
        for c in connections
    ]

    max_row_obj = nodes.order_by("-row").first()
    max_row = max_row_obj.row if max_row_obj else 1
    rows = range(1, max_row + 1)

    return render(
        request,
        "office_sim/workflow_swimlane.html",
        {
            "transaction": transaction,
            "progress": progress,
            "nodes": nodes,
            "roles": roles,
            "rows": rows,
            "connections": connections_data,
        },
    )

@login_required
def update_progress(request, pk, step_no):
    transaction = get_object_or_404(
        OfficeTransaction.objects.prefetch_related("workflow_steps"),
        id=pk,
    )

    progress, _ = StudentTransactionProgress.objects.get_or_create(
        student=request.user,
        transaction=transaction,
    )

    progress.current_step = step_no

    last_step = transaction.workflow_steps.order_by("-step_no").first()
    if last_step and step_no >= last_step.step_no:
        progress.is_completed = True
    else:
        progress.is_completed = False

    progress.save()

    return redirect("workflow_steps", pk=transaction.id)

def role_contract_view(request, role_id):
    role = get_object_or_404(OfficeRole, id=role_id)

    if request.method == "POST":
        if request.POST.get("accepted") == "yes":
            request.session[f"contract_accepted_{role.id}"] = True
            return redirect("office_role_job_description", role_id=role.id)

    return render(request, "office_sim/role_contract.html", {
        "role": role
    })


def role_job_description_view(request, role_id):
    role = get_object_or_404(OfficeRole, id=role_id)

    if not request.session.get(f"contract_accepted_{role.id}"):
        return redirect("office_role_contract", role_id=role.id)

    if request.method == "POST":
        if request.POST.get("accepted") == "yes":
            request.session[f"job_description_accepted_{role.id}"] = True
            return redirect("office_role_welcome", role_id=role.id)

    return render(request, "office_sim/role_job_description.html", {
        "role": role
    })


def role_welcome_view(request, role_id):
    role = get_object_or_404(OfficeRole, id=role_id)

    if not request.session.get(f"contract_accepted_{role.id}"):
        return redirect("office_role_contract", role_id=role.id)

    if not request.session.get(f"job_description_accepted_{role.id}"):
        return redirect("office_role_job_description", role_id=role.id)

    return render(request, "office_sim/role_welcome.html", {
        "role": role
    })

def office_company_list(request):
    companies = (
        OfficeTransaction.objects
        .values_list("company_name", flat=True)
        .distinct()
    )
    return render(request, "office_sim/company_list.html", {"companies": companies})

def office_company_transactions(request, company_name):
    transactions = OfficeTransaction.objects.filter(company_name=company_name)
    return render(request, "office_sim/transaction_list.html", {
        "company_name": company_name,
        "transactions": transactions,
    })

@login_required
def workflow_swimlane(request, pk):
    transaction = get_object_or_404(
        OfficeTransaction.objects.prefetch_related(
            "nodes",
            "connections__from_node",
            "connections__to_node",
        ),
        id=pk,
    )

    roles = [
        ("admin", "Admin"),
        ("clerk", "Accounting Clerk"),
        ("accountant", "Accountant"),
        ("manager", "Manager"),
        ("cashier", "Cashier"),
        ("supplier", "Supplier"),
    ]

    nodes = transaction.nodes.all().order_by("row", "id")
    connections = transaction.connections.all().order_by("position", "id")

    max_row = nodes.order_by("-row").first().row if nodes else 1

    return render(
        request,
        "office_sim/workflow_swimlane.html",
        {
            "transaction": transaction,
            "roles": roles,
            "nodes": nodes,
            "connections": connections,
            "rows": range(1, max_row + 1),
        },
    )

@login_required
def add_transaction(request):
    if request.method == "POST":
        form = OfficeTransactionForm(request.POST)
        step_formset = WorkflowStepFormSet(request.POST, prefix="steps")
        node_formset = WorkflowNodeFormSet(request.POST, prefix="nodes")
        doc_formset = TransactionDocumentFormSet(request.POST, request.FILES, prefix="docs")
        connection_formset = WorkflowConnectionFormSet(
            request.POST,
            queryset=WorkflowConnection.objects.none(),
            prefix="connections",
        )

        if (
            form.is_valid()
            and step_formset.is_valid()
            and node_formset.is_valid()
            and doc_formset.is_valid()
            and connection_formset.is_valid()
        ):
            transaction = form.save()

            step_formset.instance = transaction
            step_formset.save()

            node_formset.instance = transaction
            node_formset.save()

            doc_formset.instance = transaction
            doc_formset.save()

            connections = connection_formset.save(commit=False)
            for obj in connection_formset.deleted_objects:
                obj.delete()

            for connection in connections:
                connection.transaction = transaction
                connection.save()

            return redirect("transaction_list")
    else:
        form = OfficeTransactionForm()
        step_formset = WorkflowStepFormSet(prefix="steps")
        node_formset = WorkflowNodeFormSet(prefix="nodes")
        doc_formset = TransactionDocumentFormSet(prefix="docs")
        connection_formset = WorkflowConnectionFormSet(
            queryset=WorkflowConnection.objects.none(),
            prefix="connections",
        )

    return render(request, "office_sim/add_transaction.html", {
        "form": form,
        "step_formset": step_formset,
        "node_formset": node_formset,
        "connection_formset": connection_formset,
        "doc_formset": doc_formset,
    })

def _read_csv(uploaded_file):
    data = uploaded_file.read().decode("utf-8-sig")
    return csv.DictReader(io.StringIO(data))


@staff_member_required
def upload_transactions(request):
    if request.method == "POST":
        form = FullWorkflowUploadForm(request.POST, request.FILES)

        if form.is_valid():
            transactions_file = form.cleaned_data["transactions_file"]
            steps_file = form.cleaned_data["steps_file"]
            nodes_file = form.cleaned_data["nodes_file"]
            connections_file = form.cleaned_data["connections_file"]

            # maps for later linking
            transaction_map = {}
            node_map = {}

            try:
                # 1. TRANSACTIONS
                for row in _read_csv(transactions_file):
                    role = OfficeRole.objects.get(id=row["role_id"])

                    tx = OfficeTransaction.objects.create(
                        title=row["title"],
                        role=role,
                        transaction_date=row["transaction_date"],
                        company_name=row.get("company_name", ""),
                        amount=row.get("amount") or None,
                        description=row.get("description", ""),
                        department=row.get("department", ""),
                        status=row.get("status", "Pending"),
                    )

                    # external key from CSV
                    transaction_map[row["transaction_code"]] = tx

                # 2. WORKFLOW STEPS
                for row in _read_csv(steps_file):
                    transaction = transaction_map[row["transaction_code"]]

                    role = None
                    if row.get("role_id"):
                        role = OfficeRole.objects.get(id=row["role_id"])

                    WorkflowStep.objects.create(
                        transaction=transaction,
                        step_no=row["step_no"],
                        title=row["title"],
                        description=row.get("description", ""),
                        responsible_person=row.get("responsible_person", ""),
                        expected_output=row.get("expected_output", ""),
                        role=role,
                        node_type=row.get("node_type", "process"),
                    )

                # 3. WORKFLOW NODES
                for row in _read_csv(nodes_file):
                    transaction = transaction_map[row["transaction_code"]]

                    node = WorkflowNode.objects.create(
                        transaction=transaction,
                        code=row["code"],
                        title=row["title"],
                        description=row.get("description", ""),
                        node_type=row.get("node_type", "process"),
                        lane=row.get("lane", "clerk"),
                        row=row.get("row") or 1,
                    )

                    # unique key: transaction_code + node code
                    node_map[f'{row["transaction_code"]}::{row["code"]}'] = node

                # 4. WORKFLOW CONNECTIONS
                for row in _read_csv(connections_file):
                    transaction = transaction_map[row["transaction_code"]]

                    from_node = node_map[f'{row["transaction_code"]}::{row["from_node_code"]}']
                    to_node = node_map[f'{row["transaction_code"]}::{row["to_node_code"]}']

                    WorkflowConnection.objects.create(
                        transaction=transaction,
                        from_node=from_node,
                        to_node=to_node,
                        label=row.get("label", ""),
                        position=row.get("position") or 1,
                    )

                messages.success(request, "Upload completed.")
                return redirect("transaction_list")

            except Exception as e:
                messages.error(request, f"Upload failed: {e}")
    else:
        form = FullWorkflowUploadForm()

    return render(request, "office_sim/upload_transactions.html", {"form": form})