from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import Http404

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

def get_resume_qno(attempt):
    """
    Returns question number (1-based) to resume at:
    - first unanswered question
    - else last question
    """
    exam = attempt.exam
    questions = list(exam.questions.order_by("id").all())
    total = len(questions)
    if total == 0:
        return 1

    answers = attempt.answers.select_related("question", "selected_choice").all()
    answer_by_qid = {a.question_id: a for a in answers}

    for i, q in enumerate(questions, start=1):
        ans = answer_by_qid.get(q.id)
        if not ans or ans.selected_choice_id is None:
            return i  # ✅ first unanswered

    return total  # ✅ all answered -> go to last question

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


@login_required
def student_dashboard(request):
    user = request.user

    # Only exams teacher allowed this student to see
    exams = Exam.objects.filter(
        is_published=True,
        resit_permissions__user=user,
        resit_permissions__can_view=True
    ).distinct().order_by("-created_at")

    # Latest attempt per exam
    attempts = Attempt.objects.filter(user=user).select_related("exam").order_by("-attempt_no", "-started_at")
    latest_by_exam_id = {}
    for a in attempts:
        if a.exam_id not in latest_by_exam_id:
            latest_by_exam_id[a.exam_id] = a

    rows = []
    for exam in exams:
        latest = latest_by_exam_id.get(exam.id)

        # Teacher allowed attempts
        perm = ExamResitPermission.objects.filter(exam=exam, user=user).first()
        allowed = perm.allowed_attempts if perm else 1
        used = Attempt.objects.filter(user=user, exam=exam).count()
        remaining = max(0, allowed - used)

        if latest is None:
            status = "Not started"
            action = {"label": "Start", "url_name": "start_exam", "arg": exam.id}

        # elif not latest.is_submitted:
        #     status = f"In progress (time left: {latest.time_left_seconds()}s)"
        #     action = {"label": "Resume", "url_name": "take_exam", "arg": latest.id}

        elif not latest.is_submitted:
            status = f"In progress (time left: {latest.time_left_seconds()}s)"
            qno = get_resume_qno(latest)
            action = {"label": "Resume", "url_name": "take_exam_q", "args": [latest.id, qno]}

        else:
            status = f"Submitted ({latest.score}/{latest.max_score})"
            if remaining > 0:
                action = {"label": f"Re-sit ({remaining} left)", "url_name": "start_exam", "arg": exam.id}
            else:
                action = {"label": "View Result", "url_name": "exam_result", "arg": latest.id}

        rows.append({
            "exam": exam,
            "attempt": latest,
            "status": status,
            "action": action,
            "allowed_attempts": allowed,
            "used_attempts": used,
            "remaining_attempts": remaining,
        })

    recent_results = attempts.filter(submitted_at__isnull=False).order_by("-submitted_at")[:10]

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
    # unfinished = Attempt.objects.filter(user=request.user, exam=exam, submitted_at__isnull=True).first()
    # if unfinished:
    #     return redirect("take_exam", attempt_id=unfinished.id)
    unfinished = Attempt.objects.filter(user=request.user, exam=exam, submitted_at__isnull=True).first()
    if unfinished:
        qno = get_resume_qno(unfinished)
        return redirect("take_exam_q", attempt_id=unfinished.id, qno=qno)

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

# @login_required
# @transaction.atomic
# def take_exam(request, attempt_id):
#     attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)
#     exam = attempt.exam

#     # ✅ Backend auto-submit (NO is_submitted dependency)
#     if attempt.submitted_at is None:
#         elapsed = (timezone.now() - attempt.started_at).total_seconds()
#         if elapsed >= attempt.duration_seconds:
#             return redirect("submit_exam", attempt_id=attempt.id)

#     questions = exam.questions.prefetch_related("choices").all()

#     if request.method == "POST" and attempt.submitted_at is None:
#         for q in questions:
#             key = f"q_{q.id}"
#             choice_id = request.POST.get(key)

#             ans, _ = Answer.objects.get_or_create(
#                 attempt=attempt,
#                 question=q
#             )

#             if choice_id:
#                 ans.selected_choice = Choice.objects.filter(
#                     id=choice_id, question=q
#                 ).first()
#             else:
#                 ans.selected_choice = None
#             ans.save()

#         if "submit" in request.POST:
#             return redirect("submit_exam", attempt_id=attempt.id)

#         return redirect("take_exam", attempt_id=attempt.id)

#     return render(
#         request,
#         "exams/take_exam.html",
#         {
#             "attempt": attempt,
#             "exam": exam,
#             "questions": questions,
#             "time_left": attempt.time_left_seconds(),
#         },
#     )


