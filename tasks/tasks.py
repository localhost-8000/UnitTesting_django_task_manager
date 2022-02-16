
from datetime import datetime, timedelta

from celery import shared_task
from django.core.mail import send_mail
from pytz import timezone

from tasks.models import Task, TaskReport


@shared_task(name="send_periodic_reportes_to_user")
def send_email_report():

    curr_time = datetime.now(tz=timezone('UTC'))
    # Get the schedules that is enabled and sending is due
    curr_schedules = TaskReport.objects.filter(enabled=True, next_run_at__lte=curr_time)

    for schedule in curr_schedules:
        user = schedule.user
        user_mail = schedule.user_mail

        # Get the email content and send the mail
        email_content = get_user_tasks_status(user)
        send_mail("Tasks Report for Today", email_content, "rt945471@gmail.com", [user_mail])

        # Update the next run at for the current user task report
        next_run_at = schedule.next_run_at + timedelta(days=1)
        TaskReport.objects.filter(user=user).update(next_run_at=next_run_at)


def get_user_tasks_status(user):
    total_tasks = Task.objects.filter(user=user, deleted=False)
    pending_tasks = total_tasks.filter(status='PENDING').count()
    completed_tasks = total_tasks.filter(status='COMPLETED').count()
    in_progress_tasks = total_tasks.filter(status='IN_PROGRESS').count()
    cancelled_tasks = total_tasks.filter(status='CANCELLED').count()
    message = f"Hi {user.username},\n\nHere is your tasks report for today:\n\nTotal tasks added: {total_tasks.count()}\nPending tasks: {pending_tasks}\nIn Progress tasks: {in_progress_tasks}\nCompleted tasks: {completed_tasks}\nCancelled tasks: {cancelled_tasks}\n\nThanks"
    return message

