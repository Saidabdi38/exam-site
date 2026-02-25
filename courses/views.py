from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import get_user_model
from collections import OrderedDict

from .models import (
    Course, CourseAccess, Lesson, LessonCompletion,
    LessonQuizAttempt, LessonQuizAnswer, LessonQuizChoice, Chapter
)

from exams.models import Subject
from .utils import course_progress, get_next_lesson

User = get_user_model()

# ===============================
# STUDENT / GENERALa
# ===============================

@login_required
def course_list(request):

    # STAFF sees everything
    if request.user.is_staff:
        courses = Course.objects.filter(is_published=True)
        return render(
            request,
            "courses/course_list.html",
            {"courses": courses}
        )

    # STUDENT ACCESS CONTROL
    access_qs = CourseAccess.objects.filter(
        user=request.user,
        can_view=True,
        lessons_can_view=True,
        course__is_published=True,
        course__allow_students_view=True,   # ✅ FIX HERE
    ).select_related("course")

    courses = [a.course for a in access_qs]

    return render(
        request,
        "courses/course_list.html",
        {"courses": courses}
    )
        
@login_required
def course_edit(request, course_id):
    if not request.user.is_staff:
        messages.error(request, "You are not allowed to edit courses.")
        return redirect("courses:course_list")

    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        course.title = (request.POST.get("title") or "").strip()
        course.overview = (request.POST.get("overview") or "").strip()
        course.is_published = ("is_published" in request.POST)

        # ✅ PRICE
        price_raw = (request.POST.get("price") or "0").strip()
        try:
            course.price = Decimal(price_raw)  # ✅ SAVE
        except (InvalidOperation, ValueError):
            messages.error(request, "Invalid price value.")
            return render(request, "courses/course_edit.html", {"course": course})

        # Optional if you have is_visible in model
        if hasattr(course, "is_visible"):
            course.is_visible = ("is_visible" in request.POST)

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
    students = User.objects.filter(is_staff=False).order_by("username")
    lessons = Lesson.objects.filter(course=course).order_by("order", "id")

    # Ensure every student has a CourseAccess row
    for s in students:
        CourseAccess.objects.get_or_create(course=course, user=s)

    if request.method == "POST":
        # Global course switch
        course.allow_students_view = ("course_allow_students_view" in request.POST)
        course.save(update_fields=["allow_students_view"])

        # Per-student course view
        course_view_ids = set(request.POST.getlist("student_course_view"))
        lessons_view_ids = set(request.POST.getlist("student_lessons_view"))

        for s in students:
            access = CourseAccess.objects.get(course=course, user=s)
            access.can_view = str(s.id) in course_view_ids

            # Only if you added lessons_can_view field
            if hasattr(access, "lessons_can_view"):
                access.lessons_can_view = str(s.id) in lessons_view_ids

            access.save()

        # Lesson flags
        for l in lessons:
            l.is_published = (f"lesson_is_published_{l.id}" in request.POST)
            l.allow_students_view = (f"lesson_allow_students_{l.id}" in request.POST)
            l.save(update_fields=["is_published", "allow_students_view"])

        messages.success(request, "Course visibility updated.")
        return redirect("courses:manage_course_visibility", course_id=course.id)

    access_map = {
        a.user_id: a.can_view
        for a in CourseAccess.objects.filter(course=course, user__in=students)
    }

    lesson_access_map = None
    if any(getattr(f, "name", "") == "lessons_can_view" for f in CourseAccess._meta.get_fields()):
        lesson_access_map = {
            a.user_id: a.lessons_can_view
            for a in CourseAccess.objects.filter(course=course, user__in=students)
        }

    return render(request, "courses/manage_course_visibility.html", {
        "course": course,
        "students": students,
        "lessons": lessons,
        "access_map": access_map,
        "lesson_access_map": lesson_access_map,
    })
    
