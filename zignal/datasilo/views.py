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
    import os
    
    data_silo = get_object_or_404(DataSilo, slug=slug)
    
    # Check permissions
    if not has_silo_permission(request.user, data_silo):
        raise PermissionDenied("You don't have permission to upload files to this data silo.")
    
    if request.method == 'POST':
        # Debug information
        print("POST data:", request.POST)
        print("FILES data:", request.FILES)
        
        # Check storage configuration
        from django.core.files.storage import default_storage
        from django.conf import settings
        
        storage_type = default_storage.__class__.__name__
        s3_storage = 'S3' in storage_type or 'Boto' in storage_type  # Check if using S3 or Boto storage
        print(f"Storage type: {storage_type}, Using S3: {s3_storage}")
        
        # Verify AWS credentials if using S3
        if s3_storage:
            try:
                from storages.backends.s3boto3 import S3Boto3Storage
                import boto3
                from botocore.exceptions import ClientError
                
                # Create a test s3 client to verify credentials
                s3 = boto3.client(
                    's3',
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME
                )
                
                # Try to list buckets to verify credentials
                try:
                    response = s3.list_buckets()
                    print(f"S3 list_buckets response: {len(response['Buckets'])} buckets found")
                    if settings.AWS_STORAGE_BUCKET_NAME:
                        print(f"Using bucket: {settings.AWS_STORAGE_BUCKET_NAME}")
                    else:
                        print("WARNING: AWS_STORAGE_BUCKET_NAME not set")
                except ClientError as e:
                    print(f"S3 credential error: {str(e)}")
            except Exception as e:
                print(f"Error verifying S3 credentials: {str(e)}")
        
        # Get headers and detect AJAX
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        request_id = request.headers.get('X-Request-ID') or request.META.get('HTTP_X_REQUEST_ID')
        print(f"Request-ID: {request_id}, Is AJAX: {is_ajax}")
        
        # PREVENT DUPLICATE UPLOADS: Check if this is a duplicate request
        # Use a unique cache key for this user and file
        import hashlib
        cache_key = None
        
        if request.FILES and 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            file_name = os.path.basename(uploaded_file.name)
            
            # Create a unique key based on user, file name, and file size
            unique_str = f"{request.user.id}:{file_name}:{uploaded_file.size}"
            cache_key = f"file_upload:{hashlib.md5(unique_str.encode()).hexdigest()}"
            
            # Check if we've seen this request recently (from Django cache)
            from django.core.cache import cache
            if cache.get(cache_key):
                print(f"Duplicate upload detected via cache key: {cache_key}")
                
                # Find the most recent matching file
                import datetime
                from django.utils import timezone
                time_threshold = timezone.now() - datetime.timedelta(minutes=5)
                
                existing_files = DataFile.objects.filter(
                    data_silo=data_silo,
                    name__icontains=os.path.splitext(file_name)[0],
                    created_at__gte=time_threshold
                ).order_by('-created_at')
                
                if existing_files.exists():
                    print(f"Found matching recent file: {existing_files.first().name}")
                    data_file = existing_files.first()
                    
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'file_id': data_file.id,
                            'file_name': data_file.name,
                            'file_url': data_file.file.url,
                            'message': 'File already uploaded'
                        })
                    else:
                        messages.info(request, "This file was already uploaded.")
                        return redirect('datasilo:silo_detail', slug=data_silo.slug)
                
            # Set cache to prevent duplicate uploads (expire after 5 minutes)
            cache.set(cache_key, True, 300)
        
        # Process the form
        form = DataFileForm(request.POST, request.FILES, data_silo=data_silo, user=request.user)
        if form.is_valid():
            try:
                # Create file object but don't save to DB yet
                data_file = form.save(commit=False)
                
                # Set file name to original file name if not set
                if not data_file.name:
                    data_file.name = os.path.basename(request.FILES['file'].name)
                
                # Set company and project from data silo if not provided
                if data_silo.project and not data_file.project:
                    data_file.project = data_silo.project
                if data_silo.company and not data_file.company:
                    data_file.company = data_silo.company
                
                # Now save to database which will upload file to storage
                data_file.save()
                print(f"Saved file with ID {data_file.id} to database, file path: {data_file.file.name}")
                
                # Update file size after save
                if hasattr(data_file.file, 'size'):
                    data_file.size = data_file.file.size
                    data_file.save(update_fields=['size'])
                
                # VERIFY FILE EXISTS: Check if file was actually stored
                # For both local and S3 storage
                from django.core.files.storage import default_storage
                file_exists = False
                
                try:
                    # Use storage API which works for both local and S3
                    file_exists = default_storage.exists(data_file.file.name)
                    print(f"File exists check using storage API: {file_exists}")
                    
                    # For local storage, also check the path directly
                    if not file_exists and hasattr(data_file.file, 'path') and os.path.exists(data_file.file.path):
                        file_exists = True
                        print(f"File exists check using path: {file_exists}")
                except Exception as e:
                    print(f"Error checking file existence: {str(e)}")
                    file_exists = False
                
                if not file_exists:
                    print(f"ERROR: File not found after upload: {data_file.file.name}")
                    
                    # Try to identify the issue - check storage settings for S3
                    if s3_storage:
                        import boto3
                        from botocore.exceptions import ClientError
                        
                        try:
                            s3 = boto3.client(
                                's3',
                                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                region_name=settings.AWS_S3_REGION_NAME
                            )
                            
                            # Check if bucket exists
                            try:
                                s3.head_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
                                print(f"S3 bucket '{settings.AWS_STORAGE_BUCKET_NAME}' exists")
                                
                                # Try to list objects in the bucket (optional)
                                response = s3.list_objects_v2(
                                    Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                                    Prefix=settings.AWS_LOCATION or 'media',
                                    MaxKeys=5
                                )
                                object_count = response.get('KeyCount', 0)
                                print(f"Found {object_count} objects in bucket with prefix '{settings.AWS_LOCATION or 'media'}'")
                                
                            except ClientError as e:
                                print(f"Bucket check error: {e.response['Error']['Message']}")
                        except Exception as e:
                            print(f"S3 connection error: {str(e)}")
                    
                    messages.error(request, "File was uploaded but could not be stored. Please contact support.")
                    data_file.delete()  # Remove the database entry if file doesn't exist
                    return redirect('datasilo:silo_detail', slug=data_silo.slug)
                    
                # File exists, continue with vector store processing
                print(f"File successfully stored in storage: {data_file.file.name}")
                
                # URL of the file - for S3 this should be an S3 URL
                file_url = data_file.file.url
                print(f"File URL: {file_url}")
                
                # Trigger file processing for vector store
                from django.conf import settings
                
                # Using synchronous processing instead of Celery
                if getattr(settings, 'USE_SYNCHRONOUS_TASKS', False):
                    try:
                        from core.tasks import process_file_for_vector_store
                        print(f"Running synchronous vector store processing for file ID: {data_file.id}")
                        process_file_for_vector_store(data_file.id)
                    except (ImportError, AttributeError) as e:
                        print(f"Vector store processing not available: {str(e)}")
                        data_file.vector_store_status = 'failed'
                        data_file.save(update_fields=['vector_store_status'])
                else:
                    try:
                        from core.tasks import process_file_for_vector_store
                        # Use normal function call
                        process_file_for_vector_store(data_file.id)
                        print(f"Called vector store processing for file ID: {data_file.id}")
                    except Exception as e:
                        print(f"Error processing file for vector store: {str(e)}")
                        data_file.vector_store_status = 'failed'
                        data_file.save(update_fields=['vector_store_status'])
                
                if is_ajax:
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
        'file': data_file
    })


