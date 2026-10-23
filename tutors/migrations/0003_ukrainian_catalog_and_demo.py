from django.db import migrations


# Старі російські значення нижче потрібні лише для пошуку та перекладу давніх демоданих.
SUBJECT_NAMES = [
    ('Английский язык', 'Англійська мова'),
    ('Физика', 'Фізика'),
    ('Химия', 'Хімія'),
    ('История', 'Історія'),
]

DEMO_NAMES = [
    ('student@tutorgo.example', 'first_name', 'Алексей', 'Олексій'),
    ('maria@tutorgo.example', 'first_name', 'Мария', 'Марія'),
    ('maria@tutorgo.example', 'last_name', 'Бондарь', 'Бондар'),
    ('other@tutorgo.example', 'first_name', 'Ирина', 'Ірина'),
    ('other@tutorgo.example', 'last_name', 'Пример', 'Приклад'),
]

DEMO_PROFILES = [
    ('anna@tutorgo.example', 'short_description',
     'Математика без страха и физика с любопытством.',
     'Математика без страху й фізика з цікавістю.'),
    ('anna@tutorgo.example', 'description',
     'Объясняю сложные темы на понятных примерах. На занятиях разбираемся в причинах, задаём вопросы и много практикуемся.',
     'Пояснюю складні теми на зрозумілих прикладах. На заняттях розбираємося в причинах, ставимо запитання й багато практикуємося.'),
    ('maria@tutorgo.example', 'short_description',
     'Помогаю заговорить по-английски и полюбить процесс.',
     'Допомагаю заговорити англійською й полюбити процес.'),
    ('maria@tutorgo.example', 'description',
     'На уроках общаемся, разбираем полезную лексику и укрепляем уверенность. Подбираю практику под ваши цели и темп.',
     'На уроках спілкуємося, розбираємо корисну лексику й зміцнюємо впевненість. Добираю практику під ваші цілі й темп.'),
]

DEMO_HOMEWORK = [
    ('title', 'Практика: квадратные уравнения', 'Практика: квадратні рівняння'),
    ('description',
     'Повторите формулу дискриминанта. Решите уравнения: x² - 5x + 6 = 0 и 2x² - 8 = 0. Объясните каждый шаг решения.',
     'Повторіть формулу дискримінанта. Розв’яжіть рівняння: x² - 5x + 6 = 0 і 2x² - 8 = 0. Поясніть кожен крок розв’язання.'),
    ('description',
     'Повторите формулу дискриминанта. Решите x² - 5x + 6 = 0 и 2x² - 8 = 0. Объясните каждый шаг.',
     'Повторіть формулу дискримінанта. Розв’яжіть x² - 5x + 6 = 0 і 2x² - 8 = 0. Поясніть кожен крок.'),
]


def translate_content(apps, schema_editor, reverse=False):
    alias = schema_editor.connection.alias
    Subject = apps.get_model('tutors', 'Subject')
    User = apps.get_model('accounts', 'User')
    TutorProfile = apps.get_model('tutors', 'TutorProfile')
    Homework = apps.get_model('lessons', 'Homework')

    def pair(source, target):
        return (target, source) if reverse else (source, target)

    # Зберігаємо ID та зв’язки; не об’єднуємо предмети, якщо назви збігаються.
    for source, target in SUBJECT_NAMES:
        source, target = pair(source, target)
        if not Subject.objects.using(alias).filter(name=target).exists():
            Subject.objects.using(alias).filter(name=source).update(name=target)

    # Змінюємо лише відомі демозначення, які користувач ще не редагував.
    for email, field, source, target in DEMO_NAMES:
        source, target = pair(source, target)
        User.objects.using(alias).filter(email=email, **{field: source}).update(**{field: target})
    for email, field, source, target in DEMO_PROFILES:
        source, target = pair(source, target)
        TutorProfile.objects.using(alias).filter(user__email=email, **{field: source}).update(**{field: target})
    for field, source, target in DEMO_HOMEWORK:
        source, target = pair(source, target)
        Homework.objects.using(alias).filter(
            lesson__tutor__user__email='anna@tutorgo.example',
            lesson__student__user__email='student@tutorgo.example',
            **{field: source},
        ).update(**{field: target})


def forwards(apps, schema_editor):
    translate_content(apps, schema_editor)


def backwards(apps, schema_editor):
    translate_content(apps, schema_editor, reverse=True)


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_ukrainian_labels'),
        ('lessons', '0002_ukrainian_labels'),
        ('tutors', '0002_ukrainian_labels'),
    ]
    operations = [migrations.RunPython(forwards, backwards)]
