
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from pytz import timezone

from tasks.models import Task, TaskReport
from tasks.tasks import get_user_tasks_status, send_email_report


class TestCeleryFunction(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test_user_1')
        self.user.set_password('pass123')
        self.user.save()

    def create_tasks(self, length=1, user=None, completed=False, deleted=False, status='PENDING'):
        for i in range(1, length + 1):
            Task.objects.create(
                user=user, 
                title=f"TEST TASK {i} TITLE", 
                description=f"Test task {i} description", 
                priority=i, 
                deleted=deleted, 
                completed=completed,
                status=status
            )
    
    def test_send_email_report(self):
        curr_time = datetime.now(tz=timezone('UTC')) - timedelta(minutes=10)
        task_report = TaskReport.objects.create(user=self.user, user_mail='mail@abc.com', report_time='11:00', next_run_at=curr_time)
        result = send_email_report.apply()

        self.assertTrue(result.successful())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].recipients()[0], task_report.user_mail)
        self.assertEqual(TaskReport.objects.get(user=self.user).next_run_at, curr_time + timedelta(days=1))

    def test_get_user_tasks_status(self):
        self.create_tasks(1, user=self.user)
        self.create_tasks(1, user=self.user, completed=True, status='COMPLETED')
        self.create_tasks(1, user=self.user, status='IN_PROGRESS')
        self.create_tasks(1, user=self.user, status='CANCELLED')

        founded_message = get_user_tasks_status(self.user)
        expected_message = f"Hi {self.user.username},\n\nHere is your tasks report for today:\n\nTotal tasks added: 4\nPending tasks: 1\nIn Progress tasks: 1\nCompleted tasks: 1\nCancelled tasks: 1\n\nThanks"

        self.assertEqual(founded_message, expected_message)
