# exams/teacher_views.py (FULL UPDATED: CRUD + attempts + resits)

from django.contrib.auth.decorators import login_required, user_passes_test
from django.forms import ModelForm, inlineformset_factory
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.db import models


from .models import Subject, BankQuestion, BankChoice, Answer, Attempt, Choice, Exam, ExamResitPermission, Question

# ---------- Permission ----------
def is_teacher(user):
    # simplest teacher rule: staff OR superuser
    return user.is_authenticated and (user.is_staff or user.is_superuser)

def teacher_required(view_func):
    """
    Wrapper that:
    - requires login
    - requires teacher test
    - returns 403 if not allowed
    """
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Not allowed")
        return view_func(request, *args, **kwargs)
    return _wrapped

@teacher_required
def subject_list(request):
    subjects = Subject.objects.order_by("name")
    return render(request, "teacher/subject_list.html", {"subjects": subjects})

@teacher_required
def bank_question_list(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    questions = BankQuestion.objects.filter(subject=subject).order_by("-id")
    return render(request, "teacher/bank_question_list.html", {
        "subject": subject,
        "questions": questions,
    })

@teacher_required
def bank_question_create(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    q = BankQuestion(subject=subject)
    form = BankQuestionForm(request.POST or None, instance=q)
    formset = BankChoiceFormSet(request.POST or None, instance=q)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        q = form.save(commit=False)
        q.subject = subject
        q.save()
        formset.instance = q
        formset.save()

        # keep only 1 correct
        correct = q.choices.filter(is_correct=True).order_by("-id")
        if correct.count() > 1:
            keep_id = correct.first().id
            q.choices.exclude(id=keep_id).update(is_correct=False)

        return redirect("teacher_bank_question_list", subject_id=subject.id)

    return render(request, "teacher/bank_question_form.html", {
        "form": form,
        "formset": formset,
        "subject": subject,
        "mode": "Create",
    })

@teacher_required
def bank_question_edit(request, subject_id, pk):
    subject = get_object_or_404(Subject, id=subject_id)
    q = get_object_or_404(BankQuestion, id=pk, subject=subject)

    form = BankQuestionForm(request.POST or None, instance=q)
    formset = BankChoiceFormSet(request.POST or None, instance=q)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()

        correct = q.choices.filter(is_correct=True).order_by("-id")
        if correct.count() > 1:
            keep_id = correct.first().id
            q.choices.exclude(id=keep_id).update(is_correct=False)

        return redirect("teacher_bank_question_list", subject_id=subject.id)

    return render(request, "teacher/bank_question_form.html", {
        "form": form,
        "formset": formset,
        "subject": subject,
        "mode": "Edit",
    })

@teacher_required
def bank_question_delete(request, subject_id, pk):
    subject = get_object_or_404(Subject, id=subject_id)
    q = get_object_or_404(BankQuestion, id=pk, subject=subject)

    if request.method == "POST":
        q.delete()
        return redirect("teacher_bank_question_list", subject_id=subject.id)

    return render(request, "teacher/confirm_delete.html", {"object": q})

User = get_user_model()


def _get_owned_exam_or_404(request, exam_id: int) -> Exam:
    """Teachers can only manage their own exams (superuser can manage all)."""
    if request.user.is_superuser:
        return get_object_or_404(Exam, id=exam_id)
    return get_object_or_404(Exam, id=exam_id, created_by=request.user)

# ---------- Forms ----------
class ExamForm(ModelForm):
    class Meta:
        model = Exam
        fields = ["title", "description", "duration_minutes", "is_published", "price"]

class QuestionForm(ModelForm):
    class Meta:
        model = Question
        fields = ["text", "qtype", "points"]

# ---------- Bank Forms ----------
class BankQuestionForm(ModelForm):
    class Meta:
        model = BankQuestion
        fields = ["text", "qtype"]

BankChoiceFormSet = inlineformset_factory(
    BankQuestion,
    BankChoice,
    fields=("text", "is_correct"),
    extra=4,
    can_delete=True,
)

ChoiceFormSet = inlineformset_factory(
    Question,
    Choice,
    fields=("text", "is_correct"),
    extra=4,
    can_delete=True,
)


# ---------- Teacher views ----------
@teacher_required
def teacher_dashboard(request):
    if request.user.is_superuser:
        exams = Exam.objects.order_by("-created_at")
    else:
        exams = Exam.objects.filter(created_by=request.user).order_by("-created_at")
    return render(request, "teacher/dashboard.html", {"exams": exams})


@teacher_required
def exam_create(request):
    form = ExamForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        exam = form.save(commit=False)
        exam.created_by = request.user
        exam.save()
        return redirect("teacher_exam_detail", exam_id=exam.id)
    return render(request, "teacher/exam_form.html", {"form": form, "mode": "Create"})


@teacher_required
def exam_edit(request, exam_id: int):
    exam = _get_owned_exam_or_404(request, exam_id)
    form = ExamForm(request.POST or None, instance=exam)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("teacher_exam_detail", exam_id=exam.id)
    return render(request, "teacher/exam_form.html", {"form": form, "mode": "Edit"})


@teacher_required
def exam_delete(request, exam_id: int):
    exam = _get_owned_exam_or_404(request, exam_id)
    if request.method == "POST":
        exam.delete()
        return redirect("teacher_dashboard")
    return render(request, "teacher/confirm_delete.html", {"object": exam, "type": "Exam"})


@teacher_required
def exam_detail(request, exam_id: int):
    exam = _get_owned_exam_or_404(request, exam_id)
    questions = exam.questions.all().order_by("id")
    return render(request, "teacher/exam_detail.html", {"exam": exam, "questions": questions})


@teacher_required
def question_create(request, exam_id: int):
    exam = _get_owned_exam_or_404(request, exam_id)
    form = QuestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        q = form.save(commit=False)
        q.exam = exam
        q.save()
        return redirect("teacher_question_edit", exam_id=exam.id, question_id=q.id)
    return render(request, "teacher/question_form.html", {"form": form, "exam": exam, "mode": "Create"})


@teacher_required
def question_edit(request, exam_id: int, question_id: int):
    exam = _get_owned_exam_or_404(request, exam_id)
    q = get_object_or_404(Question, id=question_id, exam=exam)

    form = QuestionForm(request.POST or None, instance=q)
    formset = ChoiceFormSet(request.POST or None, instance=q)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        form.save()
        formset.save()

        # Keep ONLY one correct choice (MCQ/TF)
        correct_qs = q.choices.filter(is_correct=True).order_by("-id")
        if correct_qs.count() > 1:
            keep_id = correct_qs.first().id
            q.choices.exclude(id=keep_id).update(is_correct=False)

        return redirect("teacher_exam_detail", exam_id=exam.id)

    return render(
        request,
        "teacher/question_edit.html",
        {"form": form, "formset": formset, "exam": exam, "question": q},
    )


@teacher_required
def question_delete(request, exam_id: int, question_id: int):
    exam = _get_owned_exam_or_404(request, exam_id)
    q = get_object_or_404(Question, id=question_id, exam=exam)
    if request.method == "POST":
        q.delete()
        return redirect("teacher_exam_detail", exam_id=exam.id)
    return render(request, "teacher/confirm_delete.html", {"object": q, "type": "Question"})


@teacher_required
def exam_attempts(request, exam_id: int):
    """List student attempts for an exam (owner-only, superuser can view all)."""
    exam = _get_owned_exam_or_404(request, exam_id)
    attempts = (
        Attempt.objects.filter(exam=exam)
        .select_related("user")
        .order_by("-submitted_at", "-started_at")
    )
    return render(request, "teacher/attempts_list.html", {"exam": exam, "attempts": attempts})

@teacher_required
def attempt_detail(request, exam_id: int, attempt_id: int):
    exam = _get_owned_exam_or_404(request, exam_id)
    attempt = get_object_or_404(Attempt, id=attempt_id, exam=exam)

    answers = Answer.objects.filter(attempt=attempt).select_related(
        "question", "bank_question", "selected_choice"
    ).order_by("id")

    rows = []
    for a in answers:
        # Decide where question came from
        if a.bank_question:
            qtext = a.bank_question.text
            correct = a.bank_question.choices.filter(is_correct=True).first()
        else:
            qtext = a.question.text if a.question else ""
            correct = a.question.choices.filter(is_correct=True).first() if a.question else None

        is_correct = bool(a.selected_choice_id and correct and a.selected_choice_id == correct.id)

        rows.append({
            "question_text": qtext,
            "selected": a.selected_choice,
            "correct": correct,
            "is_correct": is_correct,
        })

    return render(request, "teacher/attempt_detail.html", {
        "exam": exam,
        "attempt": attempt,
        "rows": rows,
    })

@teacher_required
def manage_resits(request, exam_id: int):
    """Page where teachers can give extra attempts (resits) to students."""
    exam = _get_owned_exam_or_404(request, exam_id)
    students = User.objects.order_by("username")

    perms = ExamResitPermission.objects.filter(exam=exam)
    perms_by_user_id = {p.user_id: p for p in perms}

    rows = []
    for student in students:
        perm = perms_by_user_id.get(student.id)
        rows.append({
            "student": student,
            "extra": perm.extra_attempts if perm else 0,
            "allowed": perm.allowed_attempts if perm else 1,
        })

    return render(request, "teacher/manage_resits.html", {"exam": exam, "rows": rows})

@teacher_required
@transaction.atomic
def teacher_set_resit(request, exam_id: int, user_id: int):
    """Set extra attempts for a student (resits)"""
    exam = _get_owned_exam_or_404(request, exam_id)
    student = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        try:
            extra_attempts = int(request.POST.get("extra_attempts", "0"))
        except ValueError:
            extra_attempts = 0
        extra_attempts = max(extra_attempts, 0)

        perm, _ = ExamResitPermission.objects.get_or_create(exam=exam, user=student)
        perm.extra_attempts = extra_attempts
        perm.save()

    return redirect("teacher_manage_resits", exam_id=exam.id)

@login_required
@user_passes_test(is_teacher)
def teacher_add_attempt(request, exam_id, user_id):
    exam = get_object_or_404(Exam, id=exam_id)
    user = get_object_or_404(User, id=user_id)

    perm, _ = ExamResitPermission.objects.get_or_create(exam=exam, user=user)
    perm.extra_attempts += 1
    perm.save()

    return redirect("teacher_manage_resits", exam_id=exam.id)

@teacher_required
def manage_view_permissions(request, exam_id: int):
    """Page where teachers can allow students to view exam results."""
    exam = _get_owned_exam_or_404(request, exam_id)
    students = User.objects.order_by("username")

    perms = ExamResitPermission.objects.filter(exam=exam)
    perms_by_user_id = {p.user_id: p for p in perms}

    rows = []
    for student in students:
        perm = perms_by_user_id.get(student.id)
        rows.append({
            "student": student,
            "can_view": perm.can_view if perm else False,
        })

    return render(request, "teacher/manage_view_permissions.html", {"exam": exam, "rows": rows})

@teacher_required
@transaction.atomic
def set_view_permission(request, exam_id: int, user_id: int):
    """Set can_view permission for a student."""
    exam = _get_owned_exam_or_404(request, exam_id)
    student = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        can_view = request.POST.get("can_view") == "on"
        perm, _ = ExamResitPermission.objects.get_or_create(exam=exam, user=student)
        perm.can_view = can_view
        perm.save()

    return redirect("teacher_manage_view_permissions", exam_id=exam.id)