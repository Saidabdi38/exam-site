from django.apps import apps
from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def create_teachers_group(sender, **kwargs):
    """Ensure the 'Teachers' group exists after migrations.

    This makes the Teacher Dashboard usable immediately without manually creating
    the group in Admin.
    """
    # Only run when OUR app migrates
    if sender and getattr(sender, "label", "") != "exams":
        return
    Group.objects.get_or_create(name="Teachers")
