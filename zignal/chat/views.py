from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from companies.models import Company
from .models import Thread, Message
from .services.openai_service import ChatOpenAIService
import json
import logging
import time
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)

@login_required
def force_new_thread(request):
    """Forcefully create a new thread and show debug info"""
    # Get the user's company
    company_relation = request.user.company_relations.first()
    if not company_relation:
        return HttpResponse("No company found for your account", content_type="text/plain")
    
    company = company_relation.company
    if not company.openai_assistant_id:
        return HttpResponse("Company does not have an OpenAI assistant configured", content_type="text/plain")
    
    debug_info = []
    debug_info.append(f"User: {request.user.email}")
    debug_info.append(f"Company: {company.name}")
    debug_info.append(f"Assistant ID: {company.openai_assistant_id}")
    
    # Create OpenAI client
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        default_headers={"OpenAI-Beta": "assistants=v2"}
    )
    debug_info.append(f"Created OpenAI client with API key ending in: {settings.OPENAI_API_KEY[-4:]}")
    
    # Try to create a thread directly
    thread_id = None
    error = None
    try:
        start_time = time.time()
        thread_result = client.beta.threads.create()
        duration = time.time() - start_time
        thread_id = thread_result.id
        debug_info.append(f"Created thread in {duration:.2f}s with ID: {thread_id}")
        
        # Verify thread exists
        retrieved = client.beta.threads.retrieve(thread_id=thread_id)
        debug_info.append(f"Retrieved thread: {retrieved.id}")
    except Exception as e:
        error = str(e)
        debug_info.append(f"ERROR: {error}")
    
    # If we have a thread ID, save to database
    if thread_id:
        try:
            thread = Thread.objects.create(
                user=request.user,
                company=company,
                title=f'Chat with {company.name}',
                openai_thread_id=thread_id
            )
            debug_info.append(f"Created thread in database with ID: {thread.id}")
            debug_info.append(f"OPENAI ID: {thread.openai_thread_id}")
            
            # Add a link to the chat view
            debug_info.append(f"<a href='/chat/' class='btn btn-primary mt-4'>Go to chat</a>")
            
        except Exception as e:
            debug_info.append(f"ERROR saving to database: {str(e)}")
    
    # Return debug info as plain text
    return HttpResponse("<br>".join(debug_info), content_type="text/html")

@login_required
def chat_view(request):
    """Render the chat interface"""
    # Get the user's company
    company_relation = request.user.company_relations.first()
    if not company_relation:
        return render(request, 'chat/chat.html', {'error': 'No company found for your account. Please join or create a company first.'})
    
    company = company_relation.company
    if not company.openai_assistant_id:
        return render(request, 'chat/chat.html', {'error': 'Company does not have an AI assistant configured. Please ask an administrator to set up the OpenAI assistant.'})
    
    # Log key information for debugging
    logger.info(f"Chat view accessed by user {request.user.id} for company {company.id}")
    logger.info(f"Company {company.name} has OpenAI assistant ID: {company.openai_assistant_id}")
    
    # Check for a specific action to create a new thread
    create_new = request.GET.get('new', False)
    if create_new:
        logger.info("User requested a new thread")
        
    # Get existing thread or prepare to create a new one
    thread = None
    error = None
    try:
        # Look for an existing thread if not explicitly creating a new one
        if not create_new:
            existing_threads = Thread.objects.filter(
                user=request.user,
                company=company
            ).order_by('-updated_at')
            
            if existing_threads.exists():
                thread = existing_threads.first()
                logger.info(f"Found existing thread {thread.id} with OpenAI ID: {thread.openai_thread_id or 'None'}")
        
        # Create a new thread if needed
        if thread is None or not thread.openai_thread_id or create_new:
            # If we're creating a new one but had an old one, mark that we're replacing it
            if thread and create_new:
                logger.info(f"Creating new thread to replace existing thread {thread.id}")
                
            # Create the thread in the database
            thread = Thread.objects.create(
                user=request.user,
                company=company,
                title=f'Chat with {company.name}'
            )
            logger.info(f"Created new thread {thread.id} in database")
            
            # Create the thread in OpenAI
            openai_service = ChatOpenAIService()
            result = openai_service.create_thread(company)
            
            if result['success']:
                thread.openai_thread_id = result['thread_id']
                thread.save()
                logger.info(f"Successfully created OpenAI thread: {thread.openai_thread_id}")
            else:
                error = result.get('error', 'Failed to create OpenAI thread')
                logger.error(f"Failed to create OpenAI thread: {error}")
                # Delete the thread if we can't create it in OpenAI
                thread.delete()
                thread = None
                
        # Final check to ensure thread has an OpenAI thread ID
        if thread and not thread.openai_thread_id:
            error = "Thread exists but has no OpenAI thread ID"
            logger.error(error)
    
    except Exception as e:
        logger.exception(f"Error in chat_view: {str(e)}")
        error = f"An unexpected error occurred: {str(e)}"
    
    if error:
        return render(request, 'chat/chat.html', {'error': error})
    
    if not thread:
        return render(request, 'chat/chat.html', {'error': 'Could not initialize chat thread. Please try again.'})
    
    return render(request, 'chat/chat.html', {
        'thread': thread,
        'company': company
    })

