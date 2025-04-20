from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Profile
from .serializers import ProfileUpdateSerializer

@login_required
def profile_view(request):
    """View the current user's profile"""
    profile = request.user.profile
    
    context = {
        'profile': profile,
    }
    
    return render(request, 'profiles/profile_view.html', context)

@login_required
def profile_edit(request):
    """Edit the current user's profile"""
    profile = request.user.profile
    user = request.user
    
    if request.method == 'POST':
        # Handle user data updates
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # Update user data
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        user.save()
        
        # Handle profile data updates
        bio = request.POST.get('bio')
        position = request.POST.get('position')
        phone_number = request.POST.get('phone_number')
        linkedin_url = request.POST.get('linkedin_url')
        twitter_url = request.POST.get('twitter_url')
        github_url = request.POST.get('github_url')
        website_url = request.POST.get('website_url')
        
        # Update email notifications preference if checkbox is present
        email_notifications = 'email_notifications' in request.POST
        
        # Update dark mode preference if checkbox is present
        dark_mode = 'dark_mode' in request.POST
        
        # Update profile data
        profile.bio = bio
        profile.position = position
        profile.phone_number = phone_number
        profile.linkedin_url = linkedin_url
        profile.twitter_url = twitter_url
        profile.github_url = github_url
        profile.website_url = website_url
        profile.email_notifications = email_notifications
        profile.dark_mode = dark_mode
        
        # Handle profile image upload
        if 'profile_image' in request.FILES:
            profile.profile_image = request.FILES['profile_image']
        
        profile.save()
        
        messages.success(request, "Profile updated successfully")
        return redirect('profile_view')
    
    context = {
        'profile': profile,
        'user': user,
    }
    
    return render(request, 'profiles/profile_edit.html', context)

@login_required
def settings_view(request):
    """View for user settings"""
    profile = request.user.profile
    
    context = {
        'profile': profile,
    }
    
    return render(request, 'profiles/settings.html', context)

@login_required
@require_POST
def toggle_dark_mode(request):
    """Toggle dark mode setting via AJAX"""
    profile = request.user.profile
    profile.dark_mode = not profile.dark_mode
    profile.save()
    
    return JsonResponse({'success': True, 'dark_mode': profile.dark_mode})

@login_required
@require_POST
def toggle_notifications(request):
    """Toggle email notifications setting via AJAX"""
    profile = request.user.profile
    profile.email_notifications = not profile.email_notifications
    profile.save()
    
    return JsonResponse({'success': True, 'email_notifications': profile.email_notifications})
