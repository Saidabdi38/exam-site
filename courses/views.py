from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import get_user_model

from .models import (
    Course, CourseAccess, Lesson, LessonCompletion,
    LessonQuizAttempt, LessonQuizAnswer, LessonQuizChoice
)

from exams.models import Subject
from .utils import course_progress, get_next_lesson

User = get_user_model()

# ===============================
# STUDENT / GENERAL
# ===============================

@login_required
def course_list(request):
    if request.user.is_staff:
        # teachers can see all published courses
        courses = Course.objects.all().order_by("title")
    else:
        # students see only courses they are allowed to view (and published)
        courses = Course.objects.filter(
            is_published=True,
            access_list__user=request.user,
            access_list__can_view=True,
        ).order_by("title")

    return render(request, "courses/course_list.html", {"courses": courses})

@login_required
def course_edit(request, course_id):
    if not request.user.is_staff:
        messages.error(request, "You are not allowed to edit courses.")
        return redirect("courses:course_list")

    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        course.title = request.POST.get("title", "").strip()
        course.overview = request.POST.get("overview", "").strip()
        course.is_published = request.POST.get("is_published") == "on"

        # Optional if you have is_visible in model
        if hasattr(course, "is_visible"):
            course.is_visible = request.POST.get("is_visible") == "on"

        if not course.title:
            messages.error(request, "Title is required.")
            return render(request, "courses/course_edit.html", {"course": course})

        course.save()
        messages.success(request, "Course updated successfully.")
        return redirect("courses:course_dashboard", course_id=course.id)

    return render(request, "courses/course_edit.html", {"course": course})

