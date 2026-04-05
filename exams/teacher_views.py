from django.contrib.auth.decorators import login_required, user_passes_test
from django.forms import ModelForm, inlineformset_factory
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import get_user_model
from django.db import transaction
from django import forms
import csv
import io

from .models import (
    Subject,
    BankQuestion,
    BankChoice,
    Answer,
    Attempt,
    Choice,
    Exam,
    ExamResitPermission,
    Question,
    SequencingItem,
)

# ---------- Permission ----------
def is_teacher(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def teacher_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not is_teacher(request.user):
            return HttpResponseForbidden("Not allowed")
        return view_func(request, *args, **kwargs)
    return _wrapped


# ---------- Subject Views ----------
@login_required
@user_passes_test(is_teacher)
def subject_create(request):
    if request.method == "POST":
        Subject.objects.create(
            name=request.POST.get("name"),
            level=request.POST.get("level"),
            overview=request.POST.get("overview"),
            learning_objectives=request.POST.get("learning_objectives"),
            topics_covered=request.POST.get("topics_covered"),
            assessment_format=request.POST.get("assessment_format"),
            exam_structure=request.POST.get("exam_structure"),
            preparation_tips=request.POST.get("preparation_tips"),
            prerequisites=request.POST.get("prerequisites"),
            study_materials=request.POST.get("study_materials"),
        )
        return redirect("teacher_subject_list")

    return render(request, "teacher/subject_create.html")


@teacher_required
def subject_edit(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    if request.method == "POST":
        subject.name = request.POST.get("name")
        subject.level = request.POST.get("level")
        subject.overview = request.POST.get("overview")
        subject.learning_objectives = request.POST.get("learning_objectives")
        subject.topics_covered = request.POST.get("topics_covered")
        subject.assessment_format = request.POST.get("assessment_format")
        subject.exam_structure = request.POST.get("exam_structure")
        subject.preparation_tips = request.POST.get("preparation_tips")
        subject.prerequisites = request.POST.get("prerequisites")
        subject.study_materials = request.POST.get("study_materials")
        subject.save()
        return redirect("teacher_subject_list")

    return render(request, "teacher/subject_edit.html", {"subject": subject})


@teacher_required
def subject_delete(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    if request.method == "POST":
        subject.delete()
        return redirect("teacher_subject_list")

    return render(request, "teacher/confirm_delete.html", {
        "object": subject,
        "type": "Subject",
    })


@teacher_required
def subject_list(request):
    subjects = Subject.objects.order_by("name")
    return render(request, "teacher/subject_list.html", {"subjects": subjects})


# ---------- Helpers ----------
User = get_user_model()


def _get_owned_exam_or_404(request, exam_id: int) -> Exam:
    if request.user.is_superuser:
        return get_object_or_404(Exam, id=exam_id)
    return get_object_or_404(Exam, id=exam_id, created_by=request.user)


# ---------- Forms ----------
class ExamForm(ModelForm):
    class Meta:
        model = Exam
        fields = [
            "title", "description", "subject", "use_question_bank", "question_count",
            "duration_minutes", "is_published", "price",
        ]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("use_question_bank") and not cleaned.get("subject"):
            raise forms.ValidationError("Please select a subject when using Question Bank.")
        return cleaned


class QuestionForm(ModelForm):
    class Meta:
        model = Question
        fields = ["text", "qtype", "points", "correct_part_a", "correct_part_b", "correct_part_c"]


class BankQuestionForm(ModelForm):
    class Meta:
        model = BankQuestion
        fields = ["text", "qtype", "correct_part_a", "correct_part_b", "correct_part_c"]


# ---------- Formsets ----------
BankChoiceFormSet = inlineformset_factory(
    BankQuestion,
    BankChoice,
    fields=("text", "is_correct"),
    extra=4,
    can_delete=True,
)

BankSequencingFormSet = inlineformset_factory(
    BankQuestion,
    SequencingItem,
    fk_name="bank_question",
    fields=("text", "correct_order"),
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

SequencingFormSet = inlineformset_factory(
    Question,
    SequencingItem,
    fk_name="question",
    fields=("text", "correct_order"),
    extra=4,
    can_delete=True,
)


# ---------- Bank Question Views ----------
@teacher_required
def bank_question_list(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    questions = BankQuestion.objects.filter(subject=subject).order_by("id")
    return render(request, "teacher/bank_question_list.html", {
        "subject": subject,
        "questions": questions,
    })

@teacher_required
@transaction.atomic
def bank_question_upload(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    if request.method == "POST":
        file = request.FILES.get("file")

        if not file:
            return render(request, "teacher/bank_question_upload.html", {
                "subject": subject,
                "error": "Please choose a file.",
            })

        filename = file.name.lower()

        if filename.endswith(".csv"):
            data = file.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(data))

            for row in reader:
                qtype = (row.get("qtype") or "MCQ").strip().upper()
                text = (row.get("question") or "").strip()

                if not text:
                    continue

                q = BankQuestion.objects.create(
                    subject=subject,
                    text=text,
                    qtype=qtype,
                    correct_part_a=(row.get("correct_part_a") or "").strip() or None,
                    correct_part_b=(row.get("correct_part_b") or "").strip() or None,
                    correct_part_c=(row.get("correct_part_c") or "").strip() or None,
                )

                if qtype in ["MCQ", "TF"]:
                    correct_answer = (row.get("correct_answer") or "").strip().upper()

                    choices_map = {
                        "A": (row.get("A") or "").strip(),
                        "B": (row.get("B") or "").strip(),
                        "C": (row.get("C") or "").strip(),
                        "D": (row.get("D") or "").strip(),
                    }

                    for letter, choice_text in choices_map.items():
                        if choice_text:
                            BankChoice.objects.create(
                                question=q,
                                text=choice_text,
                                is_correct=(letter == correct_answer),
                            )

                elif qtype == "SEQ":
                    items = [
                        (row.get("item1") or "").strip(),
                        (row.get("item2") or "").strip(),
                        (row.get("item3") or "").strip(),
                        (row.get("item4") or "").strip(),
                        (row.get("item5") or "").strip(),
                        (row.get("item6") or "").strip(),
                    ]

                    order_no = 1
                    for item_text in items:
                        if item_text:
                            SequencingItem.objects.create(
                                bank_question=q,
                                text=item_text,
                                correct_order=order_no,
                            )
                            order_no += 1

            return redirect("teacher_bank_question_list", subject_id=subject.id)

        return render(request, "teacher/bank_question_upload.html", {
            "subject": subject,
            "error": "Only CSV file is supported for now.",
        })

    return render(request, "teacher/bank_question_upload.html", {
        "subject": subject,
    })

@teacher_required
def bank_question_create(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)

    q = BankQuestion(subject=subject)
    form = BankQuestionForm(request.POST or None, instance=q)
    formset = BankChoiceFormSet(request.POST or None, instance=q, prefix="choices")
    seq_formset = BankSequencingFormSet(request.POST or None, instance=q, prefix="seq")

    if request.method == "POST" and form.is_valid():
        q = form.save(commit=False)
        q.subject = subject
        q.save()

        if q.qtype == BankQuestion.STRUCT:
            q.choices.all().delete()
            q.sequence_items.all().delete()

        elif q.qtype == BankQuestion.SEQ:
            q.choices.all().delete()

            if seq_formset.is_valid():
                seq_formset.instance = q
                seq_formset.save()
            else:
                return render(request, "teacher/bank_question_form.html", {
                    "form": form,
                    "formset": formset,
                    "seq_formset": seq_formset,
                    "subject": subject,
                    "mode": "Create",
                })

        else:
            q.sequence_items.all().delete()

            if formset.is_valid():
                formset.instance = q
                formset.save()

                correct = q.choices.filter(is_correct=True).order_by("-id")
                if correct.count() > 1:
                    keep_id = correct.first().id
                    q.choices.exclude(id=keep_id).update(is_correct=False)
            else:
                return render(request, "teacher/bank_question_form.html", {
                    "form": form,
                    "formset": formset,
                    "seq_formset": seq_formset,
                    "subject": subject,
                    "mode": "Create",
                })

        return redirect("teacher_bank_question_list", subject_id=subject.id)

    return render(request, "teacher/bank_question_form.html", {
        "form": form,
        "formset": formset,
        "seq_formset": seq_formset,
        "subject": subject,
        "mode": "Create",
    })


@teacher_required
def bank_question_edit(request, subject_id, pk):
    subject = get_object_or_404(Subject, id=subject_id)
    q = get_object_or_404(BankQuestion, id=pk, subject=subject)

    form = BankQuestionForm(request.POST or None, instance=q)
    formset = BankChoiceFormSet(request.POST or None, instance=q, prefix="choices")
    seq_formset = BankSequencingFormSet(request.POST or None, instance=q, prefix="seq")

    if request.method == "POST" and form.is_valid():
        q = form.save()

        if q.qtype == BankQuestion.STRUCT:
            q.choices.all().delete()
            q.sequence_items.all().delete()

        elif q.qtype == BankQuestion.SEQ:
            q.choices.all().delete()

            if seq_formset.is_valid():
                seq_formset.save()
            else:
                return render(request, "teacher/bank_question_form.html", {
                    "form": form,
                    "formset": formset,
                    "seq_formset": seq_formset,
                    "subject": subject,
                    "mode": "Edit",
                })

        else:
            q.sequence_items.all().delete()

            if formset.is_valid():
                formset.save()

                correct = q.choices.filter(is_correct=True).order_by("-id")
                if correct.count() > 1:
                    keep_id = correct.first().id
                    q.choices.exclude(id=keep_id).update(is_correct=False)
            else:
                return render(request, "teacher/bank_question_form.html", {
                    "form": form,
                    "formset": formset,
                    "seq_formset": seq_formset,
                    "subject": subject,
                    "mode": "Edit",
                })

        return redirect("teacher_bank_question_list", subject_id=subject.id)

    return render(request, "teacher/bank_question_form.html", {
        "form": form,
        "formset": formset,
        "seq_formset": seq_formset,
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


# ---------- Teacher Dashboard / Exam Views ----------
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
        return redirect("teacher_dashboard")

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

    return render(request, "teacher/question_form.html", {
        "form": form,
        "exam": exam,
        "mode": "Create",
    })


@teacher_required
def question_edit(request, exam_id: int, question_id: int):
    exam = _get_owned_exam_or_404(request, exam_id)
    q = get_object_or_404(Question, id=question_id, exam=exam)

    form = QuestionForm(request.POST or None, instance=q)
    formset = ChoiceFormSet(request.POST or None, instance=q, prefix="choices")
    seq_formset = SequencingFormSet(request.POST or None, instance=q, prefix="seq")

    if request.method == "POST" and form.is_valid():
        q = form.save()

        if q.qtype == Question.STRUCT:
            q.choices.all().delete()
            q.sequence_items.all().delete()

        elif q.qtype == Question.SEQ:
            q.choices.all().delete()

            if seq_formset.is_valid():
                seq_formset.save()
            else:
                return render(request, "teacher/question_edit.html", {
                    "form": form,
                    "formset": formset,
                    "seq_formset": seq_formset,
                    "exam": exam,
                    "question": q,
                })

        else:
            q.sequence_items.all().delete()

            if formset.is_valid():
                formset.save()

                correct_qs = q.choices.filter(is_correct=True).order_by("-id")
                if correct_qs.count() > 1:
                    keep_id = correct_qs.first().id
                    q.choices.exclude(id=keep_id).update(is_correct=False)
            else:
                return render(request, "teacher/question_edit.html", {
                    "form": form,
                    "formset": formset,
                    "seq_formset": seq_formset,
                    "exam": exam,
                    "question": q,
                })

        return redirect("teacher_exam_detail", exam_id=exam.id)

    return render(request, "teacher/question_edit.html", {
        "form": form,
        "formset": formset,
        "seq_formset": seq_formset,
        "exam": exam,
        "question": q,
    })


@teacher_required
def question_delete(request, exam_id: int, question_id: int):
    exam = _get_owned_exam_or_404(request, exam_id)
    q = get_object_or_404(Question, id=question_id, exam=exam)
    if request.method == "POST":
        q.delete()
        return redirect("teacher_exam_detail", exam_id=exam.id)
    return render(request, "teacher/confirm_delete.html", {"object": q, "type": "Question"})


# ---------- Attempts / Results ----------
@teacher_required
def exam_attempts(request, exam_id: int):
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

    answers = (
        Answer.objects.filter(attempt=attempt)
        .select_related(
            "question",
            "bank_question",
            "selected_choice",
            "selected_bank_choice",
        )
        .order_by("id")
    )

    rows = []

    for a in answers:
        if a.bank_question:
            qobj = a.bank_question
            qtext = qobj.text
            qtype = qobj.qtype
            correct_choice = qobj.choices.filter(is_correct=True).first()
            selected_choice = a.selected_bank_choice
        else:
            qobj = a.question
            qtext = qobj.text if qobj else ""
            qtype = qobj.qtype if qobj else None
            correct_choice = qobj.choices.filter(is_correct=True).first() if qobj else None
            selected_choice = a.selected_choice

        row = {
            "question_text": qtext,
            "qtype": qtype,
            "selected": None,
            "correct": None,
            "is_correct": False,
        }

        # MCQ / TF
        if qtype in ("MCQ", "TF"):
            row["selected"] = selected_choice
            row["correct"] = correct_choice

            if selected_choice and correct_choice and selected_choice.id == correct_choice.id:
                row["is_correct"] = True

        # STRUCT
        elif qtype == "STRUCT":
            student_a = (a.structured_part_a or "").strip()
            student_b = (a.structured_part_b or "").strip()
            student_c = (a.structured_part_c or "").strip()

            correct_a = (getattr(qobj, "correct_part_a", "") or "").strip()
            correct_b = (getattr(qobj, "correct_part_b", "") or "").strip()
            correct_c = (getattr(qobj, "correct_part_c", "") or "").strip()

            row["selected"] = {
                "part_a": student_a,
                "part_b": student_b,
                "part_c": student_c,
            }
            row["correct"] = {
                "part_a": correct_a,
                "part_b": correct_b,
                "part_c": correct_c,
            }

            row["is_correct"] = (
                student_a.lower() == correct_a.lower()
                and student_b.lower() == correct_b.lower()
                and student_c.lower() == correct_c.lower()
            )

        # SEQ
        elif qtype == "SEQ":
            submitted = a.sequencing_answer or []
            correct_items = list(qobj.sequence_items.all().order_by("correct_order"))

            # correct order as ids and text
            correct_ids = [str(item.id) for item in correct_items]
            id_to_text = {str(item.id): item.text for item in correct_items}

            # convert submitted ids to readable text
            selected_texts = [id_to_text.get(str(item_id), str(item_id)) for item_id in submitted]
            correct_texts = [item.text for item in correct_items]

            row["selected"] = selected_texts
            row["correct"] = correct_texts
            row["is_correct"] = [str(x) for x in submitted] == correct_ids

        else:
            row["selected"] = selected_choice
            row["correct"] = correct_choice
            row["is_correct"] = False

        rows.append(row)

    return render(request, "teacher/attempt_detail.html", {
        "exam": exam,
        "attempt": attempt,
        "rows": rows,
    })


# ---------- Resits ----------
@teacher_required
def manage_resits(request, exam_id: int):
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


# ---------- View Permissions ----------
@teacher_required
def manage_view_permissions(request, exam_id: int):
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
    exam = _get_owned_exam_or_404(request, exam_id)
    student = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        can_view = request.POST.get("can_view") == "on"
        perm, _ = ExamResitPermission.objects.get_or_create(exam=exam, user=student)
        perm.can_view = can_view
        perm.save()

    return redirect("teacher_manage_view_permissions", exam_id=exam.id)