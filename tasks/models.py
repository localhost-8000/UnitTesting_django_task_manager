
from django.db import models

from django.contrib.auth.models import User


STATUS_CHOICES = (
    ("PENDING", "PENDING"),
    ("IN_PROGRESS", "IN_PROGRESS"),
    ("COMPLETED", "COMPLETED"),
    ("CANCELLED", "CANCELLED"),
)

class Task(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    completed = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField(default=False)
    priority = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=100, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0])
    user = models.ForeignKey(User , on_delete=models.CASCADE , null=True,blank=True)

    def __str__(self):
        return self.title
    
    def pretty_date(self):
        return self.created_date.strftime("%a %d %b")


class TaskHistory(models.Model):
    task = models.ForeignKey(Task, related_name='tasks', on_delete=models.CASCADE)
    old_status = models.CharField(max_length=100, choices=STATUS_CHOICES, default=None)
    new_status = models.CharField(max_length=100, choices=STATUS_CHOICES, default=STATUS_CHOICES[0][0])
    updated_date = models.DateTimeField(auto_now=True)


class TaskReport(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_mail = models.EmailField(null=True)
    report_time = models.TimeField(auto_now=False, auto_now_add=False, default="12:00:00")
    next_run_at = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    enabled = models.BooleanField(default=True)
