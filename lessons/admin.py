from django.contrib import admin
from .models import AvailabilitySlot, Homework, Lesson


class ReadOnlyAdmin(admin.ModelAdmin):
    """Статуси змінюються через особистий кабінет; панель адміністратора допомагає переглядати дані."""
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Lesson)
class LessonAdmin(ReadOnlyAdmin):
    list_display = ('id', 'student', 'tutor', 'subject', 'status', 'price')
    list_filter = ('status', 'subject')
    list_select_related = ('student__user', 'tutor__user', 'subject')


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(ReadOnlyAdmin):
    list_display = ('tutor', 'start_time', 'is_listed')
    list_filter = ('is_listed',)


@admin.register(Homework)
class HomeworkAdmin(ReadOnlyAdmin):
    list_display = ('title', 'lesson', 'due_date')
