from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db import IntegrityError, OperationalError
from django.shortcuts import redirect


def role_required(role):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.user.role != role:
                raise PermissionDenied('Ця дія недоступна для вашого типу облікового запису.')
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def handle_database_conflicts(redirect_to):
    """Исключение ловится после выхода из atomic(), когда транзакция уже откатилась."""
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            try:
                return view(request, *args, **kwargs)
            except IntegrityError:
                messages.error(request, 'Зміни не збережено: дані вже змінилися або такий запис існує. Оновіть сторінку й повторіть дію.')
            except OperationalError as error:
                if 'locked' not in str(error).lower() and 'busy' not in str(error).lower():
                    raise
                messages.error(request, 'База даних зайнята іншим запитом. Зміни не збережено; спробуйте ще раз.')
            return redirect(redirect_to)
        return wrapped
    return decorator
