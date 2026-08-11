from .models import Attempt, ExamResitPermission

def is_teacher(user):
    # Teacher if staff OR in Teachers group
    return user.is_authenticated and (
        user.is_staff or user.groups.filter(name="Teachers").exists()
    )

def allowed_attempts_for(user, exam):
    perm = ExamResitPermission.objects.filter(user=user, exam=exam).first()
    return perm.allowed_attempts if perm else 1

def used_attempts_for(user, exam):
    return Attempt.objects.filter(user=user, exam=exam, submitted_at__isnull=False).count()

def can_start_attempt(user, exam):
    return used_attempts_for(user, exam) < allowed_attempts_for(user, exam)
