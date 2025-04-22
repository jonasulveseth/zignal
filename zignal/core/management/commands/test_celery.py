from django.core.management.base import BaseCommand
import time
from core.tasks import sample_task, process_data
from mail_receiver.tasks import process_incoming_email_task

class Command(BaseCommand):
    help = 'Test Celery tasks to verify they are working correctly'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            help='Specify which task to run (all, sample, process_data, email)',
            default='all'
        )

    def handle(self, *args, **options):
        task_type = options.get('task', 'all')
        
        if task_type in ['all', 'sample']:
            self.stdout.write(self.style.WARNING('Testing basic sample task...'))
            result = sample_task.delay('test_argument')
            self.stdout.write(self.style.SUCCESS(f'Sample task submitted with ID: {result.id}'))
            
            # Wait for task completion (only in development)
            self.stdout.write('Waiting for task to complete...')
            try:
                task_result = result.get(timeout=10)  # Wait up to 10 seconds
                self.stdout.write(self.style.SUCCESS(f'Task completed with result: {task_result}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error waiting for task: {str(e)}'))
        
        if task_type in ['all', 'process_data']:
            self.stdout.write(self.style.WARNING('Testing process_data task...'))
            result = process_data.delay('1234')
            self.stdout.write(self.style.SUCCESS(f'Data processing task submitted with ID: {result.id}'))
            
            try:
                task_result = result.get(timeout=10)
                self.stdout.write(self.style.SUCCESS(f'Task completed with result: {task_result}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error waiting for task: {str(e)}'))
        
        if task_type in ['all', 'email']:
            self.stdout.write(self.style.WARNING('Testing email processing task...'))
            # Create test email data
            test_email_data = {
                'sender': 'test@example.com',
                'recipient': 'test-recipient@zignal.com',
                'subject': 'Celery Test Email',
                'body-plain': 'This is a test email from the Celery test command.',
                'body-html': '<html><body><p>This is a test email from the Celery test command.</p></body></html>',
                'timestamp': time.time(),
                'token': 'test-token-123',
            }
            
            # Note: This will fail in production if attachments need handling
            # It's just for testing the celery worker connectivity
            try:
                result = process_incoming_email_task.delay(test_email_data)
                self.stdout.write(self.style.SUCCESS(f'Email task submitted with ID: {result.id}'))
                
                # Wait for task completion
                self.stdout.write('Waiting for email task to complete...')
                try:
                    task_result = result.get(timeout=20)  # Wait up to 20 seconds
                    self.stdout.write(self.style.SUCCESS(f'Email task completed with result: {task_result}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error waiting for email task: {str(e)}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error submitting email task: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS('Celery test command completed.'))
        self.stdout.write(self.style.WARNING('Note: Successful task submission does not guarantee task completion.'))
        self.stdout.write(self.style.WARNING('Check your Celery logs for actual task execution details.')) 