from django.contrib.auth.decorators import login_required, user_passes_test
from django.forms import ModelForm, inlineformset_factory
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .models import Answer, Attempt, Choice, Exam, Question


# ---------- Permission ----------
def is_teacher(user):
    # simplest teacher rule: staff OR superuser
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def teacher_required(view_func):
    """
    Wrapper that:
    - requires login
    - requires teacher test
    - returns 403 instead of redirecting to login again
    """
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Not allowed")
        return view_func(request, *args, **kwargs)
    return _wrapped


def _get_owned_exam_or_404(request, exam_id: int) -> Exam:
    """Teachers can only manage their own exams (superuser can manage all)."""
    if request.user.is_superuser:
        return get_object_or_404(Exam, id=exam_id)
    return get_object_or_404(Exam, id=exam_id, created_by=request.user)


# ---------- Forms ----------
class ExamForm(ModelForm):
    class Meta:
        model = Exam
        fields = ["title", "description", "duration_minutes", "is_published"]


class QuestionForm(ModelForm):
    class Meta:
        model = Question
        fields = ["text", "qtype", "points"]


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
    """View a specific student's attempt + per-question correctness."""
    exam = _get_owned_exam_or_404(request, exam_id)
    attempt = get_object_or_404(Attempt, id=attempt_id, exam=exam)

    answers = (
        Answer.objects.filter(attempt=attempt)
        .select_related("question", "selected_choice")
        .order_by("question_id")
    )

    rows = []
    for a in answers:
        correct_choice = a.question.choices.filter(is_correct=True).first()
        is_correct = bool(
            a.selected_choice_id and correct_choice and a.selected_choice_id == correct_choice.id
        )
        rows.append(
            {"question": a.question, "selected": a.selected_choice, "correct": correct_choice, "is_correct": is_correct}
        )

    return render(request, "teacher/attempt_detail.html", {"exam": exam, "attempt": attempt, "rows": rows})
