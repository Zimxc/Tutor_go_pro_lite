from django.urls import path
from . import views

app_name = 'tutors'
urlpatterns = [
    path('', views.catalog, name='catalog'),
    path('mine/', views.my_tutors, name='mine'),
    path('profile/edit/', views.edit_profile, name='edit'),
    path('subjects/', views.subjects, name='subjects'),
    path('subjects/<int:pk>/edit/', views.subjects, name='subject_edit'),
    path('subjects/<int:pk>/delete/', views.delete_subject, name='subject_delete'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/subscription/', views.subscription, name='subscription'),
]
