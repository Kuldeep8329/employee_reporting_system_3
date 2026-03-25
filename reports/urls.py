from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='reports/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    path('dashboard/employee/', views.employee_dashboard, name='employee_dashboard'),
    path('dashboard/start-timer/', views.start_timer, name='start_timer'),
    path('dashboard/pause-timer/', views.pause_timer, name='pause_timer'),
    path('dashboard/issue-tracker/', views.issue_tracker, name='issue_tracker'),
    path('dashboard/issue-action/<int:issue_id>/<str:action>/', views.leader_issue_action, name='leader_issue_action'),
    path('dashboard/admin-issues/', views.admin_issue_list, name='admin_issue_list'),
    path('dashboard/stop-timer/', views.stop_timer, name='stop_timer'),
    path('dashboard/submit-report/', views.submit_report, name='submit_report'),
    path('dashboard/team-leader/', views.team_leader_dashboard, name='team_leader_dashboard'),
    path('dashboard/team-leader/employee/<int:user_id>/', views.leader_employee_detail, name='leader_employee_detail'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/admin/team/<int:team_id>/', views.admin_team_detail, name='admin_team_detail'),
    path('dashboard/admin/employee/<int:user_id>/', views.admin_employee_detail, name='admin_employee_detail'),
    path('leave-request/', views.leave_request, name='leave_request'),
    path('approve-leave/<int:leave_id>/', views.approve_leave, name='approve_leave'),
    path('dashboard/manager/', views.manager_dashboard, name='manager_dashboard'),
    path('dashboard/superadmin/', views.superadmin_dashboard, name='superadmin_dashboard'),
    
    path('report/approve/<int:report_id>/', views.approve_report, name='approve_report'),
    path('report/reject/<int:report_id>/', views.reject_report, name='reject_report'),
    
    path('api/heartbeat/', views.heartbeat, name='heartbeat'),
    path('export/excel/', views.export_excel, name='export_excel'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
    path('export/issues/pdf/', views.export_issues_pdf, name='export_issues_pdf'),
]
