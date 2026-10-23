from django.urls import path
from . import views

app_name = 'lessons'
urlpatterns = [
    path('', views.lesson_list, name='list'),
    path('schedule/', views.schedule, name='schedule'),
    path('schedule/<int:pk>/delete/', views.delete_slot, name='slot_delete'),
    path('book/<int:tutor_pk>/', views.book, name='book'),
    path('homework/', views.homework_list, name='homework_list'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/status/', views.change_status, name='status'),
    path('<int:pk>/meeting/', views.meeting, name='meeting'),
    path('<int:pk>/homework/', views.homework_edit, name='homework_edit'),
    path('<int:pk>/homework/delete/', views.homework_delete, name='homework_delete'),
]
