from datetime import datetime, timedelta

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.forms import ChoiceField, ModelForm, ValidationError
from django.http import HttpResponseRedirect
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from pytz import all_timezones, timezone

from tasks.api_views import TaskUtilityFunctions
from tasks.models import Task, TaskReport


class AuthorisedTaskManager(LoginRequiredMixin):
    def get_queryset(self):
        return Task.objects.filter(deleted=False, user=self.request.user)

class TaskCreateForm(ModelForm):

    def clean_title(self):
        title = self.cleaned_data['title']
        if len(title) < 10:
            raise ValidationError('Title must be at least 10 characters long')
        return title.upper()

    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'status', 'completed']


class GenericTaskCreateView(LoginRequiredMixin, CreateView, TaskUtilityFunctions):
    form_class = TaskCreateForm
    template_name = 'task_create.html'
    extra_context = {'title': 'Create Todo'}
    success_url = '/tasks'

    def form_valid(self, form):
        # Apply priority cascading logic
        self.priority_cascading_logic(form.cleaned_data['priority'])
        
        # Save the task model
        self.object = form.save()
        self.object.user = self.request.user 
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class GenericTaskDetailView(AuthorisedTaskManager, DetailView):
    model = Task
    template_name = 'task_details.html'
    extra_context = {'title': 'Task Details'}


class GenericTaskUpdateView(AuthorisedTaskManager, UpdateView, TaskUtilityFunctions):
    model = Task
    form_class = TaskCreateForm
    template_name = 'task_update.html'
    extra_context = {'title': 'Update Todo'}
    success_url = '/tasks'

    def form_valid(self, form):
        # Get the current active task instance
        task = self.get_object()

        # Apply priority cascading logic
        self.priority_cascading_logic(form.cleaned_data['priority'], task.id)

        old_status = task.status
        new_status = form.cleaned_data['status']

        # Check for the status changes
        if old_status != new_status:
            self.create_task_history(task, old_status, new_status)
        
        return super().form_valid(form)


class GenericTaskDeleteView(AuthorisedTaskManager, DeleteView, TaskUtilityFunctions):
    model = Task
    template_name = 'task_delete.html'
    success_url = '/tasks'

    def form_valid(self, form):
        task = self.get_object()
        old_status = task.status
        new_status = 'CANCELLED'

        if old_status != new_status:
            self.create_task_history(task, old_status, new_status)

        Task.objects.filter(pk=task.id, user=self.request.user).update(deleted=True)

        return HttpResponseRedirect(self.get_success_url())


class UserLoginView(LoginView):
    template_name = 'user_login.html'
    extra_context = { 'title': 'Task Manager' }

class UserCreateView(CreateView):
    form_class = UserCreationForm
    template_name = "user_create.html"
    extra_context = { 'title': 'Task Manager' }
    success_url = "/tasks"


class GenericTaskView(LoginRequiredMixin, ListView):
    template_name = 'tasks.html'
    context_object_name = 'tasks'
    paginate_by = 3

    def get_queryset(self):
        return Task.objects.filter(deleted=False, user=self.request.user).order_by('priority')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['completed_tasks_len'] = Task.objects.filter(completed=True, deleted=False, user=self.request.user).count()
        context['total_tasks_len'] = Task.objects.filter(deleted=False, user=self.request.user).count()
        return context


class GenericCompleteTaskView(LoginRequiredMixin, ListView):
    template_name = 'completed_tasks.html'
    context_object_name = 'completed_tasks'
    paginate_by = 3

    def get_queryset(self):
        return Task.objects.filter(completed=True, deleted=False, user=self.request.user).order_by('priority')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_tasks_len'] = Task.objects.filter(deleted=False, user=self.request.user).count()
        context['completed_tasks_len'] = Task.objects.filter(completed=True, deleted=False, user=self.request.user).count()
        return context


class GenericPendingTaskView(GenericTaskView):
    template_name = 'pending_tasks.html'
    context_object_name = 'pending_tasks'

    def get_queryset(self):
        return Task.objects.filter(completed=False, deleted=False, user=self.request.user).order_by('priority')


class TaskReportCreateForm(ModelForm):
    timezone = ChoiceField(choices=[(tz, tz) for tz in all_timezones], required=True)

    class Meta:
        model = TaskReport
        fields = ['user_mail', 'report_time', 'enabled']

class GenericTaskReportCreateView(LoginRequiredMixin, CreateView):
    form_class = TaskReportCreateForm
    template_name = 'task_report.html'
    extra_context = {'title': 'Schedule Task Report'}
    success_url = '/tasks'

    def form_valid(self, form): 
        if TaskReport.objects.filter(user=self.request.user).exists():
            raise ValidationError('You have already scheduled a report. Go to /update-report to update your report.')

        user_timezone = form.cleaned_data['timezone']
        task_report_form = form.save(commit=False)
        task_report_form.user = self.request.user
        task_report_form.next_run_at = get_next_run_at(task_report_form.report_time, user_timezone)
        task_report_form.save()
        self.object = task_report_form
        
        return HttpResponseRedirect(self.get_success_url())


def get_next_run_at(report_time, user_timezone='UTC'):
    tz = timezone(user_timezone)
    # Localize the current time as per user timezone
    curr_datetime = datetime.now().astimezone(tz)

    # Get the current time in user timezone
    curr_time = curr_datetime.time()
    curr_date = curr_datetime.date()

    # If report time is less than current time, start schedule from next day
    if report_time <= curr_time:
        curr_date += timedelta(days=1)

    # Get the next run time with date and time in user timezone
    report_time = datetime.combine(curr_date, report_time).astimezone(tz)

    return report_time.astimezone(timezone('UTC'))


class GenericTaskReportUpdateView(LoginRequiredMixin, UpdateView):
    model = TaskReport
    form_class = TaskReportCreateForm
    template_name = 'task_report.html'
    extra_context = {'title': 'Update Task Report'}
    success_url = '/tasks'

    def get_object(self):
        return TaskReport.objects.get(user=self.request.user)

    def form_valid(self, form):
        task_report_form = form.save(commit=False)
        user_timezone = form.cleaned_data['timezone']
        task_report_form.next_run_at = get_next_run_at(task_report_form.report_time, user_timezone)
        task_report_form.save()

        return HttpResponseRedirect(self.get_success_url())


def home_view(request):
    return HttpResponseRedirect('/tasks')
