from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from agents.models import Agent

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a default agent for testing purposes'

    def add_arguments(self, parser):
        parser.add_argument('--name', type=str, default='General Assistant', help='Name of the agent')
        parser.add_argument('--type', type=str, default='chat', help='Type of agent (chat, report, meeting, email)')
        parser.add_argument('--model', type=str, default='gpt-3.5-turbo', help='LLM model to use')
        parser.add_argument('--username', type=str, help='Username of the user to set as creator')

    def handle(self, *args, **options):
        name = options['name']
        agent_type = options['type']
        model = options['model']
        username = options.get('username')
        
        # Find a user to set as creator
        created_by = None
        if username:
            try:
                created_by = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'User with username {username} not found'))
        
        if not created_by:
            # Get the first superuser
            try:
                created_by = User.objects.filter(is_superuser=True).first()
            except:
                self.stdout.write(self.style.WARNING('No superuser found'))
        
        # Create system prompt based on agent type
        system_prompt = ""
        if agent_type == 'chat':
            system_prompt = """You are a helpful assistant for Zignal, an investment tracking platform. 
Your goal is to help users with their investment tracking needs.
Be concise, professional, and helpful in your responses.
If you don't know something, be honest about it."""
        elif agent_type == 'report':
            system_prompt = """You are a report generation assistant for Zignal.
You help users generate reports about their investments and portfolios.
Focus on clear data presentation and actionable insights."""
        elif agent_type == 'meeting':
            system_prompt = """You are a meeting assistant for Zignal.
You help users prepare for, conduct, and follow up on meetings related to their investments.
Be professional, organized, and help keep meetings on track."""
        elif agent_type == 'email':
            system_prompt = """You are an email assistant for Zignal.
You help users draft, review, and respond to emails related to their investments.
Be professional, clear, and concise in your communications."""
        
        # Create the agent
        agent, created = Agent.objects.get_or_create(
            name=name,
            agent_type=agent_type,
            defaults={
                'description': f'Default {agent_type} agent for testing',
                'model': model,
                'temperature': 0.7,
                'max_tokens': 1000,
                'system_prompt': system_prompt,
                'created_by': created_by
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Successfully created agent: {agent.name}'))
        else:
            self.stdout.write(self.style.WARNING(f'Agent with name {name} already exists')) 