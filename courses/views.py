from django.contrib.auth.decorators import login_required
from django.shortcuts import render,get_object_or_404,redirect
from django.contrib import messages
from django.db import transaction
from .models import Course,Lesson,LessonCompletion,LessonQuizAttempt,LessonQuizAnswer,LessonQuizChoice
from .utils import course_progress,get_next_lesson

@login_required
def course_list(request):
    courses = Course.objects.filter(is_published=True)
    return render(request,"courses/course_list.html",{"courses":courses})

@login_required
def course_dashboard(request,course_id):
    course = get_object_or_404(Course,id=course_id)
    lessons = Lesson.objects.filter(course=course).order_by("order")
    completed = set(LessonCompletion.objects.filter(user=request.user,lesson__course=course)
                    .values_list("lesson_id",flat=True))
    rows=[{"lesson":l,"done":l.id in completed} for l in lessons]
    prog=course_progress(request.user,course)
    nxt=get_next_lesson(request.user,course)
    return render(request,"courses/course_dashboard.html",
                  {"course":course,"rows":rows,"progress":prog,"next_lesson":nxt})

@login_required
@transaction.atomic
def lesson_detail(request,course_id,lesson_id):
    course=get_object_or_404(Course,id=course_id)
    lesson=get_object_or_404(Lesson,id=lesson_id,course=course)
    if request.method=="POST":
        LessonCompletion.objects.get_or_create(user=request.user,lesson=lesson)
        if hasattr(lesson,"quiz"):
            return redirect("courses:lesson_quiz",course_id=course.id,lesson_id=lesson.id)
        messages.success(request,"Lesson completed")
        return redirect("courses:course_dashboard",course_id=course.id)
    return render(request,"courses/lesson_detail.html",{"course":course,"lesson":lesson})

@login_required
def lesson_quiz(request,course_id,lesson_id):
    course=get_object_or_404(Course,id=course_id)
    lesson=get_object_or_404(Lesson,id=lesson_id,course=course)
    quiz=lesson.quiz
    questions=list(quiz.questions.prefetch_related("choices"))
    attempt=LessonQuizAttempt.objects.create(user=request.user,quiz=quiz)
    if request.method=="POST":
        correct=0
        for q in questions:
            cid=request.POST.get(f"q_{q.id}")
            if cid:
                choice=LessonQuizChoice.objects.get(id=cid)
                LessonQuizAnswer.objects.create(attempt=attempt,question=q,selected_choice=choice)
                if choice.is_correct:
                    correct+=1
        attempt.score=correct
        attempt.max_score=len(questions)
        attempt.passed=correct>=len(questions)*quiz.pass_percent/100
        attempt.save()
        return redirect("courses:course_dashboard",course_id=course.id)
    return render(request,"courses/lesson_quiz.html",
                  {"course":course,"lesson":lesson,"questions":questions})