@login_required
def course_dashboard(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # student access (your existing rules)
    if not request.user.is_staff:
        access = CourseAccess.objects.filter(course=course, user=request.user, can_view=True).exists()
        if not (access and course.is_published and course.allow_students_view):
            messages.error(request, "This course is not available yet.")
            return redirect("courses:course_list")

    # chapters (so even empty chapters appear)
    chapters = course.chapters.all().order_by("order", "id")

    lessons_qs = Lesson.objects.filter(course=course).select_related("chapter").order_by(
        "chapter__order", "chapter_id", "order", "id"
    )

    if not request.user.is_staff:
        lessons_qs = lessons_qs.filter(is_published=True, allow_students_view=True)

    completed_ids = set(
        LessonCompletion.objects.filter(user=request.user, lesson__course=course)
        .values_list("lesson_id", flat=True)
    )

    grouped = OrderedDict()

    # ✅ add all chapters first (even if no lessons)
    for ch in chapters:
        grouped[ch] = []

    # ✅ add "No Chapter"
    grouped[None] = []

    # fill lessons
    for l in lessons_qs:
        key = l.chapter  # Chapter object or None
        grouped.setdefault(key, [])
        grouped[key].append({"lesson": l, "done": (l.id in completed_ids)})

    # progress
    total = lessons_qs.count()
    done = sum(1 for l in lessons_qs if l.id in completed_ids)
    percent = int((done / total) * 100) if total else 0

    next_lesson = None
    for l in lessons_qs:
        if l.id not in completed_ids:
            next_lesson = l
            break

    return render(request, "courses/course_dashboard.html", {
        "course": course,
        "grouped": grouped,
        "progress": {"done": done, "total": total, "percent": percent},
        "next_lesson": next_lesson,
    })
        
@login_required
def chapter_create(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Only teachers/admins
    if not request.user.is_staff:
        messages.error(request, "You are not allowed to add chapters.")
        return redirect("courses:course_dashboard", course_id=course.id)

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        order_val = request.POST.get("order") or ""

        if not title:
            messages.error(request, "Chapter title is required.")
            return render(request, "courses/chapter_form.html", {"course": course})

        order = 1
        if order_val.strip():
            try:
                order = int(order_val)
            except ValueError:
                order = 1
        else:
            # auto next order
            last = course.chapters.order_by("-order", "-id").first()
            order = (last.order + 1) if last else 1

        Chapter.objects.create(course=course, title=title, order=order)
        messages.success(request, "Chapter added successfully.")
        return redirect("courses:course_dashboard", course_id=course.id)

    return render(request, "courses/chapter_form.html", {"course": course})

@login_required
def chapter_edit(request, course_id, chapter_id):

    if not request.user.is_staff:
        messages.error(request, "You are not allowed.")
        return redirect("courses:course_list")

    course = get_object_or_404(Course, id=course_id)
    chapter = get_object_or_404(
        Chapter,
        id=chapter_id,
        course=course
    )

    if request.method == "POST":
        chapter.title = request.POST.get("title", "").strip()

        order_val = request.POST.get("order")
        if order_val:
            try:
                chapter.order = int(order_val)
            except ValueError:
                pass

        if not chapter.title:
            messages.error(request, "Chapter title required.")
            return render(
                request,
                "courses/chapter_form.html",
                {"course": course, "chapter": chapter}
            )

        chapter.save()
        messages.success(request, "Chapter updated.")
        return redirect(
            "courses:course_dashboard",
            course_id=course.id
        )

    return render(
        request,
        "courses/chapter_form.html",
        {"course": course, "chapter": chapter}
    )
    
@login_required
def lesson_create(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if not request.user.is_staff:
        messages.error(request, "You are not allowed to add lessons.")
        return redirect("courses:course_dashboard", course_id=course.id)

    chapters = course.chapters.all().order_by("order", "id")

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        content = (request.POST.get("content") or "").strip()
        chapter_id = request.POST.get("chapter") or None

        if not title:
            messages.error(request, "Lesson title is required.")
            return render(request, "courses/lesson_form.html", {"course": course, "chapters": chapters})

        Lesson.objects.create(
            course=course,
            chapter_id=chapter_id,         # ✅ NEW
            title=title,
            content=content,
            order=course.lessons.count() + 1,
            is_published=True,
            allow_students_view=True,
        )

        messages.success(request, "Lesson added successfully.")
        return redirect("courses:course_dashboard", course_id=course.id)

    return render(request, "courses/lesson_form.html", {"course": course, "chapters": chapters})
        
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

    # Only teacher/staff
    if not request.user.is_staff:
        messages.error(request, "You are not allowed to edit lessons.")
        return redirect("courses:course_list")

    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)

    # ✅ needed for chapter dropdown in template
    chapters = course.chapters.all().order_by("order", "id")

    if request.method == "POST":

        # ✅ CHAPTER (new)
        lesson.chapter_id = request.POST.get("chapter") or None

        lesson.title = request.POST.get("title", "").strip()
        lesson.content = request.POST.get("content", "").strip()

        # ORDER
        order_val = request.POST.get("order")
        if order_val:
            try:
                lesson.order = int(order_val)
            except ValueError:
                pass

        # ✅ checkbox fix
        lesson.is_published = "is_published" in request.POST
        lesson.allow_students_view = "allow_students_view" in request.POST

        if not lesson.title:
            messages.error(request, "Lesson title is required.")
            return render(
                request,
                "courses/lesson_edit.html",
                {"course": course, "lesson": lesson, "chapters": chapters},
            )

        lesson.save()

        messages.success(request, "Lesson updated successfully.")
        return redirect("courses:course_dashboard", course_id=course.id)

    return render(
        request,
        "courses/lesson_edit.html",
        {"course": course, "lesson": lesson, "chapters": chapters},
    )
            
@login_required
@transaction.atomic
def lesson_detail(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)

    # course-level gate
    if not request.user.is_staff:
        access = CourseAccess.objects.filter(
            course=course,
            user=request.user,
            can_view=True,
            lessons_can_view=True
        ).exists()

        if not (course.is_published and course.allow_students_view and access):
            messages.error(request, "This course is not available yet.")
            return redirect("courses:course_list")

    lesson = get_object_or_404(Lesson, id=lesson_id, course=course, is_published=True)

    # ✅ lesson-level gate (content lock)
    if not request.user.is_staff and not lesson.allow_students_view:
        messages.error(request, "This lesson is not available yet.")
        return redirect("courses:course_dashboard", course_id=course.id)

    if request.method == "POST":
        LessonCompletion.objects.get_or_create(user=request.user, lesson=lesson)
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
        is_published = ("is_published" in request.POST)

        # ✅ PRICE
        price_raw = (request.POST.get("price") or "0").strip()
        try:
            price = Decimal(price_raw)
        except (InvalidOperation, ValueError):
            messages.error(request, "Invalid price value.")
            return render(request, "courses/course_create.html", {"subjects": subjects})

        if not subject_id or not title:
            messages.error(request, "Subject and Title are required.")
            return render(request, "courses/course_create.html", {"subjects": subjects})

        course = Course.objects.create(
            subject_id=subject_id,
            title=title,
            overview=overview,
            price=price,  # ✅ SAVE
            is_published=is_published,
            allow_students_view=False,
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