from django.core.management.base import BaseCommand
from django.db import transaction
from companies.models import Company
from core.tasks import create_default_project_and_silo
from projects.models import Project
from datasilo.models import DataSilo

class Command(BaseCommand):
    help = 'Create default project and data silo for companies that do not have them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Specify a single company ID to create resources for',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if the company already has projects or data silos',
        )

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        force = options.get('force', False)
        
        if company_id:
            companies = Company.objects.filter(id=company_id)
            if not companies.exists():
                self.stdout.write(self.style.ERROR(f'Company with ID {company_id} not found.'))
                return
        else:
            companies = Company.objects.all()
            
        self.stdout.write(self.style.WARNING(f'Processing {companies.count()} companies...'))
        
        for company in companies:
            self.process_company(company, force)
        
        self.stdout.write(self.style.SUCCESS('Default resources creation completed.'))
    
    def process_company(self, company, force=False):
        """Process a single company to create default resources"""
        has_projects = Project.objects.filter(company=company).exists()
        has_silos = DataSilo.objects.filter(company=company).exists()
        
        if has_projects and has_silos and not force:
            self.stdout.write(self.style.WARNING(
                f'Company "{company.name}" (ID: {company.id}) already has projects and data silos. '
                f'Use --force to create anyway.'
            ))
            return
        
        self.stdout.write(f'Creating default resources for "{company.name}" (ID: {company.id})...')
        
        # Get the company creator or first admin
        user = None
        if company.created_by:
            user = company.created_by
        else:
            # Try to find an admin
            relation = company.user_relations.filter(role='admin').first()
            if relation:
                user = relation.user
            else:
                # Use any user related to the company
                relation = company.user_relations.first()
                if relation:
                    user = relation.user
        
        if not user:
            self.stdout.write(self.style.ERROR(
                f'No user found for company "{company.name}" (ID: {company.id}). Cannot create resources.'
            ))
            return
        
        try:
            with transaction.atomic():
                # Execute task synchronously for the management command
                result = create_default_project_and_silo(company.id, user.id)
                
                if result.get('success'):
                    self.stdout.write(self.style.SUCCESS(
                        f'Successfully created resources for "{company.name}": '
                        f'Project ID: {result["project_id"]}, '
                        f'Project Silo ID: {result["project_silo_id"]}, '
                        f'Company Silo ID: {result["company_silo_id"]}'
                    ))
                else:
                    self.stdout.write(self.style.ERROR(
                        f'Failed to create resources for "{company.name}": {result.get("error", "Unknown error")}'
                    ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error processing company "{company.name}": {str(e)}')) 