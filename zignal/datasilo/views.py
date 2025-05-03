from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.urls import reverse
from django.core.exceptions import PermissionDenied

from .models import DataSilo, DataFile
from .forms import DataSiloForm, DataFileForm
from permissions import has_silo_permission, has_file_permission


@login_required
def data_silo_list(request):
    """List all data silos that the user has access to"""
    user = request.user
    
    # Get companies user has access to through UserCompanyRelation
    user_companies = user.company_relations.values_list('company', flat=True)
    
    # Get projects user has access to through UserProjectRelation (if that exists)
    # Otherwise use an empty queryset
    try:
        from projects.models import UserProjectRelation
        user_projects = UserProjectRelation.objects.filter(user=user).values_list('project', flat=True)
    except ImportError:
        user_projects = []
    
    # Query data silos related to user's projects and companies
    data_silos = DataSilo.objects.filter(
        Q(project__in=user_projects) | 
        Q(company__in=user_companies)
    ).distinct()
    
    return render(request, 'datasilo/silo_list.html', {
        'data_silos': data_silos
    })


@login_required
def data_silo_create(request):
    """Create a new data silo"""
    if request.method == 'POST':
        form = DataSiloForm(request.POST, user=request.user)
        if form.is_valid():
            data_silo = form.save(commit=False)
            data_silo.created_by = request.user
            data_silo.save()
            
            messages.success(request, "Data silo created successfully.")
            return redirect('datasilo:silo_detail', slug=data_silo.slug)
    else:
        form = DataSiloForm(user=request.user)
    
    return render(request, 'datasilo/silo_form.html', {
        'form': form,
        'title': 'Create Data Silo'
    })


@login_required
def data_silo_detail(request, slug):
    """View a data silo and its files"""
    data_silo = get_object_or_404(DataSilo, slug=slug)
    
    # Check permissions
    if not has_silo_permission(request.user, data_silo):
        raise PermissionDenied("You don't have permission to access this data silo.")
    
    # Get all files in the data silo
    files = data_silo.files.all().order_by('-created_at')
    
    # Calculate total size
    total_size = sum(f.size for f in files)
    
    return render(request, 'datasilo/silo_detail.html', {
        'data_silo': data_silo,
        'files': files,
        'total_size': total_size,
        'file_count': files.count()
    })


@login_required
def data_silo_edit(request, slug):
    """Edit an existing data silo"""
    data_silo = get_object_or_404(DataSilo, slug=slug)
    
    # Check permissions
    if not has_silo_permission(request.user, data_silo, require_admin=True):
        raise PermissionDenied("You don't have permission to edit this data silo.")
    
    if request.method == 'POST':
        form = DataSiloForm(request.POST, instance=data_silo, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Data silo updated successfully.")
            return redirect('datasilo:silo_detail', slug=data_silo.slug)
    else:
        form = DataSiloForm(instance=data_silo, user=request.user)
    
    return render(request, 'datasilo/silo_form.html', {
        'form': form,
        'data_silo': data_silo,
        'title': 'Edit Data Silo'
    })


@login_required
def data_silo_delete(request, slug):
    """Delete a data silo"""
    data_silo = get_object_or_404(DataSilo, slug=slug)
    
    # Check permissions
    if not has_silo_permission(request.user, data_silo, require_admin=True):
        raise PermissionDenied("You don't have permission to delete this data silo.")
    
    # Get file count to warn user
    file_count = data_silo.files.count()
    
    if request.method == 'POST':
        # Record which project/company the silo belonged to for redirection
        if data_silo.project:
            redirect_url = reverse('projects:detail', kwargs={'slug': data_silo.project.slug})
        else:
            redirect_url = reverse('companies:detail', kwargs={'slug': data_silo.company.slug})
        
        data_silo.delete()
        messages.success(request, "Data silo deleted successfully.")
        return redirect(redirect_url)
    
    return render(request, 'datasilo/silo_delete.html', {
        'data_silo': data_silo,
        'file_count': file_count
    })


@login_required
def file_upload(request, slug):
    """Upload a file to a data silo"""
    data_silo = get_object_or_404(DataSilo, slug=slug)
    
    # Check permissions
    if not has_silo_permission(request.user, data_silo):
        raise PermissionDenied("You don't have permission to upload files to this data silo.")
    
    if request.method == 'POST':
        # Debug information
        print("POST data:", request.POST)
        print("FILES data:", request.FILES)
        
        form = DataFileForm(request.POST, request.FILES, data_silo=data_silo, user=request.user)
        if form.is_valid():
            try:
                data_file = form.save()
                
                # Update file size after save
                data_file.size = data_file.file.size
                data_file.save()
                
                # Trigger file processing for vector store
                from django.conf import settings
                try:
                    # Check if Celery tasks for vector store processing exist
                    from core.tasks import process_file_for_vector_store
                    # Schedule the task
                    process_file_for_vector_store.delay(data_file.id)
                    print(f"Scheduled vector store processing for file ID: {data_file.id}")
                except (ImportError, AttributeError) as e:
                    print(f"Vector store processing not available: {str(e)}")
                    # Update status to indicate processing wasn't triggered
                    data_file.vector_store_status = 'failed'
                    data_file.save(update_fields=['vector_store_status'])
                
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    # Return JSON response for AJAX requests
                    return JsonResponse({
                        'success': True,
                        'file_id': data_file.id,
                        'file_name': data_file.name,
                        'file_url': data_file.file.url
                    })
                
                messages.success(request, "File uploaded successfully.")
                return redirect('datasilo:silo_detail', slug=data_silo.slug)
            except Exception as e:
                print("Error saving file:", str(e))
                messages.error(request, f"Error saving file: {str(e)}")
        else:
            print("Form errors:", form.errors)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error in {field}: {error}")
    else:
        form = DataFileForm(data_silo=data_silo, user=request.user)
    
    return render(request, 'datasilo/file_upload.html', {
        'form': form,
        'data_silo': data_silo
    })


@login_required
def file_detail(request, file_id):
    """View details of a specific file"""
    data_file = get_object_or_404(DataFile, id=file_id)
    
    # Check permissions
    if not has_file_permission(request.user, data_file):
        raise PermissionDenied("You don't have permission to view this file.")
    
    return render(request, 'datasilo/file_detail.html', {
        'file': data_file,
        'data_silo': data_file.data_silo
    })


@login_required
def file_delete(request, file_id):
    """Delete a file"""
    data_file = get_object_or_404(DataFile, id=file_id)
    data_silo = data_file.data_silo
    
    # Check permissions
    if not has_file_permission(request.user, data_file, require_admin=True):
        raise PermissionDenied("You don't have permission to delete this file.")
    
    if request.method == 'POST':
        data_file.delete()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Return JSON response for AJAX requests
            return JsonResponse({'success': True})
        
        messages.success(request, "File deleted successfully.")
        return redirect('datasilo:silo_detail', slug=data_silo.slug)
    
    return render(request, 'datasilo/file_delete.html', {
        'file': data_file,
        'data_silo': data_silo
    })
