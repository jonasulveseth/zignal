from django.urls import path
from . import views

urlpatterns = [
    path('invitations/', views.invitation_list, name='invitation_list'),
    path('invitations/<uuid:uuid>/', views.invitation_detail, name='invitation_detail'),
    path('invitations/<uuid:uuid>/accept/', views.invitation_accept, name='invitation_accept'),
    path('invitations/<uuid:uuid>/decline/', views.invitation_decline, name='invitation_decline'),
    path('invitations/<uuid:uuid>/cancel/', views.invitation_cancel, name='invitation_cancel'),
    path('invitations/<uuid:uuid>/resend/', views.resend_invitation, name='resend_invitation'),
    path('companies/<int:company_id>/invite/', views.create_company_invitation, name='create_company_invitation'),
    path('projects/<int:project_id>/invite/', views.create_project_invitation, name='create_project_invitation'),
] 