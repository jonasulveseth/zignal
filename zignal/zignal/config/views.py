from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from allauth.account.forms import SignupForm
from django.contrib.auth import get_user_model
from django.conf import settings
import os
import uuid

# Import necessary models
from companies.models import Company
from projects.models import Project
from reports.models import Report
from datasilo.models import DataFile, DataSilo
from agents.models import MeetingTranscript
from profiles.models import Profile
from django.db.models import Count

User = get_user_model()

def home(request):
    if request.user.is_authenticated:
        # Redirect authenticated users to dashboard
        return redirect('dashboard')
    return render(request, 'home.html')

def chat(request):
    return render(request, 'chat/chat.html') 

@login_required
def dashboard(request):
    user = request.user
    profile = Profile.objects.filter(user=user).first()
    
    # Check if the user has a company associated
    has_company = False
    if profile and hasattr(profile, 'company') and profile.company:
        has_company = True
    
    # If no company is found through profile, try to get it through UserCompanyRelation
    if not has_company:
        has_company = user.company_relations.exists()
    
    # If user doesn't have a company, redirect to company setup
    if not has_company:
        messages.info(request, "You need to set up a company before you can access the dashboard.")
        return redirect('setup_company')
    
    # Debug print to check user type
    print(f"Current user: {user.username}, User type: {user.user_type}")
    
    # Determine user type and redirect to appropriate dashboard
    if user.user_type == 'portfolio_manager':
        print("Rendering PORTFOLIO MANAGER dashboard")
        # Portfolio managers only see companies
        companies = Company.objects.filter(user_relations__user=user)
        company_count = companies.count()
        
        # Don't fetch projects for portfolio managers
        project_count = 0
        report_count = 0
        recent_reports = []
        
        # Recent activities would be determined by a separate model
        # For now, we'll pass empty data
        recent_activities = []
        
        return render(request, 'dashboard/portfolio_dashboard.html', {
            'user': user,
            'profile': profile,
            'companies': companies,
            'company_count': company_count,
            'project_count': project_count,
            'report_count': report_count,
            'recent_reports': recent_reports,
            'recent_activities': recent_activities,
        })
    else:
        print("Rendering COMPANY USER dashboard")
        # Company user dashboard
        company = None
        if profile and hasattr(profile, 'company'):
            company = profile.company
        
        # If no company is found through profile, try to get it through UserCompanyRelation
        if not company:
            company_relation = user.company_relations.first()
            if company_relation:
                company = company_relation.company
        
        if company:
            projects = Project.objects.filter(company=company)
            reports = Report.objects.filter(project__in=projects)
            recent_reports = reports.order_by('-created_at')[:5]
            
            # Get data silos for the company
            data_silos = DataSilo.objects.filter(company=company)
            
            # Get meeting transcripts for the company
            meeting_transcripts = MeetingTranscript.objects.filter(company=company).order_by('-created_at')[:5]
        else:
            projects = Project.objects.none()
            reports = Report.objects.none()
            recent_reports = []
            data_silos = DataSilo.objects.none()
            meeting_transcripts = MeetingTranscript.objects.none()
        
        return render(request, 'dashboard/company_dashboard.html', {
            'user': user,
            'profile': profile,
            'company': company,
            'projects': projects,
            'reports': recent_reports,
            'data_silos': data_silos,
            'meeting_transcripts': meeting_transcripts,
        })

def test_template(request):
    return render(request, 'test_template.html') 

def test_view(request):
    """A simple view to test template inheritance"""
    return render(request, 'test.html') 

def test_base_view(request):
    """A simple view to test a template without inheritance"""
    return render(request, 'layouts/base_test.html')

def custom_signup(request):
    """Custom signup view for debugging"""
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                # Save the form with the request
                user = form.save(request)
                messages.success(request, 'Account created successfully! Please log in.')
                return redirect('account_login')
            except Exception as e:
                # Log any error during save
                print(f"Error saving user: {str(e)}")
                messages.error(request, f"An error occurred during signup: {str(e)}")
        else:
            # Log form errors for debugging
            print("Form errors:", form.errors)
            print("Non-field errors:", form.non_field_errors())
            print("POST data:", dict(request.POST))
            
            # Check username related errors specifically
            if 'username' in form.errors:
                print("Username errors:", form.errors['username'])
                
                # Try to generate a valid username
                email = request.POST.get('email', '')
                if email:
                    username = email.split('@')[0]
                    print(f"Generated username: {username}")
    else:
        form = SignupForm()
        
    context = {
        'form': form,
    }
    return render(request, 'account/custom_signup.html', context) 

