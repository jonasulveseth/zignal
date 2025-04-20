"""
URL configuration for zignal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('chat/', views.chat, name='chat'),
    
    # Test view
    path('test/', views.test_view, name='test_view'),
    path('test-base/', views.test_base_view, name='test_base_view'),
    
    # django-allauth URLs - main authentication system
    path('accounts/', include('allauth.urls')),
    
    # Custom signup view for debugging
    path('accounts/custom-signup/', views.custom_signup, name='custom_signup'),
    
    # Test template for debugging
    path('test-template/', views.test_template, name='test_template'),
    
    # Redirects from old auth routes to allauth
    path('login/', RedirectView.as_view(url='/accounts/login/', permanent=True), name='login_redirect'),
    path('signup/', RedirectView.as_view(url='/accounts/signup/', permanent=True), name='signup_redirect'),
    path('logout/', RedirectView.as_view(url='/accounts/logout/', permanent=True), name='logout_redirect'),
    path('password_reset/', RedirectView.as_view(url='/accounts/password/reset/', permanent=True), name='password_reset_redirect'),
    
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', include('invitations.urls')),
    path('', include('agents.urls')),
    path('', include('profiles.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
