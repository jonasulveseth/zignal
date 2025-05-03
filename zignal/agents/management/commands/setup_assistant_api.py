from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from agents.models import Agent
from agents.services.openai_service import OpenAIService

User = get_user_model()

class Command(BaseCommand):
    help = 'Sets up the OpenAI Assistants API for the General Assistant and removes other assistants'

    def handle(self, *args, **options):
        # Delete all agents except the General Assistant
        general_assistant = None
        
        try:
            # Find the General Assistant
            general_assistant = Agent.objects.get(name='General Assistant', agent_type='chat')
            self.stdout.write(self.style.SUCCESS(f"Found General Assistant (ID: {general_assistant.id})"))
            
            # Delete all other agents
            count = Agent.objects.exclude(id=general_assistant.id).delete()[0]
            self.stdout.write(self.style.SUCCESS(f"Deleted {count} other agents"))
            
        except Agent.DoesNotExist:
            self.stdout.write(self.style.WARNING("General Assistant not found. Creating a new one..."))
            
            # Create the General Assistant
            general_assistant = Agent.objects.create(
                name='General Assistant',
                description='A general purpose AI assistant to help with various tasks.',
                agent_type='chat',
                model='gpt-4o-mini',
                temperature=0.7,
                max_tokens=1000,
                system_prompt='You are a helpful AI assistant for Zignal. Your role is to assist users with their queries and provide helpful information.',
                active=True
            )
            
            # Try to set created_by to a superuser if available
            try:
                superuser = User.objects.filter(is_superuser=True).first()
                if superuser:
                    general_assistant.created_by = superuser
                    general_assistant.save()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not set created_by: {e}"))
        
        # Update the General Assistant to use the Assistants API
        general_assistant.api_version = 'assistants'
        general_assistant.save()
        
        self.stdout.write(self.style.SUCCESS(f"Updated General Assistant to use Assistants API"))
        
        # Create the assistant in OpenAI
        openai_service = OpenAIService()
        
        try:
            assistant_id = openai_service.create_assistant(general_assistant)
            general_assistant.assistant_id = assistant_id
            general_assistant.save()
            
            self.stdout.write(self.style.SUCCESS(f"Created OpenAI Assistant with ID: {assistant_id}"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating OpenAI Assistant: {e}")) 