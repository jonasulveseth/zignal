# Celery Setup and Configuration

This document provides instructions for setting up and using Celery with the Zignal project.

## Requirements

- Redis server installed and running (used as broker)
- Celery installed (included in project requirements)

## Running Celery Workers

To start a Celery worker:

```bash
# From the project directory
cd /path/to/zignal_django/zignal

# Start a worker with the default queue
celery -A zignal.config worker -l INFO

# Start a worker with a specific queue
celery -A zignal.config worker -l INFO -Q default,email,processing
```

## Running the Celery Beat Scheduler (for periodic tasks)

If you plan to have scheduled tasks:

```bash
cd /path/to/zignal_django/zignal
celery -A zignal.config beat -l INFO
```

## Testing Celery Tasks

The project includes a management command to test Celery tasks:

```bash
# Test all tasks
python manage.py test_celery

# Test specific task categories
python manage.py test_celery --task=sample
python manage.py test_celery --task=process_data
python manage.py test_celery --task=email
```

## Automatic Default Resources Creation

When a new company is created, the system automatically creates:
- A default project
- A project-specific data silo
- A company-level data silo

For existing companies that may not have these resources, you can use the management command:

```bash
# Create default resources for all companies
python manage.py create_default_resources

# Create for a specific company
python manage.py create_default_resources --company-id=1

# Force creation even if company already has projects/silos
python manage.py create_default_resources --force
```

## Environment Variables

Configure these environment variables in your `.env` file:

```
# Redis URLs
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# For email processing
PROCESS_EMAILS_SYNC=False  # Set to True to process emails synchronously
```

## Production Deployment

For production environments:

1. Consider using a process manager like Supervisor to manage Celery processes
2. Increase concurrency with the `-c` option (e.g., `celery -A zignal.config worker -l INFO -c 4`)
3. Configure multiple queues for different types of tasks
4. Set up monitoring with Flower: `celery -A zignal.config flower` 