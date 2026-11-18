from django.apps import AppConfig


class IaConfig(AppConfig):
    """Integracao com o Gemini (cliente e prompts). Nao tem models."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ia'
    verbose_name = 'IA generativa'
