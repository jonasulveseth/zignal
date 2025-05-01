from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.urls import reverse
from django.core.paginator import Paginator

from .models import ReportTemplate, Report, ReportSchedule
from .services.report_generation_service import ReportGenerationService
from .forms import ReportForm, ReportTemplateForm, ReportScheduleForm
from permissions import has_project_permission, has_company_permission
from companies.models import Company


@login_required
def report_list(request):
    """
    List all reports the user has access to
    """
    # Get user's projects and companies
    user_projects = request.user.projects.all()
    user_companies = request.user.companies.all()
    
    # Filter reports
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    # Start with all reports
    reports = Report.objects.filter(
        Q(project__in=user_projects) | 
        Q(company__in=user_companies)
    ).distinct()
    
    # Apply search query
    if query:
        reports = reports.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Apply status filter
    if status_filter:
        reports = reports.filter(status=status_filter)
    
    # Apply sorting
    reports = reports.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(reports, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'reports': page_obj,
        'query': query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'status_choices': Report.STATUS_CHOICES,
    }
    
    return render(request, 'reports/report_list.html', context)


@login_required
def report_detail(request, slug):
    """
    View a specific report
    """
    report = get_object_or_404(Report, slug=slug)
    
    # Check permissions
    if report.project and not has_project_permission(request.user, report.project):
        messages.error(request, "You don't have permission to view this report.")
        return redirect('reports:report_list')
    
    if report.company and not has_company_permission(request.user, report.company):
        messages.error(request, "You don't have permission to view this report.")
        return redirect('reports:report_list')
    
    context = {
        'report': report,
    }
    
    return render(request, 'reports/report_detail.html', context)


@login_required
def report_create(request):
    """
    Create a new report
    """
    # Initial data for form
    initial_data = {}
    
    # Check if company ID was passed in the query string
    company_id = request.GET.get('company')
    if company_id:
        try:
            company = Company.objects.get(id=company_id)
            # Check if user has permission to access this company
            has_access = company.user_relations.filter(user=request.user).exists()
            
            if has_access:
                initial_data['company'] = company
        except (Company.DoesNotExist, ValueError):
            pass
    
    if request.method == 'POST':
        form = ReportForm(request.POST, user=request.user)
        if form.is_valid():
            report = form.save(commit=False)
            report.created_by = request.user
            report.save()
            
            messages.success(request, f"Report '{report.title}' created successfully.")
            
            # If generate_now is checked, generate the report immediately
            if request.POST.get('generate_now'):
                return redirect('reports:report_generate', slug=report.slug)
            
            return redirect('reports:report_detail', slug=report.slug)
    else:
        form = ReportForm(user=request.user, initial=initial_data)
    
    context = {
        'form': form,
        'title': 'Create New Report',
    }
    
    return render(request, 'reports/report_form.html', context)


