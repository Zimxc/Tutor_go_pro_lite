from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounts.decorators import handle_database_conflicts, role_required
from accounts.models import User
from lessons.models import Lesson
from .forms import TutorProfileForm, TutorSubjectForm
from .models import Subject, Subscription, TutorProfile, TutorSubject


def tutor_queryset():
    return TutorProfile.objects.filter(user__is_active=True, user__role=User.Role.TUTOR).select_related('user').prefetch_related('offerings__subject')


def home(request):
    return render(request, 'home.html', {'featured': tutor_queryset()[:3], 'subjects': Subject.objects.all()[:6]})


def catalog(request):
    tutors = tutor_queryset()
    query = request.GET.get('q', '').strip()[:150]
    subject = request.GET.get('subject', '')
    if query:
        # Кожен фрагмент запиту може збігатися з ім’ям, прізвищем або предметом.
        for word in query.split():
            tutors = tutors.filter(Q(user__first_name__icontains=word) | Q(user__last_name__icontains=word) | Q(offerings__subject__name__icontains=word))
    if subject.isascii() and subject.isdecimal() and len(subject) <= 18:
        tutors = tutors.filter(offerings__subject_id=subject)
    page = Paginator(tutors.distinct(), 9).get_page(request.GET.get('page'))
    return render(request, 'tutors/catalog.html', {'page_obj': page, 'subjects': Subject.objects.all(), 'query': query, 'selected_subject': subject})


def detail(request, pk):
    tutor = get_object_or_404(tutor_queryset(), pk=pk)
    slots = tutor.slots.filter(is_listed=True, start_time__gt=timezone.now()).exclude(lessons__status__in=[Lesson.Status.PENDING, Lesson.Status.CONFIRMED])
    own_lessons = Lesson.objects.none()
    subscribed = False
    if request.user.is_authenticated and request.user.role == User.Role.STUDENT:
        student = request.user.student_profile
        subscribed = Subscription.objects.filter(student=student, tutor=tutor).exists()
        own_lessons = student.lessons.filter(tutor=tutor).select_related('subject', 'slot')
        busy_times = student.lessons.filter(
            status__in=[Lesson.Status.PENDING, Lesson.Status.CONFIRMED],
        ).values_list('start_time', flat=True)
        slots = slots.exclude(start_time__in=busy_times)
    return render(request, 'tutors/detail.html', {
        'tutor': tutor, 'slots': slots, 'subscribed': subscribed,
        'own_lessons': own_lessons,
    })


@role_required(User.Role.STUDENT)
@require_POST
@handle_database_conflicts('tutors:mine')
def subscription(request, pk):
    tutor = get_object_or_404(tutor_queryset(), pk=pk)
    with transaction.atomic():
        if request.POST.get('action') == 'subscribe':
            Subscription.objects.get_or_create(student=request.user.student_profile, tutor=tutor)
            messages.success(request, 'Викладача додано до ваших підписок.')
        elif request.POST.get('action') == 'unsubscribe':
            Subscription.objects.filter(student=request.user.student_profile, tutor=tutor).delete()
            messages.success(request, 'Підписку видалено. Ваші заняття збережено.')
        else:
            messages.error(request, 'Невідома дія.')
    return redirect(tutor)


@role_required(User.Role.STUDENT)
def my_tutors(request):
    student = request.user.student_profile
    tutors = tutor_queryset().filter(subscriptions__student=student)
    # Для невеликого навчального списку звичайний запит у циклі зрозуміліший за Prefetch.
    for tutor in tutors:
        tutor.next_lesson = tutor.lessons.filter(
            student=student,
            status=Lesson.Status.CONFIRMED,
            slot__start_time__gte=timezone.now(),
        ).select_related('slot', 'subject').first()
    return render(request, 'tutors/mine.html', {'tutors': tutors})


@role_required(User.Role.TUTOR)
@handle_database_conflicts('tutors:edit')
def edit_profile(request):
    form = TutorProfileForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=request.user.tutor_profile)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
        messages.success(request, 'Профіль викладача оновлено.')
        return redirect('tutors:edit')
    return render(request, 'tutors/edit.html', {'form': form, 'tutor': request.user.tutor_profile})


@role_required(User.Role.TUTOR)
@handle_database_conflicts('tutors:subjects')
def subjects(request, pk=None):
    tutor = request.user.tutor_profile
    offering = get_object_or_404(TutorSubject, pk=pk, tutor=tutor) if pk else None
    form = TutorSubjectForm(request.POST if request.method == 'POST' else None, instance=offering, tutor=tutor)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
        messages.success(request, 'Предмет і вартість збережено.')
        return redirect('tutors:subjects')
    return render(request, 'tutors/subjects.html', {'form': form, 'offerings': tutor.offerings.select_related('subject'), 'editing': offering})


@role_required(User.Role.TUTOR)
@require_POST
@handle_database_conflicts('tutors:subjects')
def delete_subject(request, pk):
    with transaction.atomic():
        offering = get_object_or_404(TutorSubject, pk=pk, tutor=request.user.tutor_profile)
        offering.delete()
    messages.success(request, 'Предмет видалено з профілю. Вартість наявних занять збережено.')
    return redirect('tutors:subjects')
