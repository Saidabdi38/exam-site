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
        OfficeTransaction.objects.prefetch_related("workflow_steps__role"),
        id=pk,
    )

    steps = list(transaction.workflow_steps.all())
    roles = list(OfficeRole.objects.all())

    return render(
        request,
        "office_sim/workflow_swimlane.html",
        {
            "transaction": transaction,
            "steps": steps,
            "roles": roles,
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