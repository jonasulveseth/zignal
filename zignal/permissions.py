from django.core.exceptions import PermissionDenied
from functools import wraps
from django.contrib.auth import get_user_model
from projects.models import Project, UserProjectRelation
from companies.models import Company, UserCompanyRelation
from datasilo.models import DataSilo, DataFile

User = get_user_model()

def company_role_required(role_list):
    """
    Decorator for views that checks if the user has the required role in the company.
    The view should have a company parameter or get_company() method.
    
    Example usage:
    @company_role_required(['owner', 'admin'])
    def my_view(request, company_id):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get company from view function
            company = None
            
            # Try to get company from kwargs
            company_id = kwargs.get('company_id')
            if company_id:
                from companies.models import Company
                try:
                    company = Company.objects.get(id=company_id)
                except Company.DoesNotExist:
                    raise PermissionDenied("Company not found")
            
            # If no company found, try to get from the view
            if not company and hasattr(view_func, 'get_company'):
                company = view_func.get_company(request, *args, **kwargs)
                
            if not company:
                raise PermissionDenied("Company not found")
                
            # Check if user has required role in the company
            user_company_relation = company.user_relations.filter(user=request.user).first()
            
            if not user_company_relation or user_company_relation.role not in role_list:
                raise PermissionDenied("You don't have sufficient permissions")
                
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def project_role_required(role_list):
    """
    Decorator for views that checks if the user has the required role in the project.
    The view should have a project parameter or get_project() method.
    
    Example usage:
    @project_role_required(['manager', 'member'])
    def my_view(request, project_id):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get project from view function
            project = None
            
            # Try to get project from kwargs
            project_id = kwargs.get('project_id')
            if project_id:
                from projects.models import Project
                try:
                    project = Project.objects.get(id=project_id)
                except Project.DoesNotExist:
                    raise PermissionDenied("Project not found")
            
            # If no project found, try to get from the view
            if not project and hasattr(view_func, 'get_project'):
                project = view_func.get_project(request, *args, **kwargs)
                
            if not project:
                raise PermissionDenied("Project not found")
                
            # Check if user has required role in the project
            user_project_relation = project.user_relations.filter(user=request.user).first()
            
            # Alternative: Check if user is owner/admin of the company
            company_access = False
            if not user_project_relation:
                user_company_relation = project.company.user_relations.filter(user=request.user).first()
                if user_company_relation and user_company_relation.role in ['owner', 'admin']:
                    company_access = True
            
            if not (user_project_relation and user_project_relation.role in role_list) and not company_access:
                raise PermissionDenied("You don't have sufficient permissions")
                
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def is_company_admin(user, company):
    """
    Check if a user is an admin or owner of a company
    """
    if not user.is_authenticated:
        return False
        
    relation = company.user_relations.filter(user=user).first()
    return relation and relation.role in ['owner', 'admin']


def is_project_manager(user, project):
    """
    Check if a user is a manager of a project or admin of the project's company
    """
    if not user.is_authenticated:
        return False
        
    # Check project role
    project_relation = project.user_relations.filter(user=user).first()
    if project_relation and project_relation.role == 'manager':
        return True
        
    # Check company role
    company_relation = project.company.user_relations.filter(user=user).first()
    return company_relation and company_relation.role in ['owner', 'admin']


def can_access_project(user, project):
    """
    Check if a user has any access to a project
    """
    if not user.is_authenticated:
        return False
        
    # Check project role
    project_relation = project.user_relations.filter(user=user).first()
    if project_relation:
        return True
        
    # Check company role
    company_relation = project.company.user_relations.filter(user=user).first()
    return company_relation is not None 

# User permission checks for Projects
def has_project_permission(user, project, require_admin=False):
    """Check if a user has permission to access a project"""
    if user.is_superuser:
        return True
        
    try:
        relation = UserProjectRelation.objects.get(user=user, project=project)
        return not require_admin or relation.role in ['admin', 'owner']
    except UserProjectRelation.DoesNotExist:
        # Also check if user is admin/owner of the company that owns the project
        try:
            company_relation = UserCompanyRelation.objects.get(user=user, company=project.company)
            return company_relation.role in ['admin', 'owner']
        except UserCompanyRelation.DoesNotExist:
            return False

def has_company_permission(user, company, require_admin=False):
    """Check if a user has permission to access a company"""
    if user.is_superuser:
        return True
        
    try:
        relation = UserCompanyRelation.objects.get(user=user, company=company)
        return not require_admin or relation.role in ['admin', 'owner']
    except UserCompanyRelation.DoesNotExist:
        return False

def get_accessible_projects(user):
    """Get all projects accessible to a user"""
    if user.is_superuser:
        return Project.objects.all()
        
    # Get companies where user is a member
    user_companies = Company.objects.filter(usercompanyrelation__user=user)
    
    # Get projects where user is directly a member or member of the owning company
    return Project.objects.filter(
        userprojectrelation__user=user
    ).distinct() | Project.objects.filter(
        company__in=user_companies
    ).distinct()

def get_accessible_companies(user):
    """Get all companies accessible to a user"""
    if user.is_superuser:
        return Company.objects.all()
        
    return Company.objects.filter(usercompanyrelation__user=user).distinct()

# Data Silo permissions
def has_silo_permission(user, data_silo, require_admin=False):
    """Check if a user has permission to access a data silo"""
    if user.is_superuser:
        return True
    
    # Check if user created the silo
    if data_silo.created_by == user:
        return True
        
    # Check project permissions
    if data_silo.project:
        return has_project_permission(user, data_silo.project, require_admin)
    
    # Check company permissions
    if data_silo.company:
        return has_company_permission(user, data_silo.company, require_admin)
    
    return False

# Data File permissions
def has_file_permission(user, data_file, require_admin=False):
    """Check if a user has permission to access a data file"""
    if user.is_superuser:
        return True
    
    # Check if user uploaded the file
    if data_file.uploaded_by == user:
        return True
    
    # Check data silo permissions
    return has_silo_permission(user, data_file.data_silo, require_admin) 