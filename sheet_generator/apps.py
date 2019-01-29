import os
from django.apps import AppConfig
APP_DIR = os.path.abspath(os.path.dirname(__file__))


class SheetGeneratorConfig(AppConfig):
    name = 'sheet_generator'
