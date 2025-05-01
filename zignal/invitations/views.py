from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import HttpResponseRedirect, Http404
from django.core.exceptions import PermissionDenied

from .models import Invitation
from companies.models import Company
from projects.models import Project
from zignal.config.permissions import company_role_required, project_role_required

@login_required
def invitation_list(request):
    """View for listing sent and received invitations"""
    # Get sent invitations
    sent_invitations = Invitation.objects.filter(invited_by=request.user).order_by('-created_at')
    
    # For received invitations, we need to check by email
    received_invitations = Invitation.objects.filter(
        email=request.user.email, 
        status='pending'
    ).order_by('-created_at')
    
    context = {
        'sent_invitations': sent_invitations,
        'received_invitations': received_invitations,
    }
    
    return render(request, 'invitations/invitation_list.html', context)

@login_required
def invitation_detail(request, uuid):
    """View an invitation's details"""
    invitation = get_object_or_404(Invitation, id=uuid)
    
    # Check permissions
    if invitation.invited_by != request.user and invitation.email != request.user.email:
        raise PermissionDenied("You don't have permission to view this invitation")
    
    # If the invitation is pending and expired, mark it as expired
    if invitation.status == 'pending' and invitation.is_expired():
        invitation.mark_as_expired()
    
    return render(request, 'invitations/invitation_detail.html', {'invitation': invitation})

@login_required
@company_role_required(['owner', 'admin'])
def create_company_invitation(request, company_id):
    """Create an invitation to join a company"""
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == 'POST':
        email = request.POST.get('email')
        role = request.POST.get('role')
        message = request.POST.get('message', '')
        
        # Simple validation
        if not email:
            messages.error(request, "Email is required")
            return redirect('companies:company_team')
        
        # Check if an invitation already exists
        existing_invitation = Invitation.objects.filter(
            email=email,
            company=company,
            status='pending'
        ).exists()
        
        if existing_invitation:
            messages.warning(request, "An invitation is already pending for this email")
            return redirect('companies:company_team')
        
        # Create the invitation
        invitation = Invitation.objects.create(
            email=email,
            invitation_type='company',
            company=company,
            role=role,
            message=message,
            invited_by=request.user
        )
        
        # Send the invitation email
        invitation.send_invitation_email(request)
        
        messages.success(request, f"Invitation sent to {email}")
        return redirect('companies:company_team')
    
    # GET request: show form
    return render(request, 'invitations/create_company_invitation.html', {'company': company})

@login_required
@project_role_required(['manager'])
def create_project_invitation(request, project_id):
    """Create an invitation to join a project"""
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        email = request.POST.get('email')
        role = request.POST.get('role')
        message = request.POST.get('message', '')
        
        # Simple validation
        if not email:
            messages.error(request, "Email is required")
            return redirect('projects:project_detail', project_id=project_id)
        
        # Check if an invitation already exists
        existing_invitation = Invitation.objects.filter(
            email=email,
            project=project,
            status='pending'
        ).exists()
        
        if existing_invitation:
            messages.warning(request, "An invitation is already pending for this email")
            return redirect('projects:project_detail', project_id=project_id)
        
        # Create the invitation
        invitation = Invitation.objects.create(
            email=email,
            invitation_type='project',
            project=project,
            role=role,
            message=message,
            invited_by=request.user
        )
        
        # Send the invitation email
        invitation.send_invitation_email(request)
        
        messages.success(request, f"Invitation sent to {email}")
        return redirect('projects:project_detail', project_id=project_id)
    
    # GET request: show form
    return render(request, 'invitations/create_project_invitation.html', {'project': project})

@login_required
def invitation_accept(request, uuid):
    """Accept an invitation"""
    invitation = get_object_or_404(Invitation, id=uuid)
    
    # Check if the invitation is for the current user
    if invitation.email != request.user.email:
        messages.error(request, "This invitation is not for you")
        return redirect('dashboard')
    
    # Check if the invitation is still valid
    if invitation.status != 'pending':
        messages.error(request, f"This invitation is {invitation.status}")
        return redirect('dashboard')
    
    if invitation.is_expired():
        invitation.mark_as_expired()
        messages.error(request, "This invitation has expired")
        return redirect('dashboard')
    
    # Accept the invitation
    success = invitation.accept(request.user)
    
    if success:
        messages.success(request, "Invitation accepted successfully")
        
        # Redirect based on invitation type
        if invitation.invitation_type == 'company':
            return redirect('company_detail', company_id=invitation.company.id)
        else:
            return redirect('project_detail', project_id=invitation.project.id)
    else:
        messages.error(request, "Failed to accept invitation")
        return redirect('dashboard')

@login_required
def invitation_decline(request, uuid):
    """Decline an invitation"""
    invitation = get_object_or_404(Invitation, id=uuid)
    
    # Check if the invitation is for the current user
    if invitation.email != request.user.email:
        messages.error(request, "This invitation is not for you")
        return redirect('dashboard')
    
    # Check if the invitation is still valid to decline
    if invitation.status != 'pending':
        messages.error(request, f"This invitation is already {invitation.status}")
        return redirect('dashboard')
    
    # Decline the invitation
    success = invitation.decline()
    
    if success:
        messages.success(request, "Invitation declined")
    else:
        messages.error(request, "Failed to decline invitation")
    
    return redirect('dashboard')

@login_required
@require_POST
def invitation_cancel(request, uuid):
    """Cancel a sent invitation (only the sender can do this)"""
    invitation = get_object_or_404(Invitation, id=uuid)
    
    # Only the sender can cancel
    if invitation.invited_by != request.user:
        raise PermissionDenied("You don't have permission to cancel this invitation")
    
    # Only pending invitations can be canceled
    if invitation.status != 'pending':
        messages.error(request, f"Cannot cancel a {invitation.status} invitation")
        return redirect('invitation_list')
    
    # Delete the invitation
    invitation.delete()
    
    messages.success(request, "Invitation canceled successfully")
    return redirect('invitation_list')

@login_required
def resend_invitation(request, uuid):
    """Resend an invitation email"""
    invitation = get_object_or_404(Invitation, id=uuid)
    
    # Only the sender can resend
    if invitation.invited_by != request.user:
        raise PermissionDenied("You don't have permission to resend this invitation")
    
    # Only pending invitations can be resent
    if invitation.status != 'pending':
        messages.error(request, f"Cannot resend a {invitation.status} invitation")
        return redirect('invitation_list')
    
    # Update expiration date
    invitation.expires_at = timezone.now() + timezone.timedelta(days=7)
    invitation.save(update_fields=['expires_at'])
    
    # Resend the email
    invitation.send_invitation_email(request)
    
    messages.success(request, f"Invitation resent to {invitation.email}")
    return redirect('invitation_list')
