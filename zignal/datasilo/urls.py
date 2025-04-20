from django.urls import path
from . import views

app_name = 'datasilo'

urlpatterns = [
    path('silos/', views.data_silo_list, name='silo_list'),
    path('silos/create/', views.data_silo_create, name='silo_create'),
    path('silos/<slug:slug>/', views.data_silo_detail, name='silo_detail'),
    path('silos/<slug:slug>/upload/', views.file_upload, name='file_upload'),
    path('silos/<slug:slug>/edit/', views.data_silo_edit, name='silo_edit'),
    path('silos/<slug:slug>/delete/', views.data_silo_delete, name='silo_delete'),
    path('files/<int:file_id>/', views.file_detail, name='file_detail'),
    path('files/<int:file_id>/delete/', views.file_delete, name='file_delete'),
] 