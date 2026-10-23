from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from .decorators import handle_database_conflicts
from .forms import AccountForm, RegistrationForm
from .models import User
from lessons.models import Lesson


@handle_database_conflicts('accounts:register')
def register(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = RegistrationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        # Пользователь и профиль появляются вместе или не появляются вовсе.
        with transaction.atomic():
            user = form.save()
            user.create_profile()
        login(request, user)
        messages.success(request, 'Вітаємо в TutorWise Lite Pro! Ваш обліковий запис створено.')
        return redirect('accounts:dashboard')
    return render(request, 'accounts/register.html', {'form': form})


@login_required
@handle_database_conflicts('accounts:edit')
def edit_account(request):
    form = AccountForm(request.POST if request.method == 'POST' else None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
        messages.success(request, 'Дані облікового запису оновлено.')
        return redirect('accounts:edit')
    return render(request, 'form.html', {'form': form, 'title': 'Дані облікового запису', 'subtitle': 'Ім’я та email для входу в TutorWise Lite Pro.', 'back_url': 'accounts:dashboard'})


@login_required
def dashboard(request):
    is_tutor = request.user.role == User.Role.TUTOR
    if is_tutor:
        profile = request.user.tutor_profile
    else:
        profile = request.user.student_profile
    lessons = profile.lessons.select_related('student__user', 'tutor__user', 'subject', 'slot')
    upcoming = lessons.filter(status=Lesson.Status.CONFIRMED, slot__start_time__gte=timezone.now())
    return render(request, 'accounts/dashboard.html', {
        'is_tutor': is_tutor, 'nearest': upcoming.first(),
        'pending_count': lessons.filter(status=Lesson.Status.PENDING).count(),
        'upcoming_count': upcoming.count(), 'extra_count': profile.subscriptions.count(),
    })
