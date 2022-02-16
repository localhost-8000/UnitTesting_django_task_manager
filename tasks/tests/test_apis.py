
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase
from tasks.models import Task, TaskHistory


class APITestCaseSetUp(APITestCase):

    def setUp(self):
        self.task_api_url = '/api/v1/tasks/'

        self.test_user = {
            'username': 'test_user',
            'password': 'pass123'
        }
        self.authenticated_user = User.objects.create_user(**self.test_user)
        
        self.test_tasks = [
            {
                'title': 'Test task 1 title',
                'description': 'Test description 1',
                'priority': 1,
                'status': 'PENDING'
            },
            {
                'title': 'Test task 2 title',
                'description': 'Test description 2',
                'priority': 2,
                'status': 'PENDING'
            }
        ]
        return super().setUp()
    

    def authenticate_user(self):
        res = self.client.login(username=self.test_user['username'], password=self.test_user['password'])

    def tearDown(self):
        return super().tearDown()


class CreateTaskAPITestCase(APITestCaseSetUp):

    def test_cannot_create_task_if_not_authenticated(self):
        response = self.client.post(self.task_api_url, self.test_tasks[0], format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_create_task_if_authenticated(self):
        self.authenticate_user()
        initial_tasks_count = Task.objects.count()
        response = self.client.post(self.task_api_url, self.test_tasks[0], format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), initial_tasks_count + 1)

        for attrs, expected_value in self.test_tasks[0].items():
            if attrs == 'title':
                self.assertEqual(response.data[attrs], expected_value.upper())
                continue
            self.assertEqual(response.data[attrs], expected_value)

    def test_task_cannot_be_created_with_title_length_less_than_10(self):
        self.authenticate_user()
        task_attrs = self.test_tasks[0].copy()
        task_attrs['title'] = 'title'

        response = self.client.post(self.task_api_url, task_attrs, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Task.objects.count(), 0)


    def test_priority_cascading_logic_working_in_create_tasks(self):
        self.authenticate_user()
        for task in self.test_tasks:
            response = self.client.post(self.task_api_url, task, format='json')
        
        new_test_task = {
            'title': 'Highest Priority task',
            'description': 'testing priority cascading',
            'priority': 1,
            'status': 'PENDING'
        }
        self.client.post(self.task_api_url, new_test_task, format='json')

        expected_tasks = [
            {
                'title': 'Highest Priority task',
                'description': 'testing priority cascading',
                'priority': 1,
                'status': 'PENDING'
            },
            {
                'title': 'Test task 1 title',
                'description': 'Test description 1',
                'priority': 2,
                'status': 'PENDING'
            },
            {
                'title': 'Test task 2 title',
                'description': 'Test description 2',
                'priority': 3,
                'status': 'PENDING'
            }
        ]

        created_tasks = Task.objects.all().order_by('priority')
        index = 0

        for task in expected_tasks:
            current_priority = created_tasks[index].priority
            expected_priority = task['priority']
            self.assertEqual(current_priority, expected_priority)
            index += 1

    
class ListTaskAPITestCase(APITestCaseSetUp):

    def test_cannot_list_tasks_if_not_authenticated(self):
        response = self.client.get(self.task_api_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_list_tasks_if_authenticated(self):
        self.authenticate_user()
        response = self.client.post(self.task_api_url, self.test_tasks[0], format='json') 
        response = self.client.get(self.task_api_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], self.test_tasks[0]['title'].upper())