@staff_member_required
def course_delete(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        title = course.title
        course.delete()
        messages.success(request, f"Course deleted: {title}")
        return redirect("courses:teacher_course_list")

    # If someone opens delete URL by GET, just go back (safe)
    messages.warning(request, "Delete must be confirmed.")
    return redirect("courses:course_dashboard", course_id=course.id)

@staff_member_required
def manage_course_visibility(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Choose who counts as a student in your system:
    students = User.objects.filter(is_staff=False).order_by("username")

    # Ensure every student has a CourseAccess row (so template is easy)
    for s in students:
        CourseAccess.objects.get_or_create(course=course, user=s)

    if request.method == "POST":
        allowed_ids = set(request.POST.getlist("can_view"))  # list of user IDs as strings

        for s in students:
            access = CourseAccess.objects.get(course=course, user=s)
            access.can_view = str(s.id) in allowed_ids
            access.save()

        messages.success(request, "Course visibility updated.")
        return redirect("courses:manage_course_visibility", course_id=course.id)

    access_map = {
        a.user_id: a.can_view
        for a in CourseAccess.objects.filter(course=course, user__in=students)
    }

    return render(request, "courses/manage_course_visibility.html", {
        "course": course,
        "students": students,
        "access_map": access_map,
    })

@login_required
def course_dashboard(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # ✅ Block students if teacher didn't allow view
    if (not request.user.is_staff) and (not course.allow_students_view):
        messages.error(request, "This course is not available yet.")
        return redirect("courses:course_list")

    lessons = Lesson.objects.filter(course=course, is_published=True).order_by("order")

    completed = set(
        LessonCompletion.objects.filter(user=request.user, lesson__course=course)
        .values_list("lesson_id", flat=True)
    )
    rows = [{"lesson": l, "done": l.id in completed} for l in lessons]

    prog = course_progress(request.user, course)
    nxt = get_next_lesson(request.user, course)

    return render(
        request,
        "courses/course_dashboard.html",
        {"course": course, "rows": rows, "progress": prog, "next_lesson": nxt},
    )


@login_required
def lesson_create(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # ✅ Only staff can add lessons
    if not request.user.is_staff:
        messages.error(request, "You are not allowed to add lessons.")
        return redirect("courses:course_dashboard", course_id=course.id)

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        content = (request.POST.get("content") or "").strip()

        if not title:
            messages.error(request, "Lesson title is required.")
            return render(request, "courses/lesson_form.html", {"course": course})

        Lesson.objects.create(
            course=course,
            title=title,
            content=content,
            order=course.lessons.count() + 1,
            is_published=True,
        )

        messages.success(request, "Lesson added.")
        return redirect("courses:course_dashboard", course_id=course.id)

    return render(request, "courses/lesson_form.html", {"course": course})

@staff_member_required
def lesson_delete(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)

    if request.method == "POST":
        title = lesson.title
        lesson.delete()
        messages.success(request, f"Lesson deleted: {title}")
        return redirect("courses:course_dashboard", course_id=course.id)

    messages.warning(request, "Delete must be confirmed.")
    return redirect("courses:course_dashboard", course_id=course.id)
    
@login_required
def lesson_edit(request, course_id, lesson_id):
    if not request.user.is_staff:
        messages.error(request, "You are not allowed to edit lessons.")
        return redirect("courses:course_list")

    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)

    if request.method == "POST":
        lesson.title = request.POST.get("title", "").strip()
        lesson.content = request.POST.get("content", "").strip()

        # optional fields
        order_val = request.POST.get("order")
        if order_val:
            try:
                lesson.order = int(order_val)
            except ValueError:
                pass

        lesson.is_published = request.POST.get("is_published") == "on"

        if not lesson.title:
            messages.error(request, "Lesson title is required.")
            return render(request, "courses/lesson_edit.html", {"course": course, "lesson": lesson})

        lesson.save()
        messages.success(request, "Lesson updated successfully.")
        return redirect("courses:course_dashboard", course_id=course.id)

    return render(request, "courses/lesson_edit.html", {"course": course, "lesson": lesson})
    
@login_required
@transaction.atomic
def lesson_detail(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)

    # ✅ Block students if teacher didn't allow view
    if (not request.user.is_staff) and (not course.allow_students_view):
        messages.error(request, "This course is not available yet.")
        return redirect("courses:course_list")

    lesson = get_object_or_404(Lesson, id=lesson_id, course=course, is_published=True)

    if request.method == "POST":
        LessonCompletion.objects.get_or_create(user=request.user, lesson=lesson)

        # if lesson has a quiz, go to it
        if hasattr(lesson, "quiz") and lesson.quiz:
            return redirect("courses:lesson_quiz", course_id=course.id, lesson_id=lesson.id)

        messages.success(request, "Lesson completed")
        return redirect("courses:course_dashboard", course_id=course.id)

    return render(request, "courses/lesson_detail.html", {"course": course, "lesson": lesson})


@login_required
@transaction.atomic
def lesson_quiz(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)

    # ✅ Block students if teacher didn't allow view
    if (not request.user.is_staff) and (not course.allow_students_view):
        messages.error(request, "This course is not available yet.")
        return redirect("courses:course_list")

    lesson = get_object_or_404(Lesson, id=lesson_id, course=course, is_published=True)

    # Guard: if no quiz linked, avoid 500
    if not hasattr(lesson, "quiz") or not lesson.quiz:
        messages.warning(request, "This lesson has no quiz.")
        return redirect("courses:lesson_detail", course_id=course.id, lesson_id=lesson.id)

    quiz = lesson.quiz
    questions = list(quiz.questions.prefetch_related("choices"))

    if request.method == "POST":
        attempt = LessonQuizAttempt.objects.create(user=request.user, quiz=quiz)

        correct = 0
        for q in questions:
            cid = request.POST.get(f"q_{q.id}")
            if not cid:
                continue

            # ensure selected choice belongs to this question
            choice = get_object_or_404(LessonQuizChoice, id=cid, question=q)

            LessonQuizAnswer.objects.create(
                attempt=attempt, question=q, selected_choice=choice
            )

            if choice.is_correct:
                correct += 1

        attempt.score = correct
        attempt.max_score = len(questions)
        attempt.passed = correct >= (len(questions) * quiz.pass_percent / 100)
        attempt.save()

        return redirect("courses:course_dashboard", course_id=course.id)

    return render(
        request,
        "courses/lesson_quiz.html",
        {"course": course, "lesson": lesson, "questions": questions},
    )


# ===============================
# TEACHER COURSE MANAGEMENT
# ===============================

@login_required
def course_create(request):
    if not request.user.is_staff:
        messages.error(request, "You are not allowed to create courses.")
        return redirect("courses:course_list")

    subjects = Subject.objects.all().order_by("name")

    if request.method == "POST":
        subject_id = request.POST.get("subject")
        title = (request.POST.get("title") or "").strip()
        overview = (request.POST.get("overview") or "").strip()
        is_published = request.POST.get("is_published") == "on"

        if not subject_id or not title:
            messages.error(request, "Subject and Title are required.")
            return render(request, "courses/course_create.html", {"subjects": subjects})

        course = Course.objects.create(
            subject_id=subject_id,
            title=title,
            overview=overview,
            is_published=is_published,
            allow_students_view=False,  # ✅ default locked until teacher clicks View
        )

        messages.success(request, "Course created successfully (students cannot see it yet).")
        return redirect("courses:course_dashboard", course_id=course.id)

    return render(request, "courses/course_create.html", {"subjects": subjects})

def course_prices(request):
    courses = Course.objects.filter(is_published=True)
    return render(
        request,
        "public/course_prices.html",
        {"courses": courses})
        
@staff_member_required
def teacher_course_list(request):
    # teachers see all courses (published or not)
    courses = Course.objects.all().order_by("-created_at")
    return render(request, "courses/teacher_course_list.html", {"courses": courses})


@staff_member_required
def course_toggle_publish(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    course.is_published = not course.is_published

    # If unpublished, also hide from students
    if not course.is_published:
        course.allow_students_view = False

    course.save()
    return redirect("courses:teacher_course_list")


@staff_member_required
def course_toggle_view(request, course_id):
    """
    ✅ NEW: Teacher 'View' button:
    - Only works if course is published
    - Toggles allow_students_view
    """
    course = get_object_or_404(Course, id=course_id)

    if not course.is_published:
        messages.error(request, "Publish the course first before allowing students to view it.")
        return redirect("courses:teacher_course_list")

    course.allow_students_view = not course.allow_students_view
    course.save()

    if course.allow_students_view:
        messages.success(request, "Students can now view this course.")
    else:
        messages.warning(request, "Students can no longer view this course.")

    return redirect("courses:teacher_course_list")