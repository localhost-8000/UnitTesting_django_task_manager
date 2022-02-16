from django.test import TestCase

from tasks.models import Task

class TaskModelTest(TestCase):

    def test_str(self):
        task = Task.objects.create(title='test title', description='test description')
        self.assertEqual(str(task), "test title")

    def test_date_is_prettified(self):
        task = Task.objects.create(title='test title', description='test description')
        self.assertEqual(task.pretty_date(), task.created_date.strftime('%a %d %b'))