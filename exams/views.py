from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Answer, Attempt, Choice, Exam, ExamResitPermission


# -----------------------------
# Helpers
# -----------------------------
def is_teacher(user):
    return user.is_authenticated and (user.is_staff or user.groups.filter(name__in=["Teacher", "Teachers"]).exists())


def get_allowed_attempts(user, exam):
    """
    Total allowed attempts = 1 + extra_attempts (if teacher granted)
    """
    perm = ExamResitPermission.objects.filter(user=user, exam=exam).first()
    return perm.allowed_attempts if perm else 1


def get_next_attempt_no(user, exam):
    """
    Next attempt_no = max(attempt_no) + 1
    """
    max_no = Attempt.objects.filter(user=user, exam=exam).aggregate(m=Max("attempt_no"))["m"] or 0
    return max_no + 1


# -----------------------------
# Public pages
# -----------------------------
def home(request):
    return render(request, "home.html")


def exam_list(request):
    exams = Exam.objects.filter(is_published=True).order_by("-created_at")
    return render(request, "exams/exam_list.html", {"exams": exams})


# -----------------------------
# Auth
# -----------------------------
@login_required
def after_login(request):
    if is_teacher(request.user):
        return redirect("teacher_dashboard")
    return redirect("student_dashboard")


def signup(request):
    if request.user.is_authenticated:
        return redirect("after_login")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = UserCreationForm()

    return render(request, "registration/signup.html", {"form": form})


# -----------------------------
# Teacher
# -----------------------------
@login_required
@user_passes_test(is_teacher)
def teacher_dashboard(request):
    exams = Exam.objects.all().order_by("-created_at")
    return render(request, "teacher/dashboard.html", {"exams": exams})


# -----------------------------
# Student dashboard
# -----------------------------
@login_required
def student_dashboard(request):
    exams = Exam.objects.filter(is_published=True).order_by("-created_at")

    # latest attempt per exam (by attempt_no)
    attempts = (
        Attempt.objects.filter(user=request.user)
        .select_related("exam")
        .order_by("-attempt_no", "-started_at")
    )

    latest_by_exam_id = {}
    for a in attempts:
        if a.exam_id not in latest_by_exam_id:
            latest_by_exam_id[a.exam_id] = a

    rows = []
    for exam in exams:
        latest = latest_by_exam_id.get(exam.id)

        allowed = get_allowed_attempts(request.user, exam)
        used = Attempt.objects.filter(user=request.user, exam=exam).count()
        remaining = max(0, allowed - used)

        if latest is None:
            status = "Not started"
            action = {"label": "Start", "url_name": "start_exam", "arg": exam.id}

        elif not latest.is_submitted:
            status = f"In progress (time left: {latest.time_left_seconds()}s)"
            action = {"label": "Resume", "url_name": "take_exam", "arg": latest.id}

        else:
            status = f"Submitted ({latest.score}/{latest.max_score})"
            if remaining > 0:
                # student can start another attempt, but only if teacher allowed (or still within allowance)
                action = {"label": f"Re-sit ({remaining} left)", "url_name": "start_exam", "arg": exam.id}
            else:
                action = {"label": "View Result", "url_name": "exam_result", "arg": latest.id}

        rows.append(
            {
                "exam": exam,
                "attempt": latest,
                "status": status,
                "action": action,
                "allowed_attempts": allowed,
                "used_attempts": used,
                "remaining_attempts": remaining,
            }
        )

    recent_results = (
        attempts.filter(submitted_at__isnull=False)
        .order_by("-submitted_at")[:10]
    )

    return render(
        request,
        "students/dashboard.html",
        {"rows": rows, "recent_results": recent_results},
    )


# -----------------------------
# Exam flow (resit-aware)
# -----------------------------
@login_required
@transaction.atomic
def start_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, is_published=True)

    # If student has an unfinished attempt, resume it
    unfinished = Attempt.objects.filter(user=request.user, exam=exam, submitted_at__isnull=True).first()
    if unfinished:
        return redirect("take_exam", attempt_id=unfinished.id)

    # Check teacher-controlled resit limit
    allowed = get_allowed_attempts(request.user, exam)
    used = Attempt.objects.filter(user=request.user, exam=exam).count()

    if used >= allowed:
        # No more attempts allowed; just send them back to dashboard
        return redirect("student_dashboard")

    # Create a NEW attempt with a new attempt_no
    attempt_no = get_next_attempt_no(request.user, exam)
    attempt = Attempt.objects.create(
        user=request.user,
        exam=exam,
        attempt_no=attempt_no,
        duration_seconds=exam.duration_minutes * 60,
    )

    # Pre-create answers
    for q in exam.questions.all():
        Answer.objects.get_or_create(attempt=attempt, question=q)

    return redirect("take_exam", attempt_id=attempt.id)


@login_required
@transaction.atomic
def take_exam(request, attempt_id):
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)
    exam = attempt.exam

    # Auto-submit when time ends
    if not attempt.is_submitted and attempt.time_left_seconds() == 0:
        return redirect("submit_exam", attempt_id=attempt.id)

    questions = exam.questions.prefetch_related("choices").all()

    if request.method == "POST" and not attempt.is_submitted:
        for q in questions:
            key = f"q_{q.id}"
            choice_id = request.POST.get(key)
            ans = Answer.objects.get(attempt=attempt, question=q)

            if choice_id:
                ans.selected_choice = Choice.objects.filter(id=choice_id, question=q).first()
            else:
                ans.selected_choice = None
            ans.save()

        if "submit" in request.POST:
            return redirect("submit_exam", attempt_id=attempt.id)

        return redirect("take_exam", attempt_id=attempt.id)

    return render(
        request,
        "exams/take_exam.html",
        {
            "attempt": attempt,
            "exam": exam,
            "questions": questions,
            "time_left": attempt.time_left_seconds(),
        },
    )


@login_required
@transaction.atomic
def submit_exam(request, attempt_id):
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)
    if attempt.is_submitted:
        return redirect("exam_result", attempt_id=attempt.id)

    score = 0
    max_score = 0

    for q in attempt.exam.questions.all():
        max_score += q.points
        ans = Answer.objects.filter(attempt=attempt, question=q).select_related("selected_choice").first()
        if ans and ans.selected_choice and ans.selected_choice.is_correct:
            score += q.points

    attempt.score = score
    attempt.max_score = max_score
    attempt.submitted_at = timezone.now()
    attempt.save()

    return redirect("exam_result", attempt_id=attempt.id)


@login_required
def exam_result(request, attempt_id):
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)
    answers = attempt.answers.select_related("question", "selected_choice").all()
    return render(request, "exams/result.html", {"attempt": attempt, "answers": answers})
