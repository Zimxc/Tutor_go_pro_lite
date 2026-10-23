from django.contrib import admin
from .forms import TutorProfileForm
from .models import Subject, Subscription, TutorProfile, TutorSubject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    search_fields = ('name',)


class TutorSubjectInline(admin.TabularInline):
    model = TutorSubject
    extra = 0


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    form = TutorProfileForm
    readonly_fields = ('user',)
    inlines = [TutorSubjectInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('student', 'tutor', 'created_at')
    readonly_fields = ('student', 'tutor', 'created_at')

    def has_add_permission(self, request):
        return False
