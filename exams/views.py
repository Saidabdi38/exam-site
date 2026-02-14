from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import Http404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from random import sample
from .models import Subject, BankQuestion, AttemptQuestion, Question, Answer, BankChoice, Attempt, Exam, ExamResitPermission


# -----------------------------
# Helpers
# -----------------------------
def is_teacher(user):
    return user.is_authenticated and (user.is_staff or user.groups.filter(name__in=["Teacher", "Teachers"]).exists())

def get_permission(user, exam):
    return ExamResitPermission.objects.filter(user=user, exam=exam).first()

def can_view_exam(user, exam):
    perm = get_permission(user, exam)
    return bool(perm and perm.can_view)

def get_allowed_attempts(user, exam):
    """
    Total allowed attempts ONLY if teacher allowed view
    """
    perm = get_permission(user, exam)
    if not perm or not perm.can_view:
        return 0
    return perm.allowed_attempts

def get_next_attempt_no(user, exam):
    """
    Next attempt_no = max(attempt_no) + 1
    """
    max_no = Attempt.objects.filter(user=user, exam=exam).aggregate(m=Max("attempt_no"))["m"] or 0
    return max_no + 1

def get_resume_qno(attempt):
    aqs = list(attempt.attempt_questions.select_related("bank_question").all())
    total = len(aqs)
    if total == 0:
        return 1

    answered_ids = set(
        attempt.answers.filter(selected_choice__isnull=False).values_list("attempt_question_id", flat=True)
    )

    for i, aq in enumerate(aqs, start=1):
        if aq.id not in answered_ids:
            return i

    return total

# -----------------------------
# Public pages
# -----------------------------
def home(request):
    subjects = Subject.objects.all().order_by("name")
    return render(request, "home.html", {"subjects": subjects})


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

    exams = Exam.objects.filter(
        is_published=True,
        resit_permissions__user=user,
        resit_permissions__can_view=True
    ).distinct().order_by("-created_at")

    attempts = Attempt.objects.filter(user=user).select_related("exam").order_by("-attempt_no", "-started_at")
    latest_by_exam_id = {}
    for a in attempts:
        if a.exam_id not in latest_by_exam_id:
            latest_by_exam_id[a.exam_id] = a

    rows = []
    for exam in exams:
        latest = latest_by_exam_id.get(exam.id)

        perm = ExamResitPermission.objects.filter(exam=exam, user=user).first()
        allowed = perm.allowed_attempts if perm else 1
        used = Attempt.objects.filter(user=user, exam=exam).count()
        remaining = max(0, allowed - used)

        # ✅ default action structure
        action = {"label": "", "url_name": "", "arg": None, "args": None}

        if latest is None:
            status = "Not started"
            action.update({"label": "Start", "url_name": "start_exam", "arg": exam.id})

        elif not latest.is_submitted:
            status = f"In progress (time left: {latest.time_left_seconds()}s)"
            qno = get_resume_qno(latest)
            action.update({"label": "Resume", "url_name": "take_exam_q", "args": [latest.id, qno]})

        else:
            status = f"Submitted ({latest.score}/{latest.max_score})"
            if remaining > 0:
                action.update({"label": f"Re-sit ({remaining} left)", "url_name": "start_exam", "arg": exam.id})
            else:
                action.update({"label": "View Result", "url_name": "exam_result", "arg": latest.id})

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

def _lines(text):
    if not text:
        return []
    return [i.strip() for i in text.splitlines() if i.strip()]

