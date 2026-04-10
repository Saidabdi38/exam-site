from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import (
    OfficeRole,
    StudentOfficeProfile,
    OfficeTransaction,
    StudentTransactionProgress,
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
    return redirect("office_dashboard")


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
    profile = getattr(request.user, "office_profile", None)
    transactions = OfficeTransaction.objects.none()

    if profile and profile.role:
        transactions = OfficeTransaction.objects.filter(
            role=profile.role
        ).order_by("-transaction_date", "id")

    return render(
        request,
        "office_sim/transaction_list.html",
        {
            "profile": profile,
            "transactions": transactions,
        },
    )


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
def transaction_workflow(request, pk):
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

    steps = transaction.workflow_steps.all()
    nodes = list(transaction.nodes.all())
    connections = list(transaction.connections.all())

    mermaid_lines = ["flowchart TD"]

    for node in nodes:
        node_id = f"N{node.id}"
        title = (node.title or "").replace('"', '\\"')

        if node.node_type == "decision":
            mermaid_lines.append(f'{node_id}{{"{title}"}}')
        elif node.node_type == "start":
            mermaid_lines.append(f'{node_id}(["{title}"])')
        elif node.node_type == "end":
            mermaid_lines.append(f'{node_id}(["{title}"])')
        else:
            mermaid_lines.append(f'{node_id}["{title}"]')

    for conn in connections:
        from_id = f"N{conn.from_node_id}"
        to_id = f"N{conn.to_node_id}"
        label = (conn.label or "").replace('"', '\\"')

        if label:
            mermaid_lines.append(f'{from_id} -->|"{label}"| {to_id}')
        else:
            mermaid_lines.append(f"{from_id} --> {to_id}")

    mermaid_lines.append("classDef startEnd fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#111;")
    mermaid_lines.append("classDef process fill:#eef2ff,stroke:#6366f1,stroke-width:2px,color:#111;")
    mermaid_lines.append("classDef decision fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#111;")

    for node in nodes:
        node_id = f"N{node.id}"
        if node.node_type in ["start", "end"]:
            mermaid_lines.append(f"class {node_id} startEnd;")
        elif node.node_type == "decision":
            mermaid_lines.append(f"class {node_id} decision;")
        else:
            mermaid_lines.append(f"class {node_id} process;")

    mermaid_code = "\n".join(mermaid_lines)

    return render(
        request,
        "office_sim/workflow.html",
        {
            "transaction": transaction,
            "steps": steps,
            "progress": progress,
            "documents": transaction.documents.all(),
            "nodes": nodes,
            "connections": connections,
            "mermaid_code": mermaid_code,
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
def workflow_diagram(request, pk):
    transaction = get_object_or_404(
        OfficeTransaction.objects.prefetch_related(
            "nodes",
            "connections__from_node",
            "connections__to_node",
        ),
        id=pk,
    )

    nodes = list(transaction.nodes.all())
    connections = list(transaction.connections.all())

    mermaid_lines = ["flowchart TD"]

    for node in nodes:
        node_id = f"N{node.id}"
        title = (node.title or "").replace('"', '\\"')

        if node.node_type == "decision":
            mermaid_lines.append(f'{node_id}{{"{title}"}}')
        elif node.node_type in ["start", "end"]:
            mermaid_lines.append(f'{node_id}(["{title}"])')
        else:
            mermaid_lines.append(f'{node_id}["{title}"]')

    for conn in connections:
        from_id = f"N{conn.from_node_id}"
        to_id = f"N{conn.to_node_id}"
        label = (conn.label or "").replace('"', '\\"')

        if label:
            mermaid_lines.append(f'{from_id} -->|"{label}"| {to_id}')
        else:
            mermaid_lines.append(f"{from_id} --> {to_id}")

    mermaid_code = "\n".join(mermaid_lines)

    return render(
        request,
        "office_sim/workflow_diagram.html",
        {
            "transaction": transaction,
            "mermaid_code": mermaid_code,
        },
    )
        