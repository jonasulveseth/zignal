@login_required
def file_upload(request, slug):
    """Upload a file to a data silo"""
    # Configure Redis SSL settings immediately
    try:
        import redis
        import ssl
        import os
        from redis.connection import ConnectionPool
        
        # Check if we're in a production environment with SSL Redis
        redis_url = os.environ.get('REDIS_URL', '')
        if redis_url.startswith('rediss://'):
            # Configure SSL settings
            redis_ssl_settings = {
                'ssl_cert_reqs': ssl.CERT_NONE,
                'ssl_check_hostname': False,
            }
            
            # Apply SSL settings to the global default connection pool
            default_connection_pool = getattr(ConnectionPool, '_connection_pool_cache', {})
            for url, pool in default_connection_pool.items():
                if url.startswith('rediss://'):
                    pool.connection_kwargs.update(redis_ssl_settings)
                    
            # Set environment variables for Celery to use these settings
            os.environ['CELERY_REDIS_BACKEND_USE_SSL'] = 'True'
            os.environ['CELERY_BROKER_USE_SSL'] = 'True'
            
            # Explicitly configure Redis connection for this request
            redis_client = redis.Redis.from_url(
                redis_url,
                ssl_cert_reqs=None,
                ssl_check_hostname=False
            )
            # Make a simple ping to test the connection
            redis_client.ping()
            
            print("Redis SSL settings applied successfully")
    except Exception as e:
        print(f"Redis SSL configuration error: {str(e)}")
    
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