def subject_detail(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    ctx = {
        "subject": subject,
        "learning_objectives": _lines(subject.learning_objectives),
        "topics_covered": _lines(subject.topics_covered),
        "prerequisites": _lines(subject.prerequisites),
        "study_materials": _lines(subject.study_materials),
    }
    return render(request, "exams/subject_detail.html", ctx)

@login_required
@user_passes_test(staff_required)
def subject_create(request):
    if request.method == "POST":
        Subject.objects.create(
            name=request.POST.get("name"),
            level=request.POST.get("level"),
            overview=request.POST.get("overview"),
            learning_objectives=request.POST.get("learning_objectives"),
            topics_covered=request.POST.get("topics_covered"),
            assessment_format=request.POST.get("assessment_format"),
            exam_structure=request.POST.get("exa…
[14:02, 14/02/2026] Siciid Cabdi: path("subject/create/", views.subject_create, name="subject_create"),
# -----------------------------
# Exam flow (resit-aware)
# -----------------------------
@login_required
@transaction.atomic
def start_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id, is_published=True)

    if not can_view_exam(request.user, exam):
        return redirect("student_dashboard")

    unfinished = Attempt.objects.filter(user=request.user, exam=exam, submitted_at__isnull=True).first()
    if unfinished:
        qno = get_resume_qno(unfinished)
        return redirect("take_exam_q", attempt_id=unfinished.id, qno=qno)

    allowed = get_allowed_attempts(request.user, exam)
    used = Attempt.objects.filter(user=request.user, exam=exam).count()
    if used >= allowed:
        return redirect("student_dashboard")

    # ✅ Create attempt
    attempt_no = get_next_attempt_no(request.user, exam)
    attempt = Attempt.objects.create(
        user=request.user,
        exam=exam,
        attempt_no=attempt_no,
        duration_seconds=exam.duration_minutes * 60,
    )

    if not exam.use_question_bank or not exam.subject_id:
        raise Http404("Exam is not configured to use question bank / subject missing.")

    bank_qs = list(
        BankQuestion.objects.filter(subject_id=exam.subject_id).prefetch_related("choices")
    )

    if len(bank_qs) < exam.question_count:
        raise Http404(f"Not enough questions in bank. Need {exam.question_count}, have {len(bank_qs)}")

    selected = sample(bank_qs, exam.question_count)

    for idx, bq in enumerate(selected, start=1):
        AttemptQuestion.objects.create(
            attempt=attempt,
            bank_question=bq,
            order=idx,
        )
        Answer.objects.create(
            attempt=attempt,
            bank_question=bq,
        )

    return redirect("take_exam_q", attempt_id=attempt.id, qno=1)

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

    if not can_view_exam(request.user, exam):
        return redirect("student_dashboard")

    # auto-submit when time finished
    if attempt.submitted_at is None:
        elapsed = (timezone.now() - attempt.started_at).total_seconds()
        if elapsed >= attempt.duration_seconds:
            return redirect("submit_exam", attempt_id=attempt.id)

    # Questions frozen for THIS attempt (ordered)
    aqs = list(
        AttemptQuestion.objects.filter(attempt=attempt)
        .select_related("bank_question")
        .prefetch_related("bank_question__choices")
        .order_by("order")
    )

    total = len(aqs)
    if total == 0:
        raise Http404("No questions were generated for this attempt.")

    if qno < 1 or qno > total:
        raise Http404("Question number out of range.")

    aq = aqs[qno - 1]
    question = aq.bank_question
    choices = list(question.choices.all())

    # ✅ Answer record for this attempt + this bank question
    ans, _ = Answer.objects.get_or_create(
        attempt=attempt,
        bank_question=question,
        defaults={"question": None},  # keep old field empty
    )

    # Save answer
    if request.method == "POST" and attempt.submitted_at is None:
        choice_id = request.POST.get("answer", "").strip()

        if choice_id:
            ans.selected_bank_choice = BankChoice.objects.filter(
                id=choice_id,
                question=question
            ).first()
        else:
            ans.selected_bank_choice = None

        ans.save()

        nav = request.POST.get("nav")
        if nav == "prev" and qno > 1:
            return redirect("take_exam_q", attempt_id=attempt.id, qno=qno - 1)
        if nav == "next" and qno < total:
            return redirect("take_exam_q", attempt_id=attempt.id, qno=qno + 1)
        if nav == "submit":
            return redirect("submit_exam", attempt_id=attempt.id)

        return redirect("take_exam_q", attempt_id=attempt.id, qno=qno)

    time_left = attempt.time_left_seconds()

    # progress bar: which questions answered
    answered_bq_ids = set(
        Answer.objects.filter(attempt=attempt, selected_bank_choice__isnull=False)
        .values_list("bank_question_id", flat=True)
    )

    progress = []
    for i, one_aq in enumerate(aqs, start=1):
        progress.append({"no": i, "answered": (one_aq.bank_question_id in answered_bq_ids)})

    return render(
        request,
        "exams/take_exam_one.html",
        {
            "attempt": attempt,
            "exam": exam,
            "question": question,
            "choices": choices,
            "qno": qno,
            "total": total,
            # ✅ use selected_bank_choice now
            "selected_choice_id": ans.selected_bank_choice_id,
            "has_prev": qno > 1,
            "has_next": qno < total,
            "time_left": time_left,
            "progress": progress,
        },
    )

@login_required
@transaction.atomic
def autosave_answer(request, attempt_id, qno):
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)

    # ✅ don't allow autosave after submit
    if attempt.submitted_at is not None:
        return JsonResponse({"ok": False, "error": "submitted"}, status=400)

    aqs = list(
        AttemptQuestion.objects.filter(attempt=attempt)
        .select_related("bank_question")
        .order_by("order")
    )

    total = len(aqs)
    if total == 0 or qno < 1 or qno > total:
        raise Http404("Question number out of range.")

    aq = aqs[qno - 1]
    bq = aq.bank_question

    ans, _ = Answer.objects.get_or_create(
        attempt=attempt,
        bank_question=bq,
        defaults={"question": None},
    )

    if request.method == "POST":
        choice_id = request.POST.get("answer", "").strip()

        if choice_id:
            ans.selected_bank_choice = BankChoice.objects.filter(
                id=choice_id, question=bq
            ).first()
        else:
            ans.selected_bank_choice = None

        ans.save()

    return JsonResponse({"ok": True})
    
@login_required
@transaction.atomic
def submit_exam(request, attempt_id):
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)

    if not can_view_exam(request.user, attempt.exam):
        return redirect("student_dashboard")

    if attempt.submitted_at:
        return redirect("exam_result", attempt_id=attempt.id)

    answers = attempt.answers.select_related("selected_bank_choice").all()

    score = 0
    max_score = len(answers) * 2

    for ans in answers:
        if ans.selected_bank_choice and ans.selected_bank_choice.is_correct:
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