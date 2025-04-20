"""
Service for sending notifications about report generation
"""
import logging
from typing import Dict, Any, List, Optional

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.contrib.auth import get_user_model

from reports.models import Report

User = get_user_model()
logger = logging.getLogger(__name__)

class ReportNotificationService:
    """
    Service for sending notifications about report generation
    """
    
    def notify_report_completion(self, report: Report) -> bool:
        """
        Send notifications about report generation completion
        
        Args:
            report: The report that was generated
            
        Returns:
            bool: True if notifications were sent successfully
        """
        try:
            # Find users to notify
            users_to_notify = self._get_users_to_notify(report)
            
            if not users_to_notify:
                logger.warning(f"No users to notify about report {report.id} completion")
                return True
            
            # Send notifications
            return self._send_notifications(report, users_to_notify)
            
        except Exception as e:
            logger.error(f"Error sending notifications for report {report.id}: {str(e)}")
            return False
    
    def notify_report_failure(self, report: Report, error: str) -> bool:
        """
        Send notifications about report generation failure
        
        Args:
            report: The report that failed to generate
            error: The error message
            
        Returns:
            bool: True if notifications were sent successfully
        """
        try:
            # Find users to notify (typically just the creator and admins)
            users_to_notify = self._get_admin_users(report)
            
            if not users_to_notify:
                logger.warning(f"No users to notify about report {report.id} failure")
                return True
            
            # Send failure notifications
            return self._send_failure_notifications(report, users_to_notify, error)
            
        except Exception as e:
            logger.error(f"Error sending failure notifications for report {report.id}: {str(e)}")
            return False
    
    def _get_users_to_notify(self, report: Report) -> List[User]:
        """
        Get users to notify about report completion
        
        Args:
            report: The report that was generated
            
        Returns:
            List[User]: List of users to notify
        """
        users = set()
        
        # Always notify the creator
        if report.created_by:
            users.add(report.created_by)
        
        # Notify project members if applicable
        if report.project:
            # Get project managers
            users.update(report.project.members.filter(userprojectrelation__role='manager'))
        
        # Notify company admins if applicable
        if report.company:
            # Get company admins
            users.update(report.company.members.filter(usercompanyrelation__role__in=['admin', 'owner']))
        
        return list(users)
    
    def _get_admin_users(self, report: Report) -> List[User]:
        """
        Get admin users to notify about report failure
        
        Args:
            report: The report that failed
            
        Returns:
            List[User]: List of admin users to notify
        """
        users = set()
        
        # Always notify the creator
        if report.created_by:
            users.add(report.created_by)
        
        # Get superusers
        users.update(User.objects.filter(is_superuser=True))
        
        return list(users)
    
    def _send_notifications(self, report: Report, users: List[User]) -> bool:
        """
        Send notifications to users
        
        Args:
            report: The report that was generated
            users: The users to notify
            
        Returns:
            bool: True if notifications were sent successfully
        """
        success = True
        
        # Get the report URL
        report_url = settings.BASE_URL + reverse('reports:report_detail', kwargs={'slug': report.slug})
        
        # For each user
        for user in users:
            # Skip users without email
            if not user.email:
                continue
            
            # Prepare email content
            subject = f"Report '{report.title}' has been generated"
            html_message = render_to_string('reports/emails/report_completion.html', {
                'report': report,
                'user': user,
                'report_url': report_url
            })
            text_message = f"""
Report '{report.title}' has been generated and is now available for viewing.

View the report here: {report_url}

This is an automated message from Zignal.
            """
            
            # Send email
            try:
                send_mail(
                    subject=subject,
                    message=text_message,
                    html_message=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )
            except Exception as e:
                logger.error(f"Error sending email to {user.email}: {str(e)}")
                success = False
        
        return success
    
    def _send_failure_notifications(self, report: Report, users: List[User], error: str) -> bool:
        """
        Send failure notifications to users
        
        Args:
            report: The report that failed
            users: The users to notify
            error: The error message
            
        Returns:
            bool: True if notifications were sent successfully
        """
        success = True
        
        # Get the report URL
        report_url = settings.BASE_URL + reverse('reports:report_detail', kwargs={'slug': report.slug})
        
        # For each user
        for user in users:
            # Skip users without email
            if not user.email:
                continue
            
            # Prepare email content
            subject = f"Failed to generate report '{report.title}'"
            html_message = render_to_string('reports/emails/report_failure.html', {
                'report': report,
                'user': user,
                'report_url': report_url,
                'error': error
            })
            text_message = f"""
Report '{report.title}' failed to generate.

Error: {error}

View the report here: {report_url}

This is an automated message from Zignal.
            """
            
            # Send email
            try:
                send_mail(
                    subject=subject,
                    message=text_message,
                    html_message=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False
                )
            except Exception as e:
                logger.error(f"Error sending email to {user.email}: {str(e)}")
                success = False
        
        return success 