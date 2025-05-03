from django.shortcuts import render
import json
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.conf import settings
from .models import Agent, Conversation, Message, MeetingTranscript
from .services.openai_service import OpenAIService
from .services.portfolio_chat_service import PortfolioChatService
from .services.meetingbaas_service import MeetingBaaSService


def is_portfolio_manager(user):
    """Check if user is a portfolio manager"""
    return user.is_authenticated and user.user_type == 'portfolio_manager'


@login_required
@require_http_methods(["GET", "POST"])
def agent_list(request):
    """List all agents or create a new one"""
    if request.method == "GET":
        agents = Agent.objects.filter(active=True)
        data = [{
            'id': agent.id,
            'name': agent.name,
            'description': agent.description,
            'agent_type': agent.agent_type,
            'model': agent.model,
        } for agent in agents]
        return JsonResponse({'agents': data})
    
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            agent = Agent.objects.create(
                name=data.get('name', 'New Agent'),
                description=data.get('description', ''),
                agent_type=data.get('agent_type', 'chat'),
                model=data.get('model', 'gpt-4o-mini'),
                temperature=data.get('temperature', 0.7),
                max_tokens=data.get('max_tokens', 1000),
                system_prompt=data.get('system_prompt', ''),
                created_by=request.user
            )
            return JsonResponse({
                'id': agent.id,
                'name': agent.name,
                'description': agent.description,
                'agent_type': agent.agent_type,
                'model': agent.model,
            }, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def agent_detail(request, agent_id):
    """Get, update or delete an agent"""
    agent = get_object_or_404(Agent, id=agent_id)
    
    if request.method == "GET":
        return JsonResponse({
            'id': agent.id,
            'name': agent.name,
            'description': agent.description,
            'agent_type': agent.agent_type,
            'model': agent.model,
            'temperature': agent.temperature,
            'max_tokens': agent.max_tokens,
            'system_prompt': agent.system_prompt,
            'active': agent.active,
            'created_at': agent.created_at,
            'updated_at': agent.updated_at,
        })
    
    elif request.method == "PUT":
        try:
            data = json.loads(request.body)
            agent.name = data.get('name', agent.name)
            agent.description = data.get('description', agent.description)
            agent.agent_type = data.get('agent_type', agent.agent_type)
            agent.model = data.get('model', agent.model)
            agent.temperature = data.get('temperature', agent.temperature)
            agent.max_tokens = data.get('max_tokens', agent.max_tokens)
            agent.system_prompt = data.get('system_prompt', agent.system_prompt)
            agent.active = data.get('active', agent.active)
            agent.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == "DELETE":
        agent.active = False
        agent.save()
        return JsonResponse({'status': 'success'})


@login_required
@require_http_methods(["GET", "POST"])
def conversation_list(request):
    """List all conversations or create a new one"""
    if request.method == "GET":
        conversations = Conversation.objects.filter(user=request.user)
        data = [{
            'id': conv.id,
            'title': conv.title or f"Conversation {conv.id}",
            'agent': {
                'id': conv.agent.id,
                'name': conv.agent.name,
                'agent_type': conv.agent.agent_type,
            },
            'created_at': conv.created_at,
            'updated_at': conv.updated_at,
        } for conv in conversations]
        return JsonResponse({'conversations': data})
    
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            agent_id = data.get('agent_id')
            agent = get_object_or_404(Agent, id=agent_id)
            
            conversation = Conversation.objects.create(
                agent=agent,
                user=request.user,
                title=data.get('title', '')
            )
            
            # Add initial system message if provided
            initial_message = data.get('initial_message')
            if initial_message:
                Message.objects.create(
                    conversation=conversation,
                    role='user',
                    content=initial_message
                )
                
                # Get first response from AI
                openai_service = OpenAIService()
                response = openai_service.chat_completion(conversation, initial_message)
            
            return JsonResponse({
                'id': conversation.id,
                'title': conversation.title or f"Conversation {conversation.id}",
                'agent': {
                    'id': conversation.agent.id,
                    'name': conversation.agent.name,
                },
                'created_at': conversation.created_at,
            }, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def conversation_detail(request, conversation_id):
    """Get, update or delete a conversation"""
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    
    if request.method == "GET":
        return JsonResponse({
            'id': conversation.id,
            'title': conversation.title or f"Conversation {conversation.id}",
            'agent': {
                'id': conversation.agent.id,
                'name': conversation.agent.name,
                'agent_type': conversation.agent.agent_type,
            },
            'created_at': conversation.created_at,
            'updated_at': conversation.updated_at,
        })
    
    elif request.method == "PUT":
        try:
            data = json.loads(request.body)
            conversation.title = data.get('title', conversation.title)
            conversation.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    elif request.method == "DELETE":
        conversation.delete()
        return JsonResponse({'status': 'success'})


@login_required
def message_list(request, conversation_id):
    """Get all messages in a conversation"""
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    messages = conversation.messages.all()
    
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
def chat(request, conversation_id):
    """Send a message to the AI and get a response"""
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        message_content = data.get('message', '')
        
        if not message_content:
            return JsonResponse({'error': 'Message content is required'}, status=400)
        
        openai_service = OpenAIService()
        response = openai_service.chat_completion(conversation, message_content)
        
        return JsonResponse({
            'response': response['response'],
            'usage': response['usage']
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["GET", "POST"])
def stream_chat(request, conversation_id):
    """Stream a response from the AI"""
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            message_content = data.get('message', '')
        else:  # GET
            message_content = request.GET.get('message', '')
        
        if not message_content:
            return JsonResponse({'error': 'Message content is required'}, status=400)
        
        openai_service = OpenAIService()
        
        def event_stream():
            for content in openai_service.streaming_chat_completion(conversation, message_content):
                yield f"data: {json.dumps({'content': content})}\n\n"
        
        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_portfolio_manager)
@require_http_methods(["GET", "POST"])
def portfolio_conversation(request):
    """Get or create a global conversation for portfolio managers"""
    try:
        portfolio_service = PortfolioChatService(request.user)
        conversation = portfolio_service.get_or_create_global_conversation()
        
        return JsonResponse({
            'id': conversation.id,
            'title': conversation.title,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_portfolio_manager)
@require_http_methods(["GET"])
def portfolio_conversation_messages(request, conversation_id):
    """Get messages for a specific portfolio conversation"""
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    
    # Verify this is a portfolio conversation
    if conversation.agent.name != 'Portfolio Global Agent':
        return JsonResponse({'error': 'Not a portfolio conversation'}, status=403)
    
    messages = conversation.messages.all()
    data = [{
        'id': message.id,
        'role': message.role,
        'content': message.content,
        'timestamp': message.timestamp.isoformat()
    } for message in messages]
    
    return JsonResponse({'messages': data})


@login_required
@user_passes_test(is_portfolio_manager)
@csrf_exempt
@require_http_methods(["POST"])
def portfolio_chat(request, conversation_id):
    """Send a message to the portfolio chat AI and get a response"""
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    
    # Verify this is a portfolio conversation
    if conversation.agent.name != 'Portfolio Global Agent':
        return JsonResponse({'error': 'Not a portfolio conversation'}, status=403)
    
    try:
        data = json.loads(request.body)
        message_content = data.get('message', '')
        
        if not message_content:
            return JsonResponse({'error': 'Message content is required'}, status=400)
        
        portfolio_service = PortfolioChatService(request.user)
        response = portfolio_service.get_ai_response(conversation, message_content)
        
        return JsonResponse({
            'response': response['response'],
            'usage': response['usage']
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_portfolio_manager)
@csrf_exempt
@require_http_methods(["GET", "POST"])
def portfolio_stream_chat(request, conversation_id):
    """Stream a response from the portfolio chat AI"""
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    
    # Verify this is a portfolio conversation
    if conversation.agent.name != 'Portfolio Global Agent':
        return JsonResponse({'error': 'Not a portfolio conversation'}, status=403)
    
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            message_content = data.get('message', '')
        else:  # GET
            message_content = request.GET.get('message', '')
        
        if not message_content:
            return JsonResponse({'error': 'Message content is required'}, status=400)
        
        portfolio_service = PortfolioChatService(request.user)
        
        def event_stream():
            for content in portfolio_service.stream_ai_response(conversation, message_content):
                yield f"data: {json.dumps({'content': content})}\n\n"
        
        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET", "POST"])
def meeting_list(request):
    """List all meetings or create a new one"""
    if request.method == "GET":
        # Get user's meeting transcripts
        user_meetings = MeetingTranscript.objects.filter(scheduled_by=request.user).order_by('-scheduled_time')
        
        context = {
            'meetings': user_meetings
        }
        return render(request, 'agents/meeting_list.html', context)
    
    elif request.method == "POST":
        # Create a new meeting
        meeting_title = request.POST.get('meeting_title')
        meeting_platform = request.POST.get('platform')
        meeting_url = request.POST.get('meeting_url')
        scheduled_time_str = request.POST.get('scheduled_time')
        project_id = request.POST.get('project_id')
        company_id = request.POST.get('company_id')
        
        if not meeting_title or not meeting_platform or not meeting_url or not scheduled_time_str:
            messages.error(request, "Please fill in all required fields")
            return redirect('agents:meeting_list')
        
        try:
            from datetime import datetime
            # Parse scheduled time
            scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%dT%H:%M')
            
            # Create meeting transcript record
            meeting = MeetingTranscript.objects.create(
                meeting_id=f"meeting_{int(datetime.now().timestamp())}",
                meeting_title=meeting_title,
                platform=meeting_platform,
                meeting_url=meeting_url,
                scheduled_time=scheduled_time,
                status='scheduled',
                scheduled_by=request.user
            )
            
            # Associate with project if provided
            if project_id:
                from projects.models import Project
                project = get_object_or_404(Project, id=project_id)
                meeting.project = project
            
            # Associate with company if provided
            if company_id:
                from companies.models import Company
                company = get_object_or_404(Company, id=company_id)
                meeting.company = company
            
            meeting.save()
            
            messages.success(request, "Meeting scheduled successfully!")
            
            # Schedule the Meeting BaaS bot if API key is available
            if settings.MEETINGBAAS_API_KEY:
                try:
                    service = MeetingBaaSService()
                    service.create_bot(meeting, settings.HOST_URL)
                    messages.success(request, "Meeting bot has been scheduled")
                except Exception as e:
                    messages.error(request, f"Error scheduling meeting bot: {str(e)}")
            
            return redirect('agents:meeting_detail', meeting_id=meeting.id)
        
        except Exception as e:
            messages.error(request, f"Error scheduling meeting: {str(e)}")
            return redirect('agents:meeting_list')


@login_required
def meeting_detail(request, meeting_id):
    """View a meeting transcript"""
    meeting = get_object_or_404(MeetingTranscript, id=meeting_id)
    
    # Check if user has permission to view this meeting
    if meeting.scheduled_by != request.user:
        # Check if user is associated with the project or company
        has_permission = False
        
        if meeting.project:
            if request.user in meeting.project.user_relations.values_list('user', flat=True):
                has_permission = True
        
        if not has_permission and meeting.company:
            if request.user in meeting.company.user_relations.values_list('user', flat=True):
                has_permission = True
        
        if not has_permission and not request.user.is_staff:
            messages.error(request, "You don't have permission to view this meeting")
            return redirect('agents:meeting_list')
    
    context = {
        'meeting': meeting,
    }
    
    # If meeting has a conversation, get messages
    if meeting.conversation:
        messages_list = meeting.conversation.messages.all()
        context['conversation_messages'] = messages_list
    
    return render(request, 'agents/meeting_detail.html', context)


@login_required
def cancel_meeting(request, meeting_id):
    """Cancel a scheduled meeting"""
    meeting = get_object_or_404(MeetingTranscript, id=meeting_id)
    
    # Check permission
    if meeting.scheduled_by != request.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to cancel this meeting")
        return redirect('agents:meeting_list')
    
    # Can only cancel scheduled meetings
    if meeting.status != 'scheduled':
        messages.error(request, f"Cannot cancel a meeting with status '{meeting.get_status_display()}'")
        return redirect('agents:meeting_detail', meeting_id=meeting.id)
    
    # Cancel Meeting BaaS bot if API key is available
    if settings.MEETINGBAAS_API_KEY and meeting.meetingbaas_bot_id:
        service = MeetingBaaSService()
        if service.cancel_bot(meeting):
            messages.success(request, "Meeting bot canceled successfully")
        else:
            messages.error(request, "Failed to cancel meeting bot")
    
    # Update status regardless of API result
    meeting.status = 'cancelled'
    meeting.save()
    
    messages.success(request, "Meeting canceled successfully")
    return redirect('agents:meeting_list')


@csrf_exempt
@require_POST
def meeting_webhook(request, meeting_id):
    """
    Webhook endpoint for Meeting BaaS to send updates and transcripts
    
    This endpoint is exempt from CSRF protection and authentication
    since it's called by the Meeting BaaS service.
    """
    try:
        meeting = get_object_or_404(MeetingTranscript, id=meeting_id)
        
        # Parse webhook data
        webhook_data = json.loads(request.body)
        
        # Process webhook
        service = MeetingBaaSService()
        service.process_webhook(meeting, webhook_data)
        
        return HttpResponse(status=200)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing meeting webhook: {str(e)}")
        return HttpResponse(status=500)
