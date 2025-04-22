from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Project
from companies.models import Company
import logging
import json
import traceback
from django.urls import reverse

# Get logger
logger = logging.getLogger(__name__)

# Create your views here.

@login_required
@ensure_csrf_cookie
def create_project(request):
    """
    View to handle project creation
    """
    logger.info(f"Request method: {request.method}")
    logger.info(f"Is AJAX: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
    
    # Check if user has a company
    has_company = False
    if hasattr(request.user, 'profile') and request.user.profile and hasattr(request.user.profile, 'company'):
        has_company = True
    
    # If no company is found through profile, try to get it through UserCompanyRelation
    if not has_company:
        has_company = request.user.company_relations.exists()
    
    # If user doesn't have a company, redirect to company setup
    if not has_company:
        logger.warning(f"User {request.user.username} tried to create a project without having a company")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'You need to set up a company before creating projects', 'redirect': reverse('setup_company')}, status=400)
        messages.info(request, "You need to set up a company before you can create projects.")
        return redirect('setup_company')
    
    if request.method == 'POST':
        logger.info(f"POST request received for project creation")
        logger.info(f"POST data: {request.POST}")
        
        # Debug: Print all request headers and content
        try:
            logger.info(f"Request headers: {json.dumps(dict(request.headers))}")
        except Exception as e:
            logger.error(f"Error serializing headers: {str(e)}")
            
        logger.info(f"Is AJAX request: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
        
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        status = request.POST.get('status', 'active')
        start_date = request.POST.get('start_date') or None
        end_date = request.POST.get('end_date') or None
        
        logger.info(f"Project data: name={name}, status={status}, start_date={start_date}, end_date={end_date}")
        
        # Validate required fields
        if not name:
            logger.error("Project name is required")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Project name is required'}, status=400)
            messages.error(request, 'Project name is required')
            return redirect('dashboard')
        
        # Get company from user's company relation
        company = None
        if hasattr(request.user, 'profile') and request.user.profile and hasattr(request.user.profile, 'company'):
            company = request.user.profile.company
            logger.info(f"Company found via profile: {company}")
        
        # If no company is found through profile, try to get it through UserCompanyRelation
        if not company:
            try:
                company_relation = request.user.company_relations.first()
                if company_relation:
                    company = company_relation.company
                    logger.info(f"Company found via company_relations: {company}")
                else:
                    logger.info(f"No company relation found for user {request.user.username}")
            except Exception as e:
                logger.error(f"Error getting company relations: {str(e)}")
        
        # If we still don't have a company, redirect to company setup
        if not company:
            logger.warning(f"User {request.user.username} tried to create a project without having a company")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'You need to set up a company before creating projects', 'redirect': reverse('setup_company')}, status=400)
            messages.info(request, "You need to set up a company before you can create projects.")
            return redirect('setup_company')
        
        try:
            # Create the project
            project = Project.objects.create(
                name=name,
                description=description,
                status=status,
                start_date=start_date,
                end_date=end_date,
                company=company,
                created_by=request.user
            )
            logger.info(f"Project created successfully: {project.id} - {project.name}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'project_id': project.id, 'message': f'Project "{project.name}" created successfully'})
            
            messages.success(request, f'Project "{project.name}" created successfully')
            return redirect('dashboard')
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            logger.error(traceback.format_exc())
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
            
            messages.error(request, f"Error creating project: {str(e)}")
            return redirect('dashboard')
    else:
        logger.info(f"GET request received for project creation - redirecting to dashboard")
    
    # GET requests just redirect to dashboard
    return redirect('dashboard')

@login_required
def test_project_creation(request):
    """
    Test view with a simple form for project creation
    """
    # Check if user has a company
    has_company = False
    if hasattr(request.user, 'profile') and request.user.profile and hasattr(request.user.profile, 'company'):
        has_company = True
    
    # If no company is found through profile, try to get it through UserCompanyRelation
    if not has_company:
        has_company = request.user.company_relations.exists()
    
    # If user doesn't have a company, redirect to company setup
    if not has_company:
        logger.warning(f"User {request.user.username} tried to access the test project creation page without having a company")
        messages.info(request, "You need to set up a company before you can create projects.")
        return redirect('setup_company')
    
    if request.method == 'POST':
        logger.info(f"POST request received for test project creation")
        logger.info(f"POST data: {request.POST}")
        
        return create_project(request)
    
    return render(request, 'projects/test_project_form.html')
