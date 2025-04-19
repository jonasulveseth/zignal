from django.shortcuts import render
import json
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import Agent, Conversation, Message
from .services.openai_service import OpenAIService


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
                model=data.get('model', 'gpt-4o'),
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
