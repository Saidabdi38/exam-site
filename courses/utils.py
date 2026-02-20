from .models import Lesson, LessonCompletion

def course_progress(user, course):
    lessons = Lesson.objects.filter(course=course, is_published=True)
    total = lessons.count()
    done = LessonCompletion.objects.filter(user=user, lesson__in=lessons).count()
    percent = int((done/total)*100) if total else 0
    return {"total":total,"done":done,"percent":percent}

def get_next_lesson(user, course):
    lessons = Lesson.objects.filter(course=course).order_by("order","id")
    completed = set(LessonCompletion.objects.filter(user=user,lesson__course=course)
                    .values_list("lesson_id",flat=True))
    for l in lessons:
        if l.id not in completed:
            return l
    return lessons.last()
