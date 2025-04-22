import logging
import base64
import tempfile
from email.utils import parseaddr
import re
from datetime import datetime
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import IncomingEmail, EmailAttachment
from datasilo.models import DataSilo, DataFile
from agents.models import MeetingTranscript
from agents.services.meetingbaas_service import MeetingBaaSService
from .signals import email_received, email_with_attachments_received, meeting_email_received

logger = logging.getLogger(__name__)

class EmailProcessingService:
    """
    Service for processing incoming emails from Mailgun
    - Saves email and attachments to the database
    - Stores emails in the correct data silo
    - Handles meeting scheduling from email content
    """
    
    def __init__(self):
        self.meetingbaas_service = MeetingBaaSService()
    
    def process_incoming_email(self, mailgun_data):
        """
        Process incoming email data from Mailgun webhook
        
        Args:
            mailgun_data: Dict containing Mailgun webhook data
            
        Returns:
            IncomingEmail: The created email object
        """
        try:
            # Extract email data
            sender = mailgun_data.get('sender', '')
            recipient = mailgun_data.get('recipient', '')
            subject = mailgun_data.get('subject', '')
            body_plain = mailgun_data.get('body-plain', '')
            body_html = mailgun_data.get('body-html', '')
            stripped_text = mailgun_data.get('stripped-text', '')
            stripped_html = mailgun_data.get('stripped-html', '')
            message_id = mailgun_data.get('Message-Id', '')
            timestamp = mailgun_data.get('timestamp')
            
            # Create IncomingEmail record
            with transaction.atomic():
                email = IncomingEmail.objects.create(
                    sender=sender,
                    recipient=recipient,
                    subject=subject,
                    body_plain=body_plain,
                    body_html=body_html,
                    stripped_text=stripped_text,
                    stripped_html=stripped_html,
                    message_id=message_id,
                    mailgun_timestamp=timestamp,
                    mailgun_id=mailgun_data.get('token', ''),
                    status='processing'
                )
                
                # Process attachments if any
                attachments = self._process_attachments(email, mailgun_data)
                
                # Find appropriate data silo
                data_silo = self._find_data_silo(email)
                if data_silo:
                    email.data_silo = data_silo
                    email.save()
                    
                    # Save email content as a file in the data silo
                    self._save_email_to_data_silo(email, data_silo)
                
                # Check if email is for meeting scheduling
                meeting_created = False
                meeting = None
                if self._is_meeting_scheduling_email(email):
                    meeting = self._schedule_meeting(email)
                    meeting_created = email.meeting_created
                
                # Mark as processed
                email.mark_as_processed()
                
                # Send signals
                email_received.send(sender=self.__class__, email=email)
                
                if attachments:
                    email_with_attachments_received.send(
                        sender=self.__class__, 
                        email=email,
                        attachments=attachments
                    )
                
                if meeting_created and meeting:
                    meeting_email_received.send(
                        sender=self.__class__,
                        email=email,
                        meeting=meeting
                    )
                
            return email
        
        except Exception as e:
            logger.error(f"Error processing incoming email: {str(e)}")
            if 'email' in locals():
                email.mark_as_failed()
            raise
    
    def _process_attachments(self, email, mailgun_data):
        """
        Process and save email attachments
        
        Args:
            email: IncomingEmail object
            mailgun_data: Dict containing Mailgun webhook data
            
        Returns:
            list: List of EmailAttachment objects created
        """
        attachments = []
        
        # Get number of attachments
        attachment_count = int(mailgun_data.get('attachment-count', 0))
        
        for i in range(1, attachment_count + 1):
            attachment_key = f'attachment-{i}'
            
            if attachment_key in mailgun_data:
                attachment = mailgun_data[attachment_key]
                
                if hasattr(attachment, 'file'):
                    # For parsed multipart requests (Django parses the files)
                    file_obj = attachment
                    filename = attachment.name
                    content_type = attachment.content_type
                    size = attachment.size
                    
                    # Create attachment record
                    email_attachment = EmailAttachment.objects.create(
                        email=email,
                        filename=filename,
                        content_type=content_type,
                        size=size
                    )
                    
                    # Save the file
                    email_attachment.file.save(filename, file_obj)
                    attachments.append(email_attachment)
        
        return attachments
    
    def _find_data_silo(self, email):
        """
        Find the appropriate data silo for storing the email
        Currently, looks for a silo named 'Emails' in the system
        
        Args:
            email: IncomingEmail object
            
        Returns:
            DataSilo: The appropriate data silo or None
        """
        # Try to find an 'Emails' data silo
        try:
            # First, look for company-specific email silos
            company_email_silo = DataSilo.objects.filter(name='Emails', company__isnull=False).first()
            if company_email_silo:
                return company_email_silo
            
            # Then try project-specific silos
            project_email_silo = DataSilo.objects.filter(name='Emails', project__isnull=False).first()
            if project_email_silo:
                return project_email_silo
            
            # If no 'Emails' silo exists, create one for the first company
            from companies.models import Company
            default_company = Company.objects.first()
            
            if default_company:
                email_silo, created = DataSilo.objects.get_or_create(
                    name='Emails',
                    company=default_company,
                    defaults={
                        'description': 'Repository for incoming emails received via Mailgun',
                    }
                )
                return email_silo
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding data silo for email: {str(e)}")
            return None
    
    def _save_email_to_data_silo(self, email, data_silo):
        """
        Save the email content as a DataFile in the data silo
        
        Args:
            email: IncomingEmail object
            data_silo: DataSilo object
        """
        if not data_silo:
            return
        
        try:
            # Create a file containing the email content
            email_date = email.received_at.strftime('%Y-%m-%d')
            filename = f"Email_{email_date}_{email.subject[:30]}.txt"
            
            # Sanitize filename
            filename = re.sub(r'[^\w\s.-]', '', filename)
            filename = re.sub(r'\s+', '_', filename)
            
            # Create email content
            content = f"""
From: {email.sender}
To: {email.recipient}
Subject: {email.subject}
Date: {email.received_at.strftime('%Y-%m-%d %H:%M:%S')}

{email.body_plain}
            """
            
            # Create a DataFile
            data_file = DataFile.objects.create(
                name=f"Email: {email.subject[:50]}",
                description=f"Email from {email.sender} received on {email_date}",
                file_type='document',
                content_type='text/plain',
                data_silo=data_silo,
                size=len(content),
                status='processed'
            )
            
            # Save the file content
            data_file.file.save(filename, ContentFile(content.encode('utf-8')))
            
            # Process attachments if any
            for attachment in email.attachments.all():
                # Create a DataFile for each attachment
                attachment_file = DataFile.objects.create(
                    name=f"Attachment: {attachment.filename}",
                    description=f"Attachment from email: {email.subject[:50]}",
                    file_type=self._determine_file_type(attachment.content_type, attachment.filename),
                    content_type=attachment.content_type,
                    data_silo=data_silo,
                    size=attachment.size,
                    status='processed'
                )
                
                # Save the attachment file
                attachment_file.file.save(attachment.filename, attachment.file.open())
                
                # Link the DataFile to the EmailAttachment
                attachment.data_file = attachment_file
                attachment.save()
                
        except Exception as e:
            logger.error(f"Error saving email to data silo: {str(e)}")
    
    def _determine_file_type(self, content_type, filename):
        """
        Determine the file type for a DataFile based on content type and filename
        
        Args:
            content_type: MIME type of the file
            filename: Name of the file
            
        Returns:
            str: The file type from DataFile.FILE_TYPE_CHOICES
        """
        if not content_type:
            return 'other'
        
        content_type = content_type.lower()
        
        if 'image/' in content_type:
            return 'image'
        elif 'text/plain' in content_type:
            return 'document'
        elif 'pdf' in content_type:
            return 'document'
        elif 'spreadsheet' in content_type or 'excel' in content_type or '.xls' in filename.lower():
            return 'spreadsheet'
        elif 'presentation' in content_type or 'powerpoint' in content_type or '.ppt' in filename.lower():
            return 'presentation'
        elif 'audio/' in content_type:
            return 'audio'
        elif 'video/' in content_type:
            return 'video'
        elif 'text/' in content_type or filename.endswith(('.py', '.js', '.html', '.css', '.java', '.php')):
            return 'code'
        else:
            return 'document'

    def _is_meeting_scheduling_email(self, email):
        """
        Check if the email is intended for meeting scheduling
        
        Args:
            email: IncomingEmail object
            
        Returns:
            bool: True if the email is for scheduling a meeting
        """
        # Check subject for meeting-related keywords
        subject_lower = email.subject.lower()
        if any(keyword in subject_lower for keyword in ['meeting', 'schedule', 'zoom', 'teams', 'google meet']):
            return True
        
        # Check body for meeting URLs
        body_lower = email.body_plain.lower()
        if any(platform in body_lower for platform in ['zoom.us/', 'teams.microsoft.com/', 'meet.google.com/']):
            return True
            
        return False
    
    def _schedule_meeting(self, email):
        """
        Extract meeting information from email and schedule a meeting
        
        Args:
            email: IncomingEmail object
            
        Returns:
            MeetingTranscript: The created meeting object or None
        """
        try:
            # Extract meeting information
            meeting_info = self._extract_meeting_info(email)
            
            if not meeting_info:
                logger.warning(f"Could not extract meeting info from email {email.id}")
                return None
                
            # Create a MeetingTranscript object
            meeting = MeetingTranscript.objects.create(
                meeting_id=f"mail_{email.id}",
                meeting_title=meeting_info.get('title', email.subject),
                platform=meeting_info.get('platform', 'zoom'),
                meeting_url=meeting_info.get('url', ''),
                scheduled_time=meeting_info.get('time', timezone.now()),
                status='scheduled',
                company=meeting_info.get('company', None),
                project=meeting_info.get('project', None),
                scheduled_by=None  # No user in this case
            )
            
            # Link meeting to email
            email.meeting_created = True
            email.meeting_transcript = meeting
            email.save()
            
            # Schedule the Meeting BaaS bot
            if settings.MEETINGBAAS_API_KEY:
                try:
                    self.meetingbaas_service.create_bot(meeting, settings.HOST_URL)
                    logger.info(f"Scheduled meeting bot for meeting {meeting.id}")
                except Exception as e:
                    logger.error(f"Error scheduling meeting bot: {str(e)}")
            
            return meeting
            
        except Exception as e:
            logger.error(f"Error scheduling meeting: {str(e)}")
            return None
    
    def _extract_meeting_info(self, email):
        """
        Extract meeting information from email content
        
        Args:
            email: IncomingEmail object
            
        Returns:
            dict: Meeting information with keys: title, platform, url, time, company, project
        """
        # Initialize meeting info
        meeting_info = {
            'title': email.subject,
            'platform': None,
            'url': None,
            'time': timezone.now(),
            'company': None,
            'project': None
        }
        
        # Extract platform and URL
        body = email.body_plain
        
        # Look for Zoom meeting links
        zoom_match = re.search(r'(https?://(?:[\w-]+\.)?zoom\.us/[^\s]+)', body)
        if zoom_match:
            meeting_info['platform'] = 'zoom'
            meeting_info['url'] = zoom_match.group(1)
        
        # Look for Microsoft Teams meeting links
        teams_match = re.search(r'(https?://teams\.microsoft\.com/[^\s]+)', body)
        if teams_match:
            meeting_info['platform'] = 'teams'
            meeting_info['url'] = teams_match.group(1)
        
        # Look for Google Meet meeting links
        meet_match = re.search(r'(https?://meet\.google\.com/[^\s]+)', body)
        if meet_match:
            meeting_info['platform'] = 'google_meet'
            meeting_info['url'] = meet_match.group(1)
        
        # Extract meeting time - this is complex and would need more sophisticated parsing
        # For now, we'll use a simple regex to look for common date formats
        date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', body)
        time_match = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)', body)
        
        if date_match and time_match:
            try:
                date_str = date_match.group(1)
                time_str = time_match.group(1)
                
                # Convert to datetime object - this would need more sophisticated parsing in practice
                meeting_info['time'] = timezone.now()  # Placeholder
            except:
                pass
        
        # Find company and project based on email content
        # This would require more complex logic based on your specific business rules
        
        return meeting_info 