@login_required
@transaction.atomic
def take_exam(request, attempt_id):
    """
    Keep this URL, but redirect student to the first question page.
    """
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)
    return redirect("take_exam_q", attempt_id=attempt.id, qno=1)


@login_required
@transaction.atomic
def take_exam_q(request, attempt_id, qno):
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)
    exam = attempt.exam

    # ✅ Auto-submit if time finished
    if attempt.submitted_at is None:
        elapsed = (timezone.now() - attempt.started_at).total_seconds()
        if elapsed >= attempt.duration_seconds:
            return redirect("submit_exam", attempt_id=attempt.id)

    questions = list(exam.questions.prefetch_related("choices").all())
    total = len(questions)
    if total == 0:
        raise Http404("No questions in this exam.")

    if qno < 1 or qno > total:
        raise Http404("Question number out of range.")

    question = questions[qno - 1]

    # get existing answer for this question
    ans, _ = Answer.objects.get_or_create(attempt=attempt, question=question)

    if request.method == "POST" and attempt.submitted_at is None:
        choice_id = request.POST.get("answer")

        if choice_id:
            ans.selected_choice = Choice.objects.filter(id=choice_id, question=question).first()
        else:
            ans.selected_choice = None
        ans.save()

        nav = request.POST.get("nav")  # prev / next / submit

        if nav == "prev" and qno > 1:
            return redirect("take_exam_q", attempt_id=attempt.id, qno=qno - 1)

        if nav == "next" and qno < total:
            return redirect("take_exam_q", attempt_id=attempt.id, qno=qno + 1)

        if nav == "submit":
            return redirect("submit_exam", attempt_id=attempt.id)

        # default fallback
        return redirect("take_exam_q", attempt_id=attempt.id, qno=qno)

    time_left = attempt.time_left_seconds()

    return render(
        request,
        "exams/take_exam_one.html",
        {
            "attempt": attempt,
            "exam": exam,
            "question": question,
            "choices": question.choices.all(),
            "qno": qno,
            "total": total,
            "selected_choice_id": ans.selected_choice_id,
            "has_prev": qno > 1,
            "has_next": qno < total,
            "time_left": time_left,
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
        max_score += 2  # ✅ 2 marks per question

        ans = Answer.objects.filter(
            attempt=attempt,
            question=q
        ).select_related("selected_choice").first()

        if ans and ans.selected_choice and ans.selected_choice.is_correct:
            score += 2

    attempt.score = score
    attempt.max_score = max_score
    attempt.submitted_at = timezone.now()
    attempt.save()

    return redirect("exam_result", attempt_id=attempt.id)

@login_required
def exam_result(request, attempt_id):
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)

    percentage = (
        (attempt.score / attempt.max_score) * 100
        if attempt.max_score > 0 else 0
    )

    result = "PASS" if percentage >= 50 else "FAIL"

    answers = attempt.answers.select_related(
        "question", "selected_choice"
    ).all()

    return render(
        request,
        "exams/result.html",
        {
            "attempt": attempt,
            "answers": answers,
            "percentage": round(percentage, 2),
            "result": result,
        },
    )

@login_required
def student_exams(request):
    user = request.user

    # Get exams the student is allowed to see
    exams = Exam.objects.filter(
        examresitpermission__user=user,
        examresitpermission__can_view=True
    ).distinct().order_by('-created_at')

    rows = []
    for exam in exams:
        # Check if the student has already attempted this exam
        attempt = Attempt.objects.filter(user=user, exam=exam).order_by('-attempt_no').first()

        if attempt:
            status = "Submitted" if attempt.is_submitted else "In Progress"
            action = {"url_name": "take_exam", "label": "Continue Exam", "arg": exam.id} if not attempt.is_submitted else {"url_name": "view_exam_result", "label": "View Result", "arg": attempt.id}
        else:
            status = "Not Started"
            action = {"url_name": "take_exam", "label": "Start Exam", "arg": exam.id}

        rows.append({
            "exam": exam,
            "attempt": attempt,
            "status": status,
            "action": action,
        })

    # Optional: recent results
    recent_results = Attempt.objects.filter(user=user, submitted_at__isnull=False).order_by('-submitted_at')[:5]

    return render(request, "student/dashboard.html", {"rows": rows, "recent_results": recent_results})

def exam_prices(request):
    exams = Exam.objects.filter(is_published=True)
    return render(request, "public/exam_prices.html", {"exams": exams})