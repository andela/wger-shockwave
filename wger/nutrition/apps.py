'''A module that imports the signals file into an instance of nutrition'''
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class NutritionConfig(AppConfig):
    '''A class that imports the signals file to be passed onto the instance
    of the nutrition object being called.
    '''
    name = "wger.nutrition"
    verbose_name = _('nutrition')

    def ready(self):
        import wger.nutrition.signals
