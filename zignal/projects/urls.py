from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('projects/create/', views.create_project, name='create_project'),
    path('projects/test-create/', views.test_project_creation, name='test_project_creation'),
] 