@login_required
def report_edit(request, slug):
    """
    Edit an existing report
    """
    report = get_object_or_404(Report, slug=slug)
    
    # Check permissions
    if report.project and not has_project_permission(request.user, report.project):
        messages.error(request, "You don't have permission to edit this report.")
        return redirect('reports:report_list')
    
    if report.company and not has_company_permission(request.user, report.company):
        messages.error(request, "You don't have permission to edit this report.")
        return redirect('reports:report_list')
    
    if request.method == 'POST':
        form = ReportForm(request.POST, instance=report, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Report '{report.title}' updated successfully.")
            return redirect('reports:report_detail', slug=report.slug)
    else:
        form = ReportForm(instance=report, user=request.user)
    
    context = {
        'form': form,
        'report': report,
        'title': 'Edit Report',
    }
    
    return render(request, 'reports/report_form.html', context)


@login_required
def report_delete(request, slug):
    """
    Delete a report
    """
    report = get_object_or_404(Report, slug=slug)
    
    # Check permissions
    if report.project and not has_project_permission(request.user, report.project, require_admin=True):
        messages.error(request, "You don't have permission to delete this report.")
        return redirect('reports:report_list')
    
    if report.company and not has_company_permission(request.user, report.company, require_admin=True):
        messages.error(request, "You don't have permission to delete this report.")
        return redirect('reports:report_list')
    
    if request.method == 'POST':
        report.status = 'archived'
        report.save()
        messages.success(request, f"Report '{report.title}' archived successfully.")
        return redirect('reports:report_list')
    
    context = {
        'report': report,
    }
    
    return render(request, 'reports/report_delete.html', context)


@login_required
def report_generate(request, slug):
    """
    Generate a report using AI
    """
    report = get_object_or_404(Report, slug=slug)
    
    # Check permissions
    if report.project and not has_project_permission(request.user, report.project):
        messages.error(request, "You don't have permission to generate this report.")
        return redirect('reports:report_list')
    
    if report.company and not has_company_permission(request.user, report.company):
        messages.error(request, "You don't have permission to generate this report.")
        return redirect('reports:report_list')
    
    # Check if the report has a template
    if not report.template:
        messages.error(request, "The report must have a template to generate content.")
        return redirect('reports:report_detail', slug=report.slug)
    
    # Generate report content
    service = ReportGenerationService()
    success = service.generate_report(report)
    
    if success:
        messages.success(request, f"Report '{report.title}' generated successfully.")
    else:
        messages.error(request, f"Failed to generate report '{report.title}'.")
    
    return redirect('reports:report_detail', slug=report.slug)


@login_required
def report_export_pdf(request, slug):
    """
    Export a report as PDF
    """
    report = get_object_or_404(Report, slug=slug)
    
    # Check permissions
    if report.project and not has_project_permission(request.user, report.project):
        messages.error(request, "You don't have permission to export this report.")
        return redirect('reports:report_list')
    
    if report.company and not has_company_permission(request.user, report.company):
        messages.error(request, "You don't have permission to export this report.")
        return redirect('reports:report_list')
    
    # Check if the report is generated
    if report.status != 'generated':
        messages.error(request, "The report must be generated before exporting as PDF.")
        return redirect('reports:report_detail', slug=report.slug)
    
    # If PDF already exists
    if report.pdf_file:
        response = HttpResponse(report.pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report.slug}.pdf"'
        return response
    
    # Generate PDF
    service = ReportGenerationService()
    pdf_path = service._generate_pdf(report)
    
    if pdf_path:
        messages.success(request, f"Report '{report.title}' exported as PDF successfully.")
        report.pdf_file = pdf_path
        report.save()
        return redirect('reports:report_detail', slug=report.slug)
    else:
        messages.error(request, f"Failed to export report '{report.title}' as PDF.")
        return redirect('reports:report_detail', slug=report.slug)


# Template views
@login_required
def template_list(request):
    """
    List all report templates the user has access to
    """
    # Get user's companies
    user_companies = request.user.companies.all()
    
    # Filter templates
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'name')
    
    # Start with all templates
    templates = ReportTemplate.objects.filter(
        Q(company__in=user_companies) | 
        Q(company__isnull=True)
    ).distinct()
    
    # Apply search query
    if query:
        templates = templates.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Apply sorting
    templates = templates.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(templates, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'templates': page_obj,
        'query': query,
        'sort_by': sort_by,
    }
    
    return render(request, 'reports/template_list.html', context)


# Schedule views
@login_required
def schedule_list(request):
    """
    List all report schedules the user has access to
    """
    # Get user's projects and companies
    user_projects = request.user.projects.all()
    user_companies = request.user.companies.all()
    
    # Filter schedules
    query = request.GET.get('q', '')
    active_filter = request.GET.get('active', '')
    sort_by = request.GET.get('sort', 'name')
    
    # Start with all schedules
    schedules = ReportSchedule.objects.filter(
        Q(project__in=user_projects) | 
        Q(company__in=user_companies)
    ).distinct()
    
    # Apply search query
    if query:
        schedules = schedules.filter(
            Q(name__icontains=query)
        )
    
    # Apply active filter
    if active_filter:
        is_active = active_filter == 'true'
        schedules = schedules.filter(is_active=is_active)
    
    # Apply sorting
    schedules = schedules.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(schedules, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'schedules': page_obj,
        'query': query,
        'active_filter': active_filter,
        'sort_by': sort_by,
    }
    
    return render(request, 'reports/schedule_list.html', context)