class RetrieveTaskAPITestCase(APITestCaseSetUp):

    def test_cannot_retrieve_task_if_not_authenticated(self):
        task = Task.objects.create(**self.test_tasks[0])
        response = self.client.get(f"{self.task_api_url}{task.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_retrieve_task_if_authenticated(self):
        self.authenticate_user()
        task = Task.objects.create(**self.test_tasks[0])
        task.user = self.authenticated_user
        task.save()
        response = self.client.get(f"{self.task_api_url}{task.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.test_tasks[0]['title'].upper())


class UpdateTaskAPITestCase(APITestCaseSetUp):

    def test_cannot_update_tasks_if_not_authenticated(self):
        task = Task.objects.create(**self.test_tasks[0])
        updated_task = self.test_tasks[0].copy()['title'] = 'Updated task title'
        response = self.client.put(f"{self.task_api_url}{task.id}/", updated_task, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_udpate_tasks_if_authenticated(self):
        self.authenticate_user()
        task = Task.objects.create(**self.test_tasks[0])
        task.user = self.authenticated_user
        task.save()
        updated_task = self.test_tasks[0].copy()
        updated_task['title'] = 'Updated task title'
        response = self.client.put(f"{self.task_api_url}{task.id}/", updated_task, format='json')
      
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], updated_task['title'].upper())

    def test_priority_cascading_logic_working_in_update(self):
        self.authenticate_user()
        for test_task in self.test_tasks:
            task = Task.objects.create(**test_task)
            task.user = self.authenticated_user
            task.save()

        expected_tasks = [
            {
                'title': 'Test task 1 title',
                'description': 'Test description 1',
                'priority': 2,
                'status': 'PENDING'
            },
            {
                'title': 'Test task 2 title',
                'description': 'Test description 2',
                'priority': 3,
                'status': 'PENDING'
            }
        ]
        response = self.client.put(f"{self.task_api_url}1/", expected_tasks[0], format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        tasks_founded = Task.objects.all().order_by('priority')
        index = 0

        for task in expected_tasks:
            current_priority = tasks_founded[index].priority
            expected_priority = task['priority']
            self.assertEqual(current_priority, expected_priority)
            index += 1


class DestroyTaskAPITestCase(APITestCaseSetUp):

    def test_cannot_destroy_task_if_not_authenticated(self):
        task = Task.objects.create(**self.test_tasks[0])
        response = self.client.delete(f"{self.task_api_url}{task.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_destory_task_if_authenticated(self):
        self.authenticate_user()
        task = Task.objects.create(**self.test_tasks[0])
        task.user = self.authenticated_user
        task.save()
        response = self.client.delete(f"{self.task_api_url}{task.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Task.objects.get(pk=task.id).deleted, True)


class TaskHistoryTestSetUp(APITestCase):
    
    def setUp(self):
        self.task_history_api_url = '/api/v1/task/1/history/'
        self.task_api_url = '/api/v1/tasks/'
        self.test_user = {
            'username': 'test_user',
            'password': 'pass123'
        }
        self.authenticated_user = User.objects.create_user(**self.test_user)
        self.test_task = {
            'title': 'Test task title',
            'description': 'Test description',
            'priority': 1,
            'status': 'PENDING'
        }
        self.udpated_task = self.test_task.copy()
        self.udpated_task['status'] = 'IN_PROGRESS'

        return super().setUp()

    def authenticate_user(self):
        res = self.client.login(username=self.test_user['username'], password=self.test_user['password'])
    
    def create_task_history(self):
        task = Task.objects.create(**self.test_task)
        task.user = self.authenticated_user
        task.save()
        test_task_history = TaskHistory.objects.create(task=task, old_status='PENDING', new_status='IN_PROGRESS')

    def test_cannot_retrieve_task_history_if_not_authenticated(self):
        self.create_task_history()
        response = self.client.get(f"{self.task_history_api_url}1/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_can_retrieve_task_history_if_authenticated(self):
        self.authenticate_user()
        self.create_task_history()
        response = self.client.get(f"{self.task_history_api_url}1/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['old_status'], 'PENDING')

    def test_task_history_is_read_only(self):
        self.authenticate_user()
        self.create_task_history()
        updated_task_history = {
            'old_status': 'IN_PROGRESS',
            'new_status': 'COMPLETED'
        }
        response1 = self.client.put(f"{self.task_history_api_url}1/", updated_task_history, format='json')
        response2 = self.client.delete(f"{self.task_history_api_url}1/")

        self.assertEqual(response1.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response2.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_task_history_is_created_in_task_update_method(self):
        self.authenticate_user()
        task = Task.objects.create(**self.test_task)
        task.user = self.authenticated_user
        task.save()

        res = self.client.put(f"{self.task_api_url}{task.id}/", self.udpated_task, format='json')
        history_response = self.client.get(f"{self.task_history_api_url}1/")

        self.assertEqual(history_response.status_code, status.HTTP_200_OK)
        self.assertEqual(history_response.data['old_status'], 'PENDING')
        self.assertEqual(history_response.data['new_status'], 'IN_PROGRESS')
