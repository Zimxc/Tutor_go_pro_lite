from django import forms
from django.utils import timezone
from .models import AvailabilitySlot, Homework, Lesson
from tutors.models import TutorSubject


class SlotForm(forms.Form):
    start_time = forms.DateTimeField(
        label='Дата й час (Київ)',
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local', 'step': 3600}),
        help_text='Лише початок години, наприклад 15:00. Тривалість — 60 хвилин.',
    )

    def clean_start_time(self):
        start_time = self.cleaned_data['start_time']
        if start_time <= timezone.now():
            raise forms.ValidationError('Оберіть час у майбутньому.')
        if start_time.minute or start_time.second or start_time.microsecond:
            raise forms.ValidationError('Заняття починаються рівно на початку години.')
        return start_time


class BookingForm(forms.Form):
    offering = forms.ModelChoiceField(queryset=TutorSubject.objects.none(), label='Предмет і вартість', empty_label=None)
    slot = forms.ModelChoiceField(queryset=AvailabilitySlot.objects.none(), widget=forms.HiddenInput)

    def __init__(self, *args, tutor, student, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['offering'].queryset = tutor.offerings.select_related('subject', 'tutor__user')
        busy_times = student.lessons.filter(
            status__in=[Lesson.Status.PENDING, Lesson.Status.CONFIRMED],
        ).values_list('start_time', flat=True)
        self.fields['slot'].queryset = tutor.slots.filter(
            is_listed=True, start_time__gt=timezone.now(),
        ).exclude(
            lessons__status__in=[Lesson.Status.PENDING, Lesson.Status.CONFIRMED],
        ).exclude(start_time__in=busy_times)


class MeetingForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ('meeting_url',)
        widgets = {'meeting_url': forms.URLInput(attrs={'placeholder': 'https://meet.google.com/…'})}


class HomeworkForm(forms.ModelForm):
    class Meta:
        model = Homework
        fields = ('title', 'description', 'due_date')
        widgets = {'description': forms.Textarea(attrs={'rows': 7}), 'due_date': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})}
