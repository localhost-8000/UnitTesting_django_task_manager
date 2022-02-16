from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from rest_framework.routers import SimpleRouter
from tasks.api_views import TaskHistoryViewSet, TaskViewSet
from tasks.views import (GenericCompleteTaskView, GenericPendingTaskView,
                         GenericTaskCreateView, GenericTaskDeleteView,
                         GenericTaskDetailView, GenericTaskReportCreateView, GenericTaskReportUpdateView, GenericTaskUpdateView,
                         GenericTaskView, UserCreateView, UserLoginView,
                         home_view)

router = SimpleRouter()

router.register(r'tasks', TaskViewSet, basename='tasks_api')
router.register(r'task/(?P<task_id>\d+)/history', TaskHistoryViewSet)

urlpatterns = [
    path("", home_view, name="home"),
    path("admin/", admin.site.urls),
    path("user/signup/", UserCreateView.as_view(), name="create_user"),
    path("user/login/", UserLoginView.as_view(), name="login_user"),
    path("tasks", GenericTaskView.as_view(), name="tasks"),
    path("user/logout", LogoutView.as_view(), name="logout_user"),
    path("create-task", GenericTaskCreateView.as_view(), name="create_task"),
    path("update-task/<pk>", GenericTaskUpdateView.as_view(), name="update_task"),
    path("detail-task/<pk>", GenericTaskDetailView.as_view(), name="detail_task"),
    path("delete-task/<pk>", GenericTaskDeleteView.as_view(), name="delete_task"),
    path("completed-tasks", GenericCompleteTaskView.as_view(), name="completed_tasks"),
    path("pending-tasks", GenericPendingTaskView.as_view(), name="pending_tasks"),
    path("report", GenericTaskReportCreateView.as_view(), name="task_report"),
    path("update-report", GenericTaskReportUpdateView.as_view(), name="update_report"),
    path("api/v1/", include(router.urls)),
]

