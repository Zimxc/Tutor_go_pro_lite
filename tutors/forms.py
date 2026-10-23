from io import BytesIO
from uuid import uuid4
from PIL import Image, ImageOps
from django import forms
from django.core.files.base import ContentFile
from .models import Subject, TutorProfile, TutorSubject


class TutorProfileForm(forms.ModelForm):
    class Meta:
        model = TutorProfile
        fields = ('photo', 'short_description', 'description')
        widgets = {'description': forms.Textarea(attrs={'rows': 6})}

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo or not hasattr(photo, 'content_type'):
            return photo
        if photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Максимальний розмір фотографії — 5 МБ.')
        try:
            image = Image.open(photo)
            if image.format not in ('JPEG', 'PNG', 'WEBP'):
                raise forms.ValidationError('Завантажте фотографію JPEG, PNG або WebP.')
            if image.width * image.height > 16_000_000:
                raise forms.ValidationError('Роздільність фотографії має бути не більшою за 16 мегапікселів.')
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.thumbnail((1200, 1200))
            output = BytesIO()
            image.save(output, format='JPEG', quality=88)
        except (OSError, ValueError, Image.DecompressionBombError):
            raise forms.ValidationError('Не вдалося прочитати фотографію.')
        # Повторне кодування видаляє метадані, довільні імена та вбудований вміст.
        return ContentFile(output.getvalue(), name=f'{uuid4().hex}.jpg')


class TutorSubjectForm(forms.ModelForm):
    class Meta:
        model = TutorSubject
        fields = ('subject', 'price')

    def __init__(self, *args, tutor, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.tutor = tutor
        if self.instance.pk:
            self.fields['subject'].disabled = True
        else:
            self.fields['subject'].queryset = Subject.objects.exclude(offerings__tutor=tutor)
