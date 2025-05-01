from django.urls import path
from . import views

app_name = 'companies'

urlpatterns = [
    path('companies/setup/', views.setup_company, name='setup_company'),
    path('companies/create/', views.create_company, name='create_company'),
    path('companies/', views.company_list, name='company_list'),
    path('companies/<int:company_id>/', views.company_detail, name='company_detail'),
    path('companies/setup-email/', views.setup_company_email, name='setup_company_email'),
    path('companies/team/', views.company_team, name='company_team'),
] 