from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.decorators import handle_database_conflicts, role_required
from accounts.models import User
from tutors.models import TutorProfile
from .forms import BookingForm, HomeworkForm, MeetingForm, SlotForm
from .models import AvailabilitySlot, Homework, Lesson


def participant_lessons(user):
    return Lesson.objects.filter(Q(student__user=user) | Q(tutor__user=user)).select_related(
        'student__user', 'tutor__user', 'subject', 'slot', 'homework')


@role_required(User.Role.TUTOR)
@handle_database_conflicts('lessons:schedule')
def schedule(request):
    tutor = request.user.tutor_profile
    form = SlotForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            slot, created = AvailabilitySlot.objects.get_or_create(tutor=tutor, start_time=form.cleaned_data['start_time'])
            if not created and slot.is_listed:
                form.add_error('start_time', 'Такий час уже є в розкладі.')
            else:
                if not slot.is_listed:
                    slot.is_listed = True
                    slot.save(update_fields=['is_listed'])
                messages.success(request, 'Вільний час додано.')
                return redirect('lessons:schedule')
    slots = tutor.slots.filter(is_listed=True).annotate(active_count=Count('lessons', filter=Q(lessons__status__in=[Lesson.Status.PENDING, Lesson.Status.CONFIRMED])))
    return render(request, 'lessons/schedule.html', {'form': form, 'slots': slots, 'now': timezone.now()})


@role_required(User.Role.TUTOR)
@require_POST
@handle_database_conflicts('lessons:schedule')
def delete_slot(request, pk):
    with transaction.atomic():
        slot = get_object_or_404(AvailabilitySlot, pk=pk, tutor=request.user.tutor_profile, is_listed=True)
        if slot.lessons.filter(status__in=[Lesson.Status.PENDING, Lesson.Status.CONFIRMED]).exists():
            messages.error(request, 'Не можна видалити час з активною заявкою або підтвердженим уроком.')
        else:
            slot.is_listed = False
            slot.save(update_fields=['is_listed'])
            messages.success(request, 'Вільний час видалено з розкладу.')
    return redirect('lessons:schedule')


@role_required(User.Role.STUDENT)
@require_POST
@handle_database_conflicts('tutors:catalog')
def book(request, tutor_pk):
    # IMMEDIATE отримує право запису до читання, а UNIQUE запобігає дублюванню записів.
    with transaction.atomic():
        tutor = get_object_or_404(TutorProfile, pk=tutor_pk, user__is_active=True, user__role=User.Role.TUTOR)
        form = BookingForm(request.POST, tutor=tutor, student=request.user.student_profile)
        if form.is_valid():
            slot = form.cleaned_data['slot']
            if slot.start_time <= timezone.now():
                messages.error(request, 'Цей час уже минув. Оберіть інший слот.')
                return redirect(tutor)
            offering = form.cleaned_data['offering']
            lesson = Lesson.objects.create(student=request.user.student_profile, tutor=tutor,
                subject=offering.subject, slot=slot, start_time=slot.start_time,
                price=offering.price, status=Lesson.Status.PENDING)
        else:
            messages.error(request, 'Не вдалося записатися. Перевірте предмет і час: слот уже зайнятий або у вас є інше заняття на цю годину.')
            return redirect(tutor)
    messages.success(request, 'Заявку надіслано. Викладач підтвердить заняття у своєму кабінеті.')
    return redirect('lessons:detail', pk=lesson.pk)


@login_required
def lesson_list(request):
    lessons = participant_lessons(request.user)
    tab = request.GET.get('tab', 'all')
    if tab in ['pending', 'confirmed']:
        lessons = lessons.filter(status=tab)
    elif tab == 'past':
        lessons = lessons.filter(Q(status=Lesson.Status.COMPLETED) | Q(slot__start_time__lte=timezone.now() - timedelta(hours=1))).exclude(status__in=[Lesson.Status.CANCELLED, Lesson.Status.REJECTED])
    elif tab == 'cancelled':
        lessons = lessons.filter(status__in=[Lesson.Status.CANCELLED, Lesson.Status.REJECTED])
    page = Paginator(lessons.order_by('-slot__start_time', '-pk'), 15).get_page(request.GET.get('page'))
    return render(request, 'lessons/list.html', {'page_obj': page, 'tab': tab})


