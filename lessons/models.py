from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, URLValidator
from django.db import models
from django.utils import timezone


class AvailabilitySlot(models.Model):
    tutor = models.ForeignKey('tutors.TutorProfile', on_delete=models.CASCADE, related_name='slots', verbose_name='Викладач')
    start_time = models.DateTimeField('Початок заняття')
    # Приховуємо видалений вільний слот, зберігаючи історію скасованих занять.
    is_listed = models.BooleanField('Показувати в розкладі', default=True)

    class Meta:
        ordering = ['start_time']
        constraints = [models.UniqueConstraint(fields=['tutor', 'start_time'], name='unique_tutor_slot')]
        verbose_name = 'Часовий слот'
        verbose_name_plural = 'Часові слоти'

    @property
    def end_time(self):
        return self.start_time + timedelta(hours=1)

    def __str__(self):
        return f'{self.tutor} — {timezone.localtime(self.start_time):%d.%m.%Y %H:%M}'


class Lesson(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Очікує підтвердження'
        CONFIRMED = 'confirmed', 'Підтверджено'
        REJECTED = 'rejected', 'Відхилено'
        CANCELLED = 'cancelled', 'Скасовано'
        COMPLETED = 'completed', 'Завершено'

    student = models.ForeignKey('accounts.StudentProfile', on_delete=models.PROTECT, related_name='lessons', verbose_name='Учень')
    tutor = models.ForeignKey('tutors.TutorProfile', on_delete=models.PROTECT, related_name='lessons', verbose_name='Викладач')
    subject = models.ForeignKey('tutors.Subject', on_delete=models.PROTECT, related_name='lessons', verbose_name='Предмет')
    slot = models.ForeignKey(AvailabilitySlot, on_delete=models.PROTECT, related_name='lessons', verbose_name='Часовий слот')
    # Копія початку слота потрібна SQLite для перевірки унікальності пари «учень + година».
    start_time = models.DateTimeField('Початок заняття', editable=False)
    status = models.CharField('Статус', max_length=10, choices=Status.choices, default=Status.PENDING)
    price = models.DecimalField('Вартість під час запису, UAH', max_digits=9, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    meeting_url = models.URLField('Посилання на онлайн-заняття', max_length=500, blank=True, validators=[URLValidator(schemes=['https', 'http'])])
    created_at = models.DateTimeField('Дата створення', auto_now_add=True)

    class Meta:
        ordering = ['slot__start_time', 'pk']
        constraints = [
            models.UniqueConstraint(fields=['slot'], condition=models.Q(status__in=['pending', 'confirmed']), name='one_active_lesson_per_slot'),
            models.UniqueConstraint(fields=['student', 'start_time'], condition=models.Q(status__in=['pending', 'confirmed']), name='one_active_student_lesson_per_hour'),
            models.CheckConstraint(condition=models.Q(price__gt=0), name='lesson_positive_price'),
            models.CheckConstraint(condition=models.Q(status__in=['pending', 'confirmed', 'rejected', 'cancelled', 'completed']), name='lesson_valid_status'),
        ]
        verbose_name = 'Заняття'
        verbose_name_plural = 'Заняття'

    def clean(self):
        super().clean()
        if self.slot_id and self.tutor_id and self.slot.tutor_id != self.tutor_id:
            raise ValidationError('Слот належить іншому викладачеві.')
        if self.slot_id and self.start_time and self.start_time != self.slot.start_time:
            raise ValidationError('Початок заняття має збігатися з початком слота.')

    @property
    def is_active(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED)

    @property
    def can_complete(self):
        return self.status == self.Status.CONFIRMED and self.slot.end_time <= timezone.now()

    def __str__(self):
        return f'{self.subject}: {self.student} → {self.tutor}'


class Homework(models.Model):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name='homework', verbose_name='Заняття')
    title = models.CharField('Назва', max_length=200)
    description = models.TextField('Текст завдання')
    due_date = models.DateField('Термін виконання')
    created_at = models.DateTimeField('Дата створення', auto_now_add=True)

    class Meta:
        ordering = ['due_date', 'pk']
        verbose_name = 'Домашнє завдання'
        verbose_name_plural = 'Домашні завдання'

    def __str__(self):
        return self.title
