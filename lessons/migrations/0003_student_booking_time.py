from django.db import migrations, models


def copy_slot_start(apps, schema_editor):
    Lesson = apps.get_model('lessons', 'Lesson')
    alias = schema_editor.connection.alias
    for lesson in Lesson.objects.using(alias).select_related('slot').iterator():
        lesson.start_time = lesson.slot.start_time
        lesson.save(using=alias, update_fields=['start_time'])


class Migration(migrations.Migration):
    dependencies = [('lessons', '0002_ukrainian_labels')]

    operations = [
        migrations.AddField(
            model_name='lesson', name='start_time',
            field=models.DateTimeField('Початок заняття', editable=False, null=True),
        ),
        migrations.RunPython(copy_slot_start, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='lesson', name='start_time',
            field=models.DateTimeField('Початок заняття', editable=False),
        ),
        migrations.AddConstraint(
            model_name='lesson',
            constraint=models.UniqueConstraint(
                fields=['student', 'start_time'],
                condition=models.Q(status__in=['pending', 'confirmed']),
                name='one_active_student_lesson_per_hour',
            ),
        ),
    ]
