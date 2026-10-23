from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models, transaction
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Укажіть email.')
        with transaction.atomic(using=self._db):
            user = self.model(email=email.strip().lower(), **extra_fields)
            user.set_password(password)
            user.full_clean(exclude=['password'])
            user.save(using=self._db)
            user.create_profile()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'student')
        if extra_fields['is_staff'] is not True or extra_fields['is_superuser'] is not True:
            raise ValueError('Адміністратор повинен мати is_staff=True та is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Учень'
        TUTOR = 'tutor', 'Викладач'

    username = None
    email = models.EmailField('Email', unique=True)
    role = models.CharField('Тип облікового запису', max_length=7, choices=Role.choices)
    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'Користувач'
        verbose_name_plural = 'Користувачі'
        constraints = [
            models.UniqueConstraint(Lower('email'), name='user_email_case_insensitive'),
            models.CheckConstraint(condition=models.Q(role__in=['student', 'tutor']), name='user_valid_role'),
        ]

    def clean(self):
        super().clean()
        self.email = self.email.strip().lower()

    def create_profile(self):
        # Викликається під час реєстрації або створення адміністратором у тій самій транзакції.
        if self.role == self.Role.STUDENT:
            StudentProfile.objects.get_or_create(user=self)
        else:
            from tutors.models import TutorProfile
            TutorProfile.objects.get_or_create(user=self)

    @property
    def display_name(self):
        return self.get_full_name() or self.email

    def __str__(self):
        return self.display_name


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile', verbose_name='Користувач')

    class Meta:
        verbose_name = 'Профіль учня'
        verbose_name_plural = 'Профілі учнів'

    def __str__(self):
        return self.user.display_name
