from django.apps import AppConfig

class MyProjectConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myproject'  # Ensure this matches your app's directory name
