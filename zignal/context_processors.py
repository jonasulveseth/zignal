from django.conf import settings

def settings_context(request):
    """
    Add settings to the template context
    """
    return {
        'DEBUG': settings.DEBUG,
        'OPENAI_API_KEY': settings.OPENAI_API_KEY if settings.DEBUG else '',
    } 