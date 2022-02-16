from django.db import transaction

from django_filters.rest_framework import (BooleanFilter, CharFilter,
                                           ChoiceFilter, DateRangeFilter,
                                           DjangoFilterBackend, FilterSet)

from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from tasks.models import STATUS_CHOICES, Task, TaskHistory
from tasks.serializers import TaskHistorySerializer, TaskSerializer


# Task filter
class TaskFilter(FilterSet):
    title = CharFilter(lookup_expr='icontains')
    status = ChoiceFilter(choices=STATUS_CHOICES)
    completed = BooleanFilter()

# Tasks utility functions 
class TaskUtilityFunctions():

    def create_task_history(self, task, old_status, new_status):
        task_history = TaskHistory(task=task, old_status=old_status, new_status=new_status)
        task_history.save()
    
    def priority_cascading_logic(self, priority, task_id=None):
        priority = int(priority)
        updated_tasks = []
        with transaction.atomic():
            tasks = Task.objects.filter(deleted=False, completed=False, user=self.request.user).exclude(pk=task_id).select_for_update().order_by('priority')
            for task in tasks:
                if task.priority == priority:
                    task.priority = priority + 1
                    priority += 1
                    updated_tasks.append(task)

            # bulk update the tasks...
            Task.objects.bulk_update(updated_tasks, ['priority'])

# Task pagination
class TaskPagination(LimitOffsetPagination):
    default_limit = 5
    max_limit = 20

# Task viewset
class TaskViewSet(ModelViewSet, TaskUtilityFunctions):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TaskFilter

    pagination_class = TaskPagination

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user, deleted=False)

    def create(self, request, *args, **kwargs):
        # Apply priority cascading
        self.priority_cascading_logic(request.data['priority'])

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
   
    def update(self, request, *args, **kwargs):
        # Get the current active task instance
        task = self.get_object()

        # Apply priority cascading
        self.priority_cascading_logic(request.data['priority'], task.id)

        old_status = task.status
        new_status = request.data['status']
        
        # Check for the status changes
        if old_status != new_status:
            self.create_task_history(task, old_status, new_status)
        
        return super().update(request, *args, **kwargs)


    def perform_destroy(self, instance):
        task = self.get_object()
        old_status = task.status
        new_status = 'CANCELLED'

        if old_status != new_status:
            self.create_task_history(task, old_status, new_status)

        Task.objects.filter(pk=task.id, user=self.request.user).update(deleted=True)


# Task History filter..
class TaskHistoryFilter(FilterSet):
    updated_date = DateRangeFilter(field_name='updated_date', lookup_expr='exact')
    new_status = ChoiceFilter(choices=STATUS_CHOICES)
    old_status = ChoiceFilter(choices=STATUS_CHOICES)

# Task History viewset(readonly)
class TaskHistoryViewSet(ReadOnlyModelViewSet):
    queryset = TaskHistory.objects.all()
    serializer_class = TaskHistorySerializer

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TaskHistoryFilter

    def get_queryset(self):
        task_id = self.kwargs['task_id']  
        return TaskHistory.objects.filter(task__user=self.request.user, task=task_id)
