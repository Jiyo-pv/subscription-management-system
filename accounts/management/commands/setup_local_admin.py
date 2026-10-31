from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = 'Create or update the local development administrator account.'

    def add_arguments(self, parser):
        parser.add_argument('--email', default='admin@brightloop.com')
        parser.add_argument('--password', required=True, help='Local-only password; never commit it.')
        parser.add_argument('--name', default='Brightloop Admin')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('This command is only available when DEBUG=True.')

        email = User.objects.normalize_email(options['email'])
        user, created = User.objects.get_or_create(
            email=email,
            defaults={'name': options['name'], 'role': 'admin'},
        )
        user.name = options['name']
        user.role = 'admin'
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(options['password'])
        user.save()

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{action} local admin account: {email}'))