@login_required
def detail(request, pk):
    lesson = get_object_or_404(participant_lessons(request.user), pk=pk)
    return render(request, 'lessons/detail.html', {'lesson': lesson, 'is_tutor': lesson.tutor.user_id == request.user.pk, 'homework': getattr(lesson, 'homework', None)})


@login_required
@require_POST
@handle_database_conflicts('lessons:list')
def change_status(request, pk):
    with transaction.atomic():
        lesson = get_object_or_404(participant_lessons(request.user), pk=pk)
        action = request.POST.get('action')
        is_tutor = lesson.tutor.user_id == request.user.pk
        if action in ['confirm', 'reject', 'complete'] and not is_tutor:
            raise PermissionDenied('Лише викладач може виконати цю дію.')
        new_status = None
        if action == 'cancel' and lesson.is_active:
            new_status = Lesson.Status.CANCELLED
        elif action == 'confirm' and lesson.status == Lesson.Status.PENDING:
            if lesson.slot.start_time <= timezone.now():
                messages.error(request, 'Не можна підтвердити заняття в минулому. Відхиліть або скасуйте заявку.')
            else:
                new_status = Lesson.Status.CONFIRMED
        elif action == 'reject' and lesson.status == Lesson.Status.PENDING:
            new_status = Lesson.Status.REJECTED
        elif action == 'complete' and lesson.can_complete:
            new_status = Lesson.Status.COMPLETED
        else:
            messages.error(request, 'Цей перехід статусу недоступний. Завершити урок можна після закінчення його години.')
        if new_status:
            # Умовний UPDATE не перезапише вже змінений статус.
            changed = Lesson.objects.filter(pk=lesson.pk, status=lesson.status).update(status=new_status)
            if changed:
                messages.success(request, f'Статус заняття: {Lesson.Status(new_status).label.lower()}.')
            else:
                messages.error(request, 'Статус уже змінився. Оновіть сторінку.')
    return redirect('lessons:detail', pk=pk)


@role_required(User.Role.TUTOR)
@handle_database_conflicts('lessons:list')
def meeting(request, pk):
    with transaction.atomic():
        lesson = get_object_or_404(Lesson, pk=pk, tutor=request.user.tutor_profile, status__in=[Lesson.Status.CONFIRMED, Lesson.Status.COMPLETED])
        form = MeetingForm(request.POST if request.method == 'POST' else None, instance=lesson)
        if request.method == 'POST' and form.is_valid():
            form.save()
            messages.success(request, 'Посилання збережено. Воно доступне лише вам і учневі цього заняття.')
            return redirect('lessons:detail', pk=pk)
    return render(request, 'form.html', {'form': form, 'title': 'Посилання на заняття', 'subtitle': str(lesson), 'back_url': 'lessons:list'})


@role_required(User.Role.TUTOR)
@handle_database_conflicts('lessons:list')
def homework_edit(request, pk):
    with transaction.atomic():
        lesson = get_object_or_404(Lesson, pk=pk, tutor=request.user.tutor_profile, status__in=[Lesson.Status.CONFIRMED, Lesson.Status.COMPLETED])
        homework = Homework.objects.filter(lesson=lesson).first()
        form = HomeworkForm(request.POST if request.method == 'POST' else None, instance=homework)
        if request.method == 'POST' and form.is_valid():
            homework = form.save(commit=False)
            homework.lesson = lesson
            homework.save()
            messages.success(request, 'Домашнє завдання збережено.')
            return redirect('lessons:detail', pk=pk)
    return render(request, 'form.html', {'form': form, 'title': 'Домашнє завдання', 'subtitle': str(lesson), 'back_url': 'lessons:list'})


@role_required(User.Role.TUTOR)
@require_POST
@handle_database_conflicts('lessons:list')
def homework_delete(request, pk):
    with transaction.atomic():
        homework = get_object_or_404(Homework, lesson_id=pk, lesson__tutor=request.user.tutor_profile)
        homework.delete()
    messages.success(request, 'Домашнє завдання видалено.')
    return redirect('lessons:detail', pk=pk)


@login_required
def homework_list(request):
    homework = Homework.objects.filter(lesson__in=participant_lessons(request.user)).select_related('lesson__subject', 'lesson__slot', 'lesson__tutor__user', 'lesson__student__user')
    page = Paginator(homework, 15).get_page(request.GET.get('page'))
    return render(request, 'lessons/homework_list.html', {'page_obj': page})
