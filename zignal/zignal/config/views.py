from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from allauth.account.forms import SignupForm

def home(request):
    return render(request, 'home.html')

def chat(request):
    return render(request, 'chat.html') 

@login_required
def dashboard(request):
    """Dashboard view accessible only to authenticated users"""
    # Get user's companies
    user_companies = request.user.company_relations.all()
    
    # Get user's projects
    user_projects = request.user.project_relations.all()
    
    context = {
        'user_companies': user_companies,
        'user_projects': user_projects,
    }
    
    return render(request, 'dashboard.html', context) 

def test_template(request):
    return render(request, 'account/login_test.html') 

def test_view(request):
    """A simple view to test template inheritance"""
    return render(request, 'test.html') 

def test_base_view(request):
    """A simple view to test a template without inheritance"""
    return render(request, 'test_base.html')

def custom_signup(request):
    """Custom signup view for debugging"""
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(request)
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('account_login')
        else:
            # Log form errors for debugging
            print("Form errors:", form.errors)
            print("Non-field errors:", form.non_field_errors())
            print("POST data:", request.POST)
    else:
        form = SignupForm()
        
    context = {
        'form': form,
    }
    return render(request, 'account/custom_signup.html', context) 