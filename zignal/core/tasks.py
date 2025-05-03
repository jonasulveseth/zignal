from celery import shared_task
import logging
from django.utils import timezone
from projects.models import Project, UserProjectRelation
from datasilo.models import DataSilo
import time

logger = logging.getLogger(__name__)

@shared_task
def sample_task(arg):
    """
    A sample task to verify Celery is working
    """
    logger.info(f"Sample task executed with arg: {arg}")
    return f"Task completed with arg: {arg}"

@shared_task
def process_data(data_id):
    """
    Process data asynchronously
    """
    logger.info(f"Processing data with ID: {data_id}")
    # Add actual processing logic here
    return f"Data processing complete for ID: {data_id}"

@shared_task
def create_default_project_and_silo(company_id, user_id):
    """
    Create a default project and data silo for a newly created company
    
    Args:
        company_id (int): ID of the company
        user_id (int): ID of the user who created the company
        
    Returns:
        dict: Information about the created resources
    """
    from companies.models import Company
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        logger.info(f"Creating default project and silo for company ID: {company_id}")
        
        # Get company and user
        company = Company.objects.get(id=company_id)
        user = User.objects.get(id=user_id)
        
        # Create unique project name with timestamp to avoid slug collision
        timestamp = int(time.time())
        project_name = f"Default Project - {company.name} {timestamp}"
        
        # Create default project
        project = Project.objects.create(
            name=project_name,
            description=f"Default project for {company.name}",
            company=company,
            status='active',
            start_date=timezone.now().date(),
            created_by=user
        )
        
        # Create user-project relation
        UserProjectRelation.objects.create(
            user=user,
            project=project,
            role='manager'
        )
        
        logger.info(f"Created default project: {project.name} (ID: {project.id})")
        
        # Create default data silo linked to the project
        data_silo = DataSilo.objects.create(
            name=f"General Documents - {timestamp}",
            description=f"General document storage for {project.name}",
            project=project,
            company=company,
            created_by=user
        )
        
        logger.info(f"Created default data silo: {data_silo.name} (ID: {data_silo.id})")
        
        # Create default company-level data silo (not linked to project)
        company_silo = DataSilo.objects.create(
            name=f"Company Documents - {company.name} {timestamp}",
            description=f"Company-wide document storage for {company.name}",
            company=company,
            created_by=user
        )
        
        logger.info(f"Created company-level data silo: {company_silo.name} (ID: {company_silo.id})")
        
        return {
            "success": True,
            "project_id": project.id,
            "project_silo_id": data_silo.id,
            "company_silo_id": company_silo.id
        }
        
    except Exception as e:
        # Log detailed error info for easier debugging
        import traceback
        logger.error(f"Error creating default project and silo: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Log environment variables for debugging (only in non-production)
        import os
        from django.conf import settings
        if settings.DEBUG:
            redis_url = os.environ.get('REDIS_URL', 'not_set')
            celery_broker = os.environ.get('CELERY_BROKER_URL', 'not_set')
            celery_backend = os.environ.get('CELERY_RESULT_BACKEND', 'not_set')
            logger.debug(f"REDIS_URL: {redis_url[:10]}***")
            logger.debug(f"CELERY_BROKER_URL: {celery_broker[:10]}***")
            logger.debug(f"CELERY_RESULT_BACKEND: {celery_backend[:10]}***")
        
        return {
            "success": False,
            "error": str(e)
        } 