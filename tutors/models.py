from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class TutorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tutor_profile', verbose_name='Користувач')
    short_description = models.CharField('Коротко про себе', max_length=200, blank=True)
    description = models.TextField('Докладний опис', blank=True)
    photo = models.ImageField('Фотографія', upload_to='tutors/', blank=True)
    subjects = models.ManyToManyField('Subject', through='TutorSubject', related_name='tutors', verbose_name='Предмети')

    class Meta:
        verbose_name = 'Профіль викладача'
        verbose_name_plural = 'Профілі викладачів'
        ordering = ['user__first_name', 'user__last_name', 'pk']

    def __str__(self):
        return self.user.display_name

    def get_absolute_url(self):
        return reverse('tutors:detail', args=[self.pk])


class Subject(models.Model):
    name = models.CharField('Назва', max_length=100, unique=True)
    description = models.TextField('Опис', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предмети'

    def __str__(self):
        return self.name


class TutorSubject(models.Model):
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='offerings', verbose_name='Викладач')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='offerings', verbose_name='Предмет')
    price = models.DecimalField('Ціна, UAH', max_digits=9, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    duration = models.PositiveSmallIntegerField('Тривалість, хв.', default=60, editable=False)

    class Meta:
        ordering = ['subject__name']
        constraints = [
            models.UniqueConstraint(fields=['tutor', 'subject'], name='unique_tutor_subject'),
            models.CheckConstraint(condition=models.Q(price__gt=0), name='tutor_subject_positive_price'),
            models.CheckConstraint(condition=models.Q(duration=60), name='tutor_subject_duration_60'),
        ]
        verbose_name = 'Предмет викладача'
        verbose_name_plural = 'Предмети викладачів'

    def __str__(self):
        return f'{self.tutor}: {self.subject} — {self.price} UAH'


class Subscription(models.Model):
    student = models.ForeignKey('accounts.StudentProfile', on_delete=models.CASCADE, related_name='subscriptions', verbose_name='Учень')
    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name='subscriptions', verbose_name='Викладач')
    created_at = models.DateTimeField('Дата створення', auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['student', 'tutor'], name='unique_student_tutor_subscription')]
        verbose_name = 'Підписка'
        verbose_name_plural = 'Підписки'

    def __str__(self):
        return f'{self.student} → {self.tutor}'
