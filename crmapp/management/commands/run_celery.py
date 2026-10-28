import subprocess
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Start Redis, Celery worker, and Celery beat"

    def handle(self, *args, **kwargs):

        subprocess.Popen("redis-server", shell=True)
        subprocess.Popen("celery -A crm worker -l info --pool=solo", shell=True)
        subprocess.Popen("celery -A crm beat -l info", shell=True)

        self.stdout.write(self.style.SUCCESS("All services started"))