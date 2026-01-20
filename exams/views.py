from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

from .models import Answer, Attempt, Choice, Exam
from django.contrib.auth.decorators import login_required, user_passes_test

def is_teacher(user):
    return user.is_authenticated and user.groups.filter(name="Teacher").exists()

@login_required
@user_passes_test(is_teacher)
def teacher_dashboard(request):
    # You can show exams, questions, results, etc.
    exams = Exam.objects.all().order_by("-created_at")
    return render(request, "teacher/dashboard.html", {"exams": exams})


def home(request):
    # public home page
    return render(request, "home.html")

@login_required
def student_dashboard(request):
    """Student home page: shows published exams and the user's progress/results."""

    exams = Exam.objects.filter(is_published=True).order_by("-created_at")
    attempts = (
        Attempt.objects.filter(user=request.user)
        .select_related("exam")
        .order_by("-started_at")
    )
    attempt_by_exam_id = {a.exam_id: a for a in attempts}

    rows = []
    for exam in exams:
        attempt = attempt_by_exam_id.get(exam.id)

        if attempt is None:
            status = "Not started"
            action = {"label": "Start", "url_name": "start_exam", "arg": exam.id}
        elif not attempt.is_submitted:
            status = f"In progress (time left: {attempt.time_left_seconds()}s)"
            action = {"label": "Resume", "url_name": "take_exam", "arg": attempt.id}
        else:
            status = f"Submitted ({attempt.score}/{attempt.max_score})"
            action = {"label": "View Result", "url_name": "exam_result", "arg": attempt.id}

        rows.append({"exam": exam, "attempt": attempt, "status": status, "action": action})

    recent_results = attempts.filter(submitted_at__isnull=False).order_by("-submitted_at")[:10]

    return render(
        request,
        "students/dashboard.html",
        {"rows": rows, "recent_results": recent_results},
    )

def exam_list(request):
    exams = Exam.objects.filter(is_published=True).order_by("-created_at")
    return render(request, "exams/exam_list.html", {"exams": exams})

@login_required
def after_login(request):
    if request.user.is_staff:
        return redirect("teacher_dashboard")
    return redirect("student_dashboard")

def signup(request):
    if request.user.is_authenticated:
        return redirect("after_login")  # already logged in

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # By default, user is NOT staff (student)
            return redirect("login")  # or auto-login (see below)
    else:
        form = UserCreationForm()

    return render(request, "registration/signup.html", {"form": form})

@login_required
@transaction.atomic
def start_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, is_published=True)

    attempt, created = Attempt.objects.get_or_create(
        user=request.user,
        exam=exam,
        defaults={"duration_seconds": exam.duration_minutes * 60},
    )

    # If already submitted, allow restart (simple behavior)
    if attempt.is_submitted:
        attempt.delete()
        attempt = Attempt.objects.create(
            user=request.user,
            exam=exam,
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

    # auto-submit when time ends
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
        {"attempt": attempt, "exam": exam, "questions": questions, "time_left": attempt.time_left_seconds()},
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

def is_teacher(user):
    return user.is_authenticated and (user.is_staff or user.groups.filter(name="Teachers").exists())

@login_required
@user_passes_test(is_teacher)
def teacher_dashboard(request):
    # You can show exams, questions, results, etc.
    exams = Exam.objects.all().order_by("-created_at")
    return render(request, "teacher/dashboard.html", {"exams": exams})