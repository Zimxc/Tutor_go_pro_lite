from datetime import datetime, time, timedelta
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from accounts.models import User
from lessons.models import AvailabilitySlot
from tutors.models import Subject, TutorSubject


class Command(BaseCommand):
    help = 'Додати каталог предметів; --with-users додає два демопрофілі та учня.'

    def add_arguments(self, parser):
        parser.add_argument('--with-users', action='store_true')
        parser.add_argument('--password', help='Пароль лише для нових демокористувачів. Інакше генерується випадковий.')

    @transaction.atomic
    def handle(self, *args, **options):
        subjects = {}
        for name in ['Математика', 'Англійська мова', 'Фізика', 'Хімія', 'Історія']:
            subjects[name], _ = Subject.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS('Каталог: 5 предметів. Наявні дані збережено.'))
        if not options['with_users']:
            return
        password = options['password'] or get_random_string(18)
        try:
            validate_password(password)
        except ValidationError as error:
            raise CommandError('; '.join(error.messages))
        people = [
            ('anna@tutorgo.example', 'Анна', 'Коваленко', User.Role.TUTOR,
             'Математика без страху й фізика з цікавістю.',
             'Пояснюю складні теми на зрозумілих прикладах. На заняттях розбираємося в причинах, ставимо запитання й багато практикуємося.',
             [('Математика', '400.00'), ('Фізика', '500.00')]),
            ('maria@tutorgo.example', 'Марія', 'Бондар', User.Role.TUTOR,
             'Допомагаю заговорити англійською й полюбити процес.',
             'На уроках спілкуємося, розбираємо корисну лексику й зміцнюємо впевненість. Добираю практику під ваші цілі й темп.',
             [('Англійська мова', '450.00')]),
            ('student@tutorgo.example', 'Олексій', 'Мельник', User.Role.STUDENT, '', '', []),
        ]
        created_emails = []
        for email, first, last, role, short, description, offerings in people:
            user = User.objects.filter(email=email).first()
            if user:
                self.stdout.write(f'{email}: уже існує, пропущено (пароль і дані не змінювалися).')
                continue
            user = User.objects.create_user(email=email, password=password, first_name=first, last_name=last, role=role)
            created_emails.append(email)
            if role == User.Role.TUTOR:
                tutor = user.tutor_profile
                tutor.short_description = short
                tutor.description = description
                tutor.save()
                for subject_name, price in offerings:
                    TutorSubject.objects.create(tutor=tutor, subject=subjects[subject_name], price=price)
                for offset in [1, 2, 3]:
                    day = timezone.localdate() + timedelta(days=offset)
                    for hour in [10, 14]:
                        start_time = timezone.make_aware(datetime.combine(day, time(hour=hour)))
                        AvailabilitySlot.objects.create(tutor=tutor, start_time=start_time)
        if created_emails:
            self.stdout.write(self.style.SUCCESS('Створено: ' + ', '.join(created_emails)))
            self.stdout.write(f'Пароль нових демооблікових записів (збережіть локально): {password}')
        self.stdout.write('Демооблікові записи не мають прав адміністратора. Повторний запуск не скидає дані.')
