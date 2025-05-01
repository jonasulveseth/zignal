from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from .models import Company, UserCompanyRelation
from .forms import CompanyForm, CompanyEmailForm
from core.tasks import create_default_project_and_silo
from .services.openai_service import CompanyOpenAIService
import logging
from invitations.models import Invitation
import datetime

# Get logger
logger = logging.getLogger(__name__)

@login_required
def setup_company(request):
    """
    View for initial company setup after user registration.
    This is a required step for new users.
    """
    # Check if user already has a company
    has_company = False
    if hasattr(request.user, 'profile') and request.user.profile and hasattr(request.user.profile, 'company'):
        has_company = True
    
    if not has_company:
        # Check for company relations
        has_company = request.user.company_relations.exists()
    
    # If user already has a company, redirect to dashboard
    if has_company:
        messages.info(request, "You're already part of a company. You can create another one if needed.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            # Create the company
            company = form.save(commit=False)
            company.created_by = request.user
            company.save()
            logger.info(f"Created company: {company.name} (ID: {company.id})")
            
            # Create the relation between user and company
            UserCompanyRelation.objects.create(
                user=request.user,
                company=company,
                role='owner'  # Make the current user the owner
            )
            logger.info(f"Created user-company relation for user {request.user.email} and company {company.name}")
            
            # Set up OpenAI resources for the company
            logger.info(f"Setting up OpenAI resources for company {company.name}")
            openai_service = CompanyOpenAIService()
            result = openai_service.setup_company_ai(company)
            
            if result['success']:
                company.openai_assistant_id = result['assistant_id']
                company.openai_vector_store_id = result['vector_store_id']
                company.save()
                logger.info(f"Created and saved OpenAI resources for company: {company.name} - Assistant ID: {company.openai_assistant_id}, Vector Store ID: {company.openai_vector_store_id}")
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"Failed to create OpenAI resources for company: {company.name} (ID: {company.id}) - Error: {error_msg}")
                
                # Still proceed with company creation, but show error message
                if 'invalid_api_key' in error_msg or 'API key' in error_msg:
                    messages.error(request, "Company created, but AI assistant setup failed due to API key issues. Please contact support.")
                else:
                    messages.warning(request, "Company created, but AI assistant setup encountered an issue. Some AI features may not be available.")
            
            # Create default project and data silo in the background using Celery
            create_default_project_and_silo.delay(company.id, request.user.id)
            logger.info(f"Triggered default project and silo creation for company: {company.name} (ID: {company.id})")
            
            # Show success message
            messages.success(request, f'Company "{company.name}" has been set up successfully!')
            return redirect('dashboard')
    else:
        form = CompanyForm()
    
    return render(request, 'companies/setup_company.html', {
        'form': form,
        'is_initial_setup': True
    })

@login_required
def create_company(request):
    """
    View to create an additional company for an existing user
    """
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            # Create the company
            company = form.save(commit=False)
            company.created_by = request.user
            company.save()
            logger.info(f"Created company: {company.name} (ID: {company.id})")
            
            # Create the relation between user and company
            UserCompanyRelation.objects.create(
                user=request.user,
                company=company,
                role='owner'  # Make the creator the owner
            )
            logger.info(f"Created user-company relation for user {request.user.email} and company {company.name}")
            
            # Set up OpenAI resources for the company
            logger.info(f"Setting up OpenAI resources for company {company.name}")
            openai_service = CompanyOpenAIService()
            result = openai_service.setup_company_ai(company)
            
            if result['success']:
                company.openai_assistant_id = result['assistant_id']
                company.openai_vector_store_id = result['vector_store_id']
                company.save()
                logger.info(f"Created and saved OpenAI resources for company: {company.name} - Assistant ID: {company.openai_assistant_id}, Vector Store ID: {company.openai_vector_store_id}")
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"Failed to create OpenAI resources for company: {company.name} (ID: {company.id}) - Error: {error_msg}")
                
                # Still proceed with company creation, but show error message
                if 'invalid_api_key' in error_msg or 'API key' in error_msg:
                    messages.error(request, "Company created, but AI assistant setup failed due to API key issues. Please contact support.")
                else:
                    messages.warning(request, "Company created, but AI assistant setup encountered an issue. Some AI features may not be available.")
            
            # Create default project and data silo in the background using Celery
            create_default_project_and_silo.delay(company.id, request.user.id)
            logger.info(f"Triggered default project and silo creation for company: {company.name} (ID: {company.id})")
            
            # Show success message
            messages.success(request, f'Company "{company.name}" created successfully!')
            return redirect('dashboard')
    else:
        form = CompanyForm()
    
    return render(request, 'companies/create_company.html', {
        'form': form,
        'is_initial_setup': False
    })

