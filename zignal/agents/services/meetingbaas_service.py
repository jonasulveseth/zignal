"""
Service for integrating with Meeting BaaS
"""
import os
import json
import logging
import requests
from datetime import datetime, timedelta
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from ..models import Agent, Conversation, Message, MeetingTranscript

logger = logging.getLogger(__name__)

class MeetingBaaSService:
    """
    Service for interacting with Meeting BaaS API
    """
    
    def __init__(self):
        """Initialize the Meeting BaaS service"""
        self.api_key = settings.MEETINGBAAS_API_KEY
        self.api_url = settings.MEETINGBAAS_API_URL
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def create_bot(self, meeting_transcript, host_url):
        """
        Create a bot for a meeting via Meeting BaaS API
        
        Args:
            meeting_transcript: MeetingTranscript object
            host_url: Host URL for webhook callback
        
        Returns:
            dict: Response from the API
        """
        webhook_url = f"{host_url}{reverse('agents:meeting_webhook', args=[meeting_transcript.id])}"
        
        # Prepare bot configuration based on platform
        bot_config = {
            'meetingUrl': meeting_transcript.meeting_url,
            'platform': meeting_transcript.platform,
            'webhookUrl': webhook_url,
        }
        
        # Add platform-specific configuration if needed
        if meeting_transcript.platform == 'zoom':
            # If using Zoom, we may need to add specific configurations
            pass
        elif meeting_transcript.platform == 'teams':
            # Teams specific configuration
            pass
        elif meeting_transcript.platform == 'google_meet':
            # Google Meet specific configuration
            pass
        
        try:
            response = requests.post(
                f"{self.api_url}/bots",
                headers=self.headers,
                json=bot_config
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Update the meeting transcript with the bot ID and webhook ID
            meeting_transcript.meetingbaas_bot_id = data.get('botId')
            meeting_transcript.meetingbaas_webhook_id = data.get('webhookId')
            meeting_transcript.status = 'scheduled'
            meeting_transcript.save()
            
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating Meeting BaaS bot: {str(e)}")
            meeting_transcript.status = 'failed'
            meeting_transcript.save()
            raise
    
    def cancel_bot(self, meeting_transcript):
        """
        Cancel a scheduled bot
        
        Args:
            meeting_transcript: MeetingTranscript object
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not meeting_transcript.meetingbaas_bot_id:
            logger.error("No bot ID available to cancel")
            return False
        
        try:
            response = requests.delete(
                f"{self.api_url}/bots/{meeting_transcript.meetingbaas_bot_id}",
                headers=self.headers
            )
            response.raise_for_status()
            
            # Update meeting transcript status
            meeting_transcript.status = 'cancelled'
            meeting_transcript.save()
            
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error cancelling Meeting BaaS bot: {str(e)}")
            return False
    
    def process_webhook(self, meeting_transcript, webhook_data):
        """
        Process webhook data from Meeting BaaS
        
        Args:
            meeting_transcript: MeetingTranscript object
            webhook_data: Dict containing webhook data
        
        Returns:
            bool: True if successful, False otherwise
        """
        event_type = webhook_data.get('event')
        
        if event_type == 'meeting.started':
            meeting_transcript.status = 'in_progress'
            meeting_transcript.save()
            return True
        
        elif event_type == 'meeting.ended':
            # Meeting ended, update status
            meeting_transcript.status = 'completed'
            
            # If there's a transcript in the webhook data
            if 'transcript' in webhook_data:
                transcript_text = webhook_data.get('transcript', '')
                meeting_transcript.transcript_raw = transcript_text
                
                # Create or update an agent conversation with the transcript
                self._create_conversation_from_transcript(meeting_transcript, transcript_text)
                
                # Generate a summary if configured
                if hasattr(settings, 'GENERATE_MEETING_SUMMARIES') and settings.GENERATE_MEETING_SUMMARIES:
                    self._generate_summary(meeting_transcript)
            
            # If recording URL is available
            if 'recordingUrl' in webhook_data:
                meeting_transcript.recording_url = webhook_data.get('recordingUrl')
            
            # Update meeting duration if available
            if 'durationSeconds' in webhook_data:
                duration_seconds = webhook_data.get('durationSeconds', 0)
                meeting_transcript.duration_minutes = int(duration_seconds / 60)
            
            meeting_transcript.save()
            return True
            
        elif event_type == 'transcription.created':
            # New transcription available
            transcript_text = webhook_data.get('transcript', '')
            meeting_transcript.transcript_raw = transcript_text
            meeting_transcript.save()
            
            # Create a conversation from the transcript
            self._create_conversation_from_transcript(meeting_transcript, transcript_text)
            return True
            
        elif event_type == 'error':
            # Handle error
            error_message = webhook_data.get('message', 'Unknown error')
            logger.error(f"Meeting BaaS error: {error_message}")
            
            meeting_transcript.status = 'failed'
            meeting_transcript.save()
            return False
            
        # Unknown event type
        logger.warning(f"Unknown webhook event type: {event_type}")
        return False
    
    def _create_conversation_from_transcript(self, meeting_transcript, transcript_text):
        """
        Create or update a conversation from the transcript
        
        Args:
            meeting_transcript: MeetingTranscript object
            transcript_text: String containing the transcript
        """
        # If conversation already exists, use it, otherwise create one
        conversation = meeting_transcript.conversation
        
        if not conversation:
            # Try to find an existing meeting agent or create one
            try:
                agent = Agent.objects.get(
                    agent_type='meeting',
                    name='Meeting Transcript Agent',
                    active=True
                )
            except Agent.DoesNotExist:
                # Create a meeting agent
                agent = Agent.objects.create(
                    name='Meeting Transcript Agent',
                    description='Agent for processing meeting transcripts',
                    agent_type='meeting',
                    system_prompt="You are a helpful assistant that can answer questions about meeting transcripts. "
                                 "You can summarize meetings, extract action items, and provide insights.",
                    created_by=meeting_transcript.scheduled_by
                )
            
            # Create a new conversation
            conversation = Conversation.objects.create(
                agent=agent,
                user=meeting_transcript.scheduled_by,
                title=f"Meeting: {meeting_transcript.meeting_title}"
            )
            
            # Associate the conversation with the meeting transcript
            meeting_transcript.conversation = conversation
            meeting_transcript.save()
        
        # Add the transcript as a system message in the conversation
        Message.objects.create(
            conversation=conversation,
            role='system',
            content=f"Transcript from meeting \"{meeting_transcript.meeting_title}\" on "
                   f"{meeting_transcript.scheduled_time.strftime('%Y-%m-%d %H:%M')}:\n\n{transcript_text}"
        )
    
    def _generate_summary(self, meeting_transcript):
        """
        Generate a summary of the meeting transcript using AI
        
        Args:
            meeting_transcript: MeetingTranscript object
        """
        from .openai_service import OpenAIService
        
        if not meeting_transcript.transcript_raw:
            logger.warning("Cannot generate summary: No transcript available")
            return
        
        try:
            openai_service = OpenAIService()
            
            # Prepare prompt for summarization
            prompt = (
                f"Please summarize the following meeting transcript. Include main topics discussed, "
                f"key decisions, action items, and any deadlines mentioned:\n\n"
                f"{meeting_transcript.transcript_raw}"
            )
            
            # Create a temporary conversation for the summary generation
            conversation = Conversation.objects.create(
                agent=meeting_transcript.conversation.agent,
                user=meeting_transcript.scheduled_by,
                title=f"Summary: {meeting_transcript.meeting_title}"
            )
            
            # Add the prompt as a user message
            Message.objects.create(
                conversation=conversation,
                role='user',
                content=prompt
            )
            
            # Get a response from OpenAI
            response = openai_service.chat_completion(conversation)
            
            # Save the summary
            meeting_transcript.transcript_summary = response['response']
            meeting_transcript.save()
            
            # Clean up the temporary conversation
            conversation.delete()
            
        except Exception as e:
            logger.error(f"Error generating meeting summary: {str(e)}")
            # Don't fail if summary generation fails 