@login_required
def new_chat(request):
    """Redirect to chat view with a parameter to create a new thread"""
    return redirect(f"{request.path}?new=true")

@login_required
@require_http_methods(["GET"])
def thread_list(request):
    """Get all threads for the current user"""
    threads = Thread.objects.filter(user=request.user)
    data = [{
        'id': thread.id,
        'company': {
            'id': thread.company.id,
            'name': thread.company.name
        },
        'title': thread.title or f"Chat with {thread.company.name}",
        'created_at': thread.created_at,
        'updated_at': thread.updated_at,
    } for thread in threads]
    return JsonResponse({'threads': data})

@login_required
@require_http_methods(["POST"])
def create_thread(request):
    """Create a new thread for a company"""
    try:
        data = json.loads(request.body)
        company_id = data.get('company_id')
        
        if not company_id:
            return JsonResponse({'error': 'Company ID is required'}, status=400)
        
        company = get_object_or_404(Company, id=company_id)
        
        # Create thread in database
        thread = Thread.objects.create(
            company=company,
            user=request.user,
            title=data.get('title', '')
        )
        
        # Create thread in OpenAI
        openai_service = ChatOpenAIService()
        result = openai_service.create_thread(company)
        
        if result['success']:
            thread.openai_thread_id = result['thread_id']
            thread.save()
            
            return JsonResponse({
                'id': thread.id,
                'company': {
                    'id': thread.company.id,
                    'name': thread.company.name
                },
                'title': thread.title or f"Chat with {thread.company.name}",
                'created_at': thread.created_at,
                'updated_at': thread.updated_at,
            }, status=201)
        else:
            thread.delete()
            return JsonResponse({'error': result['error']}, status=500)
            
    except Exception as e:
        logger.error(f"Error creating thread: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["GET"])
def message_list(request, thread_id):
    """Get all messages in a thread"""
    thread = get_object_or_404(Thread, id=thread_id, user=request.user)
    messages = thread.messages.all()
    
    data = [{
        'id': msg.id,
        'role': msg.role,
        'content': msg.content,
        'timestamp': msg.timestamp,
    } for msg in messages]
    
    return JsonResponse({'messages': data})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def send_message(request, thread_id):
    """Send a message to the AI and get a response"""
    thread = get_object_or_404(Thread, id=thread_id, user=request.user)
    try:
        # Verify thread has an OpenAI thread ID
        if not thread.openai_thread_id:
            logger.error(f"Thread {thread.id} missing OpenAI thread ID")
            return JsonResponse({'error': 'This chat thread is not properly connected to OpenAI. Please create a new thread.'}, status=400)
        
        data = json.loads(request.body)
        message_content = data.get('message', '')
        if not message_content:
            return JsonResponse({'error': 'Message content is required'}, status=400)
            
        openai_service = ChatOpenAIService()
        # Add message to thread
        result = openai_service.add_message(thread, message_content)
        if not result['success']:
            return JsonResponse({'error': result['error']}, status=500)
            
        # Get assistant reply (not streaming)
        reply = None
        for content in openai_service.run_assistant(thread):
            content_data = json.loads(content)
            if 'content' in content_data:
                reply = content_data['content']
                break
            if 'error' in content_data:
                return JsonResponse({'error': content_data['error']}, status=500)
                
        if reply is None:
            return JsonResponse({'error': 'No response from assistant'}, status=500)
            
        return JsonResponse({'reply': reply})
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
