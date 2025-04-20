from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Reports
    path('reports/', views.report_list, name='report_list'),
    path('reports/create/', views.report_create, name='report_create'),
    path('reports/<slug:slug>/', views.report_detail, name='report_detail'),
    path('reports/<slug:slug>/edit/', views.report_edit, name='report_edit'),
    path('reports/<slug:slug>/delete/', views.report_delete, name='report_delete'),
    path('reports/<slug:slug>/generate/', views.report_generate, name='report_generate'),
    path('reports/<slug:slug>/export-pdf/', views.report_export_pdf, name='report_export_pdf'),
    
    # Templates
    path('templates/', views.template_list, name='template_list'),
    
    # Schedules
    path('schedules/', views.schedule_list, name='schedule_list'),
] 