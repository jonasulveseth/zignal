from django.core.exceptions import PermissionDenied
from functools import wraps

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