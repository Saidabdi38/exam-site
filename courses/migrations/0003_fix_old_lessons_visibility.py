from django.db import migrations


def forwards(apps, schema_editor):
    Lesson = apps.get_model("courses", "Lesson")

    # ✅ Make ALL existing lessons visible
    Lesson.objects.filter(
        is_published=True
    ).update(
        allow_students_view=True
    )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0002_courseaccess_lessons_can_view"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]