@login_required
def company_list(request):
    """
    View to list all companies the user has access to
    """
    companies = Company.objects.filter(user_relations__user=request.user)
    
    return render(request, 'companies/company_list.html', {
        'companies': companies
    })

@login_required
def company_detail(request, company_id):
    """
    View to show company details
    """
    company = get_object_or_404(Company, id=company_id)
    
    # Check if user has access to this company
    has_access = UserCompanyRelation.objects.filter(user=request.user, company=company).exists()
    if not has_access:
        messages.error(request, "You don't have access to this company.")
        return redirect('dashboard')
    
    return render(request, 'companies/company_detail.html', {
        'company': company
    })

@login_required
def setup_company_email(request):
    """
    View for setting up the company email for mail receiver
    """
    # Get the user's company
    company = None
    if hasattr(request.user, 'profile') and request.user.profile and hasattr(request.user.profile, 'company'):
        company = request.user.profile.company
    
    if not company:
        # Try to get it from company relations
        relation = request.user.company_relations.first()
        if relation:
            company = relation.company
    
    if not company:
        messages.error(request, "You need to have a company before setting up email integration.")
        return redirect('dashboard')
    
    # Check if user has admin access to this company
    is_admin = UserCompanyRelation.objects.filter(
        user=request.user, 
        company=company,
        role__in=['admin', 'owner']
    ).exists()
    
    if not is_admin:
        messages.error(request, "You need to be an admin or owner to setup email integration.")
        return redirect('dashboard')
    
    # Get the email domain from settings
    email_domain = getattr(settings, 'EMAIL_DOMAIN', 'zignal.com')
    
    # Process form
    if request.method == 'POST':
        form = CompanyEmailForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, f"Email integration successfully set up! Your company's email address is now {company.get_full_email_address()}")
            return redirect('dashboard')
    else:
        form = CompanyEmailForm(instance=company)
    
    return render(request, 'companies/setup_email.html', {
        'form': form,
        'company': company,
        'email_domain': email_domain,
    })

@login_required
def company_team(request):
    """
    View for managing team members for a company
    """
    # Get the user's company
    company = None
    if hasattr(request.user, 'profile') and request.user.profile and hasattr(request.user.profile, 'company'):
        company = request.user.profile.company
    
    if not company:
        # Try to get it from company relations
        relation = request.user.company_relations.first()
        if relation:
            company = relation.company
    
    if not company:
        messages.error(request, "You need to have a company before accessing the team page.")
        return redirect('dashboard')
    
    # Get user's role in this company
    user_relation = UserCompanyRelation.objects.filter(user=request.user, company=company).first()
    user_role = user_relation.role if user_relation else None
    
    # Check if user has access to view team
    if not user_role:
        messages.error(request, "You don't have access to this company team.")
        return redirect('dashboard')
    
    # Get all team members (users with company relation)
    team_members = UserCompanyRelation.objects.filter(company=company).select_related('user')
    
    # Get pending invitations for this company
    pending_invitations = Invitation.objects.filter(
        company=company,
        invitation_type='company',
        status='pending'
    )
    
    # Check if user has admin rights (can invite others)
    can_invite = user_role in ['owner', 'admin']
    
    return render(request, 'companies/company_team.html', {
        'company': company,
        'team_members': team_members,
        'pending_invitations': pending_invitations,
        'user_role': user_role,
        'can_invite': can_invite,
    })
