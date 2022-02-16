
from datetime import datetime, timedelta
import pdb

from django.contrib.auth.models import User
from django.forms import ValidationError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from pytz import timezone
from rest_framework import status
from tasks.models import Task, TaskHistory, TaskReport

from ..views import (GenericCompleteTaskView, GenericPendingTaskView,
                     GenericTaskCreateView, GenericTaskDeleteView,
                     GenericTaskDetailView, GenericTaskUpdateView, 
                     GenericTaskView, UserCreateView,
                     get_next_run_at)


class ViewTestSetUp(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        # Create test user
        self.user1 = User.objects.create(username='test_user_1')
        self.user1.set_password('test_123')
        self.user1.save()
        self.user2 = User.objects.create(username='test_user_2')
        self.user2.set_password('test_1234')
        self.user2.save()
        
        # Initialize url paths
        self.tasks_url = reverse('tasks')
        self.create_task_url = reverse('create_task')
        self.pending_tasks_url = reverse('pending_tasks')
        self.completed_tasks_url = reverse('completed_tasks')
        self.update_task_url = reverse('update_task', kwargs={'pk': 1})
        self.task_detail_url = reverse('detail_task', kwargs={'pk': 1})
        self.delete_task_url = reverse('delete_task', kwargs={'pk': 1})

    def authenticate_user1(self):
        login = self.client.login(username='test_user_1', password='test_123')
        self.assertTrue(login)
    
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

    def get_context_data_of_view(self, GenericView, url):
        view = self.get_view(GenericView, url)
        view.object_list = view.get_queryset()
        return view.get_context_data()

    def get_view(self, GenericView, url):
        request = self.factory.get(url)
        request.user = self.user1
        view = GenericView()
        view.setup(request)
        return view

class TestAuthViews(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.register_url = reverse('create_user')
        self.login_url = reverse('login_user')
        
    def test_user_able_to_register(self):
        request = self.factory.post(self.register_url, {'username': 'testuser2', 'password': 'test1234'})
        response = UserCreateView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    

class TestAuthView(TestCase):

    def setUp(self):
        self.register_url = reverse('create_user')
        self.login_url = reverse('login_user')
        self.factory = RequestFactory()
    
    def test_correct_template_get_rendered_in_user_create_view(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'user_create.html')

    def test_correct_template_get_rendered_in_user_login_view(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'user_login.html')


class TestTaskView(ViewTestSetUp):
    
    def test_redirect_task_view_if_not_logged_in(self):
        response = self.client.get(self.tasks_url)
        self.assertRedirects(response, '/user/login?next=/tasks', fetch_redirect_response=False)

    def test_task_view_template_rendered_if_logged_in(self):
        request = self.factory.get(self.tasks_url)
        request.user = self.user1
        response = GenericTaskView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.assertTemplateUsed('tasks.html'):
            response.render()

    def test_task_view_pagination_is_three(self):
        self.create_tasks(5, self.user1)
        context = self.get_context_data_of_view(GenericTaskView, self.tasks_url)

        self.assertTrue(context['is_paginated'] == True)
        self.assertEqual(context['tasks'].count(), 3)

    def test_task_view_context_data(self):
        self.create_tasks(1, self.user1)
        context = self.get_context_data_of_view(GenericTaskView, self.tasks_url)
        
        self.assertIn('completed_tasks_len', context)
        self.assertIn('total_tasks_len', context)

    def test_task_view_queryset(self):
        self.create_tasks(1, self.user1)
        self.create_tasks(1, self.user1, deleted=False)
        self.create_tasks(1, self.user2)

        founded_tasks = self.get_view(GenericTaskView, self.tasks_url).get_queryset()
        expected_query_tasks = Task.objects.filter(user=self.user1, deleted=False).order_by('priority')

        self.assertQuerysetEqual(founded_tasks, expected_query_tasks)
 

class TestCompletedTaskView(ViewTestSetUp):
    
    def test_completed_task_view_redirect_if_not_logged_in(self):
        response = self.client.get(self.completed_tasks_url)
        self.assertRedirects(response, '/user/login?next=/completed-tasks', fetch_redirect_response=False)
    
    def test_completed_task_view_template_rendered_if_logged_in(self):
        request = self.factory.get(self.completed_tasks_url)
        request.user = self.user1
        response = GenericCompleteTaskView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.assertTemplateUsed('completed_tasks.html'):
            response.render()

    def test_completed_task_view_pagination_is_three(self):
        self.create_tasks(5, self.user1, completed=True)
        context = self.get_context_data_of_view(GenericCompleteTaskView, self.completed_tasks_url)
        
        self.assertTrue(context['is_paginated'] == True)
        self.assertEqual(context['completed_tasks'].count(), 3)

    def test_completed_tasks_view_context_data(self):
        self.create_tasks(1, self.user1, completed=True)
        context = self.get_context_data_of_view(GenericCompleteTaskView, self.completed_tasks_url)
        
        self.assertIn('completed_tasks_len', context)
        self.assertIn('total_tasks_len', context)

    def test_completed_tasks_view_queryset(self):
        self.create_tasks(1, self.user1, completed=True)
        self.create_tasks(1, self.user1, completed=False)
        self.create_tasks(1, self.user1, deleted=True)
        
        self.create_tasks(1, self.user2, completed=True)

        founded_tasks = self.get_view(GenericCompleteTaskView, self.completed_tasks_url).get_queryset()
        expected_query_tasks = Task.objects.filter(user=self.user1, deleted=False, completed=True).order_by('priority')

        self.assertQuerysetEqual(founded_tasks, expected_query_tasks)


class TestPendingTaskView(ViewTestSetUp):
    
    def test_pending_task_view_redirect_if_not_logged_in(self):
        response = self.client.get(self.pending_tasks_url)
        self.assertRedirects(response, '/user/login?next=/pending-tasks', fetch_redirect_response=False)
    
    def test_pending_task_view_template_rendered_if_logged_in(self):
        request = self.factory.get(self.pending_tasks_url)
        request.user = self.user1
        response = GenericPendingTaskView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.assertTemplateUsed('pending_tasks.html'):
            response.render()

    def test_pending_task_view_pagination_is_three(self):
        self.create_tasks(5, self.user1)
        context = self.get_context_data_of_view(GenericPendingTaskView, self.pending_tasks_url)
        
        self.assertTrue(context['is_paginated'] == True)
        self.assertEqual(context['pending_tasks'].count(), 3)

    def test_pending_tasks_view_context_data(self):
        self.create_tasks(1, self.user1)
        context = self.get_context_data_of_view(GenericPendingTaskView, self.pending_tasks_url)
        
        self.assertIn('completed_tasks_len', context)
        self.assertIn('total_tasks_len', context)

    def test_pending_tasks_view_queryset(self):
        test_user2 = User.objects.create(username='test_user2', password='test123')
        test_task2 = Task.objects.create(user=test_user2, title='test task 2 title', description='test task 2 description', priority=1)

        self.create_tasks(1, self.user1)
        self.create_tasks(1, self.user1, deleted=True)
        self.create_tasks(1, self.user1, completed=True)
        self.create_tasks(1, self.user2)

        founded_tasks = self.get_view(GenericPendingTaskView, self.pending_tasks_url).get_queryset()
        expected_query_tasks = Task.objects.filter(user=self.user1, deleted=False, completed=False).order_by('priority')

        self.assertQuerysetEqual(founded_tasks, expected_query_tasks)


class TestTaskDetailView(ViewTestSetUp):

    def test_redirect_task_detail_view_if_not_logged_in(self):
        response = self.client.get(self.task_detail_url)
        self.assertRedirects(response, '/user/login?next=/detail-task/1', fetch_redirect_response=False)

    def test_task_detail_view_template_rendered_if_logged_in(self):
        self.create_tasks(1, self.user1)
        request = self.factory.get(self.task_detail_url)
        request.user = self.user1
        response = GenericTaskDetailView.as_view()(request, pk=1)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.assertTemplateUsed('task_details.html'):
            response.render()


class TestTaskCreateView(ViewTestSetUp):

    def test_redirect_task_create_view_if_not_logged_in(self):
        response = self.client.get(self.create_task_url)
        self.assertRedirects(response, '/user/login?next=/create-task', fetch_redirect_response=False)
    
    def test_task_create_view_template_rendered_if_logged_in(self):
        request = self.factory.get(self.create_task_url)
        request.user = self.user1
        response = GenericTaskCreateView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.assertTemplateUsed('task_create.html'):
            response.render()

    def test_task_cannot_created_with_title_less_than_ten_characters(self):
        self.authenticate_user1()
        response = self.client.post(self.create_task_url, {'title': 'test', 'description': 'test description', 'priority': 1, 'status': 'PENDING'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.context['form'].errors['title'][0], 'Title must be at least 10 characters long')
        self.assertEqual(Task.objects.count(), 0)

    def test_task_get_created_with_valid_data_and_redirected(self):
        self.authenticate_user1()
        test_task = {'title': 'test title', 'description': 'test description', 'priority': 1, 'status': 'PENDING'}
        response = self.client.post(self.create_task_url, test_task)
        
        self.assertRedirects(response, '/tasks', fetch_redirect_response=False)
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Task.objects.get(pk=1).title, test_task['title'].upper())

    def test_priority_cascading_working_in_creating_task(self):
        self.authenticate_user1()
        self.create_tasks(2, self.user1)

        new_task = {
            'title': 'Test task 3 title',
            'description': 'test description 3',
            'priority': 1,
            'status': 'PENDING'
        }

        response = self.client.post(self.create_task_url, new_task)

        self.assertRedirects(response, '/tasks', fetch_redirect_response=False)
        self.assertEqual(Task.objects.count(), 3)

        tasks_founded = Task.objects.filter(user=self.user1, deleted=False, completed=False).order_by('priority')
        expected_tasks = [
            {'title': 'Test task 3 title', 'priority': 1},
            {'title': 'Test task 1 title', 'priority': 2},
            {'title': 'Test task 2 title', 'priority': 3},
        ]
        index = 0
        for task in expected_tasks:
            self.assertEqual(tasks_founded[index].title, task['title'].upper())
            self.assertEqual(tasks_founded[index].priority, task['priority'])
            index += 1
    

class TestTaskUpdateView(ViewTestSetUp):

    def test_redirect_task_update_view_if_not_logged_in(self):
        self.create_tasks(1, self.user1)
        response = self.client.get(self.update_task_url)
        self.assertRedirects(response, '/user/login?next=/update-task/1', fetch_redirect_response=False)
    
    def test_task_create_view_template_rendered_if_logged_in(self):
        self.create_tasks(1, self.user1)
        request = self.factory.get(self.update_task_url)
        request.user = self.user1
        response = GenericTaskUpdateView.as_view()(request, pk=1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.assertTemplateUsed('task_update.html'):
            response.render()

    def test_task_cannot_updated_with_title_less_than_ten_characters(self):
        self.authenticate_user1()
        self.create_tasks(1, self.user1)
        updated_task = {'title': 'test', 'description': 'test description', 'priority': 1, 'status': 'PENDING'}
        response = self.client.post(self.update_task_url, updated_task)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.context['form'].errors['title'][0], 'Title must be at least 10 characters long')
        self.assertTrue(Task.objects.get(pk=1).title != updated_task['title'].upper())

    def test_task_get_updated_with_valid_data_and_redirected(self):
        self.authenticate_user1()
        self.create_tasks(1, self.user1)
        test_task = {'title': 'test title', 'description': 'test description', 'priority': 1, 'status': 'PENDING'}
        response = self.client.post(self.update_task_url, test_task)
        
        self.assertRedirects(response, '/tasks', fetch_redirect_response=False)

        founded_task = Task.objects.get(pk=1)
        self.assertEqual(founded_task.title, test_task['title'].upper())
        self.assertEqual(founded_task.description, test_task['description'])

    def test_priority_cascading_working_in_updating_task(self):
        self.authenticate_user1()
        self.create_tasks(2, self.user1)

        expected_tasks = [
            {'title': 'Test task 1 title', 'priority': 2, 'description': 'Test task 1 description', 'status': 'PENDING'},
            {'title': 'Test task 2 title', 'priority': 3},
        ]

        response = self.client.post(self.update_task_url, expected_tasks[0])
        self.assertRedirects(response, '/tasks', fetch_redirect_response=False)

        tasks_founded = Task.objects.filter(user=self.user1, deleted=False, completed=False).order_by('priority')
        index = 0
        for task in expected_tasks:
            self.assertEqual(tasks_founded[index].title, task['title'].upper())
            self.assertEqual(tasks_founded[index].priority, task['priority'])
            index += 1
    
    def test_task_history_cannot_created_on_no_status_change(self):
        self.authenticate_user1()
        self.create_tasks(1, self.user1)
        updated_task = {'title': 'Test task 1 title', 'description': 'Test task 1 description', 'priority': 2, 'status': 'PENDING'}

        response = self.client.post(self.update_task_url, updated_task)
        self.assertRedirects(response, '/tasks', fetch_redirect_response=False)

        self.assertEqual(TaskHistory.objects.count(), 0)

    def test_task_history_created_on_status_change(self):
        self.authenticate_user1()
        self.create_tasks(1, self.user1)
        updated_task = {'title': 'Test task 1 title', 'description': 'Test task 1 description', 'priority': 1, 'status': 'IN_PROGRESS'}

        response = self.client.post(self.update_task_url, updated_task)
        self.assertRedirects(response, '/tasks', fetch_redirect_response=False)

        task_history_founded = TaskHistory.objects.get(task=Task.objects.get(pk=1))
        self.assertEqual(task_history_founded.old_status, 'PENDING')
        self.assertEqual(task_history_founded.new_status, 'IN_PROGRESS')


class TestTaskDeleteView(ViewTestSetUp):

    def test_redirect_task_delete_view_if_not_logged_in(self):
        self.create_tasks(1, self.user1)
        response = self.client.get(self.delete_task_url)
        self.assertRedirects(response, '/user/login?next=/delete-task/1', fetch_redirect_response=False)

    def test_task_delete_view_template_rendered_if_logged_in(self):
        self.authenticate_user1()
        self.create_tasks(1, self.user1)
        request = self.factory.get(self.delete_task_url)
        request.user = self.user1

        response = GenericTaskDeleteView.as_view()(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.assertTemplateUsed('task_delete.html'):
            response.render()

    def test_task_get_soft_deleted(self):
        self.authenticate_user1()
        self.create_tasks(1, self.user1)
        response = self.client.post(self.delete_task_url)
        
        self.assertRedirects(response, '/tasks', fetch_redirect_response=False)

        founded_task = Task.objects.get(pk=1)
        self.assertTrue(founded_task.deleted)


class TestTaskReportCreateView(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test_user')
        self.user.set_password('test_123')
        self.user.save()
        self.task_report_url = reverse('task_report')
        self.factory = RequestFactory()

    def authenticate_user(self):
        login = self.client.login(username='test_user', password='test_123')
        self.assertTrue(login)

    def test_redirect_task_report_create_view_if_not_logged_in(self): 
        response = self.client.get(self.task_report_url)
        self.assertRedirects(response, '/user/login?next=/report', fetch_redirect_response=False)
    
    def test_task_report_create_view_rendered_if_logged_in(self):
        self.authenticate_user()
        response = self.client.get(self.task_report_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'task_report.html')

    def test_user_able_to_create_task_report(self):
        self.authenticate_user()
        task_report = {'user_mail': 'mail@abc.com', 'report_time': '12:00', 'enabled': True, 'timezone': 'Asia/Kolkata'}
        response = self.client.post(self.task_report_url, task_report)
        
        self.assertRedirects(response, '/tasks', fetch_redirect_response=False)
        founded_tasks = TaskReport.objects.get(user=self.user)

        self.assertEqual(founded_tasks.user_mail, task_report['user_mail'])
        self.assertEqual(founded_tasks.enabled, task_report['enabled'])

    def test_user_can_create_only_one_task_report(self):
        self.authenticate_user()
        task_report = TaskReport.objects.create(user=self.user, user_mail='mail@abc.com', report_time='12:00')
        new_task_report = {'user_mail': 'mail2@abc.com', 'report_time': '12:00', 'enabled': True, 'timezone': 'Asia/Kolkata'}

        with self.assertRaises(ValidationError) as error:
            response = self.client.post(self.task_report_url, new_task_report)
        
        self.assertEqual(error.exception.message, 'You have already scheduled a report. Go to /update-report to update your report.')

    def test_get_next_run_at_for_report_time_less_than_current_time(self):
        curr_datetime = datetime.now(tz=timezone('Asia/Kolkata')) - timedelta(minutes=10)
        print(curr_datetime)
        curr_date = curr_datetime.date() + timedelta(days=1)
        time_zone = 'Asia/Kolkata'
        report_time = curr_datetime.time()

        founded_next_run_at = get_next_run_at(report_time, time_zone)        
        expected_next_run_at = datetime.combine(curr_date, report_time, tzinfo=timezone('UTC'))
        # pdb.set_trace()
        self.assertEqual(expected_next_run_at, founded_next_run_at)
    
    def test_get_next_run_at_for_report_time_greater_than_current_time(self):
        curr_datetime = datetime.now(tz=timezone('Asia/Kolkata')) + timedelta(minutes=10)
        curr_date = curr_datetime.date()
        time_zone = 'Asia/Kolkata'
        report_time = curr_datetime.time()

        founded_next_run_at = get_next_run_at(report_time, time_zone)        
        expected_next_run_at = datetime.combine(curr_date, report_time).astimezone(timezone('UTC'))

        self.assertEqual(expected_next_run_at, founded_next_run_at)
        

class TestTaskReportUpdateView(TestCase):
    def setUp(self):
        self.user = User.objects.create(username='test_user')
        self.user.set_password('test_123')
        self.user.save()
        self.task_report_udpate_url = reverse('update_report')

    def authenticate_user(self):
        login = self.client.login(username='test_user', password='test_123')
        self.assertTrue(login)

    def test_redirect_task_report_update_view_if_not_logged_in(self): 
        response = self.client.get(self.task_report_udpate_url)
        self.assertRedirects(response, '/user/login?next=/update-report', fetch_redirect_response=False)
    
    def test_task_report_update_view_rendered_if_logged_in(self):
        self.authenticate_user()
        task_report = TaskReport.objects.create(user=self.user, user_mail='mail@abc.com', report_time='12:00')
        response = self.client.get(self.task_report_udpate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'task_report.html')

    def test_user_able_to_update_task_report(self):
        self.authenticate_user()
        task_report = TaskReport.objects.create(user=self.user, user_mail='mail@abc.com', report_time='12:00')
        updated_task_report = {'user_mail': 'newmail@abc.com', 'report_time': '12:00', 'enabled': False, 'timezone': 'Asia/Kolkata'}

        response = self.client.post(self.task_report_udpate_url, updated_task_report)
        self.assertRedirects(response, '/tasks', fetch_redirect_response=False)

        task_report = TaskReport.objects.get(user=self.user)
        self.assertEqual(task_report.user_mail, updated_task_report['user_mail'])
        self.assertEqual(task_report.enabled, updated_task_report['enabled'])

class TestHomeView(TestCase):

    def test_home_view(self):
        response = self.client.get('/')
        self.assertRedirects(response, '/tasks', fetch_redirect_response=False)