@login_required
def file_delete(request, file_id):
    """Delete a file from a data silo"""
    data_file = get_object_or_404(DataFile, id=file_id)
    data_silo = data_file.data_silo
    
    # Check permissions
    if not has_file_permission(request.user, data_file, require_admin=True):
        raise PermissionDenied("You don't have permission to delete this file.")
    
    if request.method == 'POST':
        data_file.delete()
        messages.success(request, "File deleted successfully.")
        return redirect('datasilo:silo_detail', slug=data_silo.slug)
    
    return render(request, 'datasilo/file_delete.html', {
        'data_file': data_file,
        'data_silo': data_silo
    })


@login_required
def company_data_silos(request, company_id):
    """View all data silos for a specific company"""
    from companies.models import Company
    
    # Get the company
    company = get_object_or_404(Company, id=company_id)
    
    # Check permissions - user must belong to the company
    user = request.user
    
    # More permissive permission check:
    # 1. Check if user is admin/staff
    if user.is_staff or user.is_superuser:
        # Admins can see all company silos
        pass
    else:
        # Get companies user has access to through UserCompanyRelation
        user_companies = list(user.company_relations.values_list('company', flat=True))
        
        # Check if user has profile with company
        has_company_profile = False
        if hasattr(user, 'profile') and hasattr(user.profile, 'company') and user.profile.company:
            has_company_profile = user.profile.company.id == company.id
            # Also add to user_companies for unified checking
            if has_company_profile:
                user_companies.append(company.id)
        
        # If user isn't associated with this company, deny access
        if company.id not in user_companies:
            raise PermissionDenied("You don't have permission to view this company's data silos.")
    
    # Get all data silos for the company
    data_silos = DataSilo.objects.filter(company=company)
    # Get all files across all silos for this company
    total_files = DataFile.objects.filter(data_silo__company=company).count()
    
    # If there are no silos but user has permission, create a default silo
    if data_silos.count() == 0 and (user.is_staff or user.is_superuser or company.id in user_companies):
        default_silo = DataSilo.objects.create(
            name="Default Silo",
            description="Default data silo for company documents",
            company=company,
            created_by=user
        )
        messages.success(request, "Created a default data silo for your company.")
        return redirect('datasilo:silo_detail', slug=default_silo.slug)
    # If there's exactly one silo, redirect directly to it
    if data_silos.count() >= 1:
        return redirect('datasilo:silo_detail', slug=data_silos.first().slug)
    
    # Handle search
    search_query = request.GET.get('search', '')
    if search_query:
        data_silos = data_silos.filter(name__icontains=search_query)
    
    # Handle sorting
    sort_param = request.GET.get('sort', '-created_at')
    if sort_param in ['name', '-name', 'created_at', '-created_at', 'updated_at', '-updated_at']:
        data_silos = data_silos.order_by(sort_param)
    else:
        data_silos = data_silos.order_by('-created_at')
    
    return render(request, 'datasilo/company_silos.html', {
        'company': company,
        'data_silos': data_silos
    })
