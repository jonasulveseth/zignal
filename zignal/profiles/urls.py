from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('settings/', views.settings_view, name='settings'),
    path('api/toggle-dark-mode/', views.toggle_dark_mode, name='toggle_dark_mode'),
    path('api/toggle-notifications/', views.toggle_notifications, name='toggle_notifications'),
] 