def is_portfolio_manager(user):
    """Check if user is a portfolio manager"""
    return user.is_authenticated and user.user_type == 'portfolio_manager'

@login_required
@user_passes_test(is_portfolio_manager, login_url='/dashboard/')
def portfolio_manager_chat(request):
    """Global chat for portfolio managers"""
    user = request.user
    profile = Profile.objects.filter(user=user).first()
    
    if user.user_type == 'portfolio_manager':
        return render(request, 'chat/portfolio_chat.html')
    else:
        # Redirect non-portfolio managers
        return redirect('dashboard')

@login_required
def file_management(request):
    """View for file management dashboard"""
    user = request.user
    profile = Profile.objects.filter(user=user).first()
    
    # Get data silos
    if user.user_type == 'portfolio_manager':
        # Portfolio managers can see all data silos
        data_silos = DataSilo.objects.all().annotate(file_count=Count('datafile'))
    else:
        # Company users only see their company's data silos
        company = profile.company if profile and hasattr(profile, 'company') else None
        if company:
            data_silos = DataSilo.objects.filter(company=company).annotate(file_count=Count('datafile'))
        else:
            data_silos = DataSilo.objects.none()
    
    # Get recent files
    recent_files = DataFile.objects.all().order_by('-uploaded_at')[:10]
    
    # Handle search/filter
    search_query = request.GET.get('search', '')
    file_type = request.GET.get('file_type', '')
    
    if search_query:
        data_silos = data_silos.filter(name__icontains=search_query)
        recent_files = recent_files.filter(name__icontains=search_query)
    
    if file_type:
        recent_files = recent_files.filter(file_type=file_type)
    
    return render(request, 'dashboard/file_management.html', {
        'data_silos': data_silos,
        'recent_files': recent_files,
        'search_query': search_query,
        'file_type': file_type,
    })

@login_required
def report_management(request):
    """View for report management dashboard"""
    user = request.user
    profile = Profile.objects.filter(user=user).first()
    
    # Get reports based on user type
    if user.user_type == 'portfolio_manager':
        # Portfolio managers can see all reports
        reports = Report.objects.all().order_by('-created_at')
    else:
        # Company users only see their company's reports
        company = profile.company if profile and hasattr(profile, 'company') else None
        if company:
            projects = Project.objects.filter(company=company)
            reports = Report.objects.filter(project__in=projects).order_by('-created_at')
        else:
            reports = Report.objects.none()
    
    return render(request, 'dashboard/report_management.html', {
        'reports': reports,
    })

@login_required
def toggle_user_type(request):
    """Debug view to toggle between portfolio_manager and company_user for testing"""
    user = request.user
    
    # Toggle user type
    if user.user_type == 'portfolio_manager':
        user.user_type = 'company_user'
        message = "Changed to company user"
    else:
        user.user_type = 'portfolio_manager'
        message = "Changed to portfolio manager"
    
    # Save the user
    user.save()
    
    # Add message and redirect
    messages.success(request, f"{message}. Your user type is now: {user.user_type}")
    return redirect('dashboard') 

@login_required
def redirect_to_company_silo(request):
    """Redirect to the first data silo for the company"""
    user = request.user
    company = None
    
    # Get the user's company
    if hasattr(user, 'profile') and user.profile and hasattr(user.profile, 'company'):
        company = user.profile.company
    
    if not company:
        company_relation = user.company_relations.first()
        if company_relation:
            company = company_relation.company
    
    if not company:
        messages.error(request, "You need to have a company before accessing data silos.")
        return redirect('dashboard')
    
    # Find the first data silo for this company
    from datasilo.models import DataSilo
    data_silo = DataSilo.objects.filter(company=company).first()
    
    if data_silo:
        return redirect('datasilo:silo_detail', slug=data_silo.slug)
    else:
        messages.info(request, "No data silos found for your company. Creating a default one.")
        # If no data silo exists, redirect to the data silo list (which should offer to create one)
        return redirect('datasilo:silo_list') 