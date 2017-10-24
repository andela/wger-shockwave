from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    '''
    Helper admin command to clean up demo users, to be called e.g. by cron
    '''
    help = 'Gives permission to API users to register users'
    
    def add_arguments(self, parser):
        parser.add_argument('username')
        
    def handle(self, **options):
        '''
        Add permissions to user
        '''
        user = User.objects.get(username=options['username'])
