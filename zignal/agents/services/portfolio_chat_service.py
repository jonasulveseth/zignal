"""
Service for portfolio manager chat functionality
"""
import logging
from ..models import Agent, Conversation, Message
from .openai_service import OpenAIService
from companies.models import Company
from projects.models import Project
from datasilo.models import DataSilo, DataFile

logger = logging.getLogger(__name__)

class PortfolioChatService:
    """
    Service providing specialized chat functionality for portfolio managers
    """
    
    def __init__(self, user):
        """Initialize with the portfolio manager user"""
        self.user = user
        self.openai_service = OpenAIService()
        
    def get_portfolio_system_prompt(self):
        """
        Creates a system prompt that includes information about the portfolio manager's
        companies and projects for global context.
        """
        # Get all companies the portfolio manager has access to
        companies = Company.objects.filter(user_relations__user=self.user)
        company_names = [company.name for company in companies]
        
        # Get all projects the portfolio manager has access to
        projects = Project.objects.filter(user_relations__user=self.user)
        project_info = [f"{project.name} (Company: {project.company.name})" for project in projects]
        
        # Create the system prompt
        system_prompt = (
            f"You are a specialized AI assistant for portfolio manager {self.user.full_name}. "
            "Your role is to provide insights, answer questions, and help manage the portfolio "
            "of companies and projects.\n\n"
            
            f"The portfolio manager has access to the following companies:\n"
            f"{', '.join(company_names)}\n\n"
            
            f"And the following projects:\n"
            f"{', '.join(project_info)}\n\n"
            
            "You can answer questions about these companies and projects at a high level. "
            "For specific document questions, the user should access the specific project's AI agent. "
            "You are focused on providing portfolio-wide insights, comparisons between companies/projects, "
            "strategic advice, and best practices.\n\n"
            
            "Be professional, concise, and helpful. Offer data-driven insights when possible."
        )
        
        return system_prompt
    
    def get_or_create_global_conversation(self):
        """
        Gets an existing global conversation or creates a new one
        """
        # Try to find a global agent for portfolio managers
        try:
            global_agent = Agent.objects.get(
                agent_type='chat',
                name='Portfolio Global Agent',
                company__isnull=True,
                project__isnull=True,
                active=True
            )
        except Agent.DoesNotExist:
            # Create a new global agent if one doesn't exist
            global_agent = Agent.objects.create(
                name='Portfolio Global Agent',
                description='Global AI assistant for portfolio managers',
                agent_type='chat',
                system_prompt=self.get_portfolio_system_prompt(),
                created_by=self.user
            )
        
        # Find or create a conversation for this user with the global agent
        conversations = Conversation.objects.filter(
            agent=global_agent, 
            user=self.user
        ).order_by('-updated_at')
        
        if conversations.exists():
            return conversations.first()
        
        # Create a new conversation
        return Conversation.objects.create(
            agent=global_agent,
            user=self.user,
            title="Global Portfolio Chat"
        )
    
    def add_message_to_conversation(self, conversation, content, role='user'):
        """Add a message to the conversation"""
        message = Message.objects.create(
            conversation=conversation,
            role=role,
            content=content
        )
        return message
    
    def get_ai_response(self, conversation, message_content):
        """
        Get a response from the AI for the given message
        """
        # Update the system prompt with current portfolio data
        conversation.agent.system_prompt = self.get_portfolio_system_prompt()
        conversation.agent.save()
        
        # Get response using OpenAI service
        return self.openai_service.chat_completion(conversation, message_content)
        
    def stream_ai_response(self, conversation, message_content):
        """
        Stream a response from the AI
        """
        # Update the system prompt with current portfolio data
        conversation.agent.system_prompt = self.get_portfolio_system_prompt()
        conversation.agent.save()
        
        # Stream response using OpenAI service
        return self.openai_service.streaming_chat_completion(conversation, message_content) 