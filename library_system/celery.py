import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')

app = Celery('library_system')

app.conf.beat_schedule = {
    'check_overdue_loans ': {
        'task': 'app.tasks.check_overdue_loans ',
        'schedule': crontab(minute='00,00'),
        'args': (),
    },
}
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
