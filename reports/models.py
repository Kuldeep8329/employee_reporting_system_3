from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ('employee', 'Employee'),
        ('team_leader', 'Team Leader'),
        ('admin', 'Sub-Admin'),
        ('manager', 'Manager'),
        ('superadmin', 'SuperAdmin'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    team = models.ForeignKey('Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    current_session_start = models.DateTimeField(null=True, blank=True)
    first_timer_start = models.DateTimeField(null=True, blank=True)
    accumulated_ms = models.BigIntegerField(default=0)
    last_timer_date = models.DateField(null=True, blank=True)
    last_active = models.DateTimeField(null=True, blank=True)
    is_online = models.BooleanField(default=False)

    def is_currently_online(self):
        from django.utils import timezone
        import datetime
        if self.last_active:
            return timezone.localtime() - self.last_active < datetime.timedelta(seconds=60)
        return False

    def is_employee(self):
        return self.role == 'employee' or self.is_superuser

    def is_team_leader(self):
        return self.role == 'team_leader' or self.is_superuser

    def is_admin_role(self):
        return self.role in ['admin', 'manager', 'superadmin'] or self.is_superuser

class Team(models.Model):
    name = models.CharField(max_length=100)
    leader = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='led_team')
    logo = models.ImageField(upload_to='team_logos/', null=True, blank=True)

    def __str__(self):
        return self.name

class DailyReport(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('accepted', 'Accepted & Saved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    date = models.DateField(default=timezone.now)
    work_description = models.TextField()
    hours_worked = models.DecimalField(max_digits=4, decimal_places=2)
    work_duration_calc = models.CharField(max_length=20, null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')
    
    # Traceability
    accepted_by_leader_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='leader_approvals_tmp')
    accepted_by_subadmin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='subadmin_approvals_tmp')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.date}"

class FinalReport(models.Model):
    LEVEL_CHOICES = (
        ('employee_level', 'Employee Level (Approved by Leader)'),
        ('leader_level', 'Leader Level (Approved by Sub-Admin)'),
    )

    employee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='final_employee_reports')
    leader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='final_leader_reports')
    subadmin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='final_subadmin_reports')
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='final_team_reports')

    work_description = models.TextField()
    hours_worked = models.DecimalField(max_digits=4, decimal_places=2)
    work_duration_calc = models.CharField(max_length=20, null=True, blank=True)

    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    status = models.CharField(max_length=20, default='accepted')
    date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Final: {self.level} - {self.date}"

class LeaveRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('reviewing', 'In Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Traceability
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='leave_approvals')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.start_date} to {self.end_date}"

class IssueReport(models.Model):
    ISSUE_TYPE_CHOICES = (
        ('bug', 'Bug/Error'),
        ('ui', 'UI/UX Issue'),
        ('feature', 'Feature Request'),
        ('other', 'Other'),
    )
    SEVERITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending Leader Approval'),
        ('reviewing', 'In Review'),
        ('accepted', 'Accepted by Leader'),
        ('rejected', 'Rejected by Leader'),
        ('resolved', 'Resolved by Admin'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reported_issues')
    title = models.CharField(max_length=200)
    module_page = models.CharField(max_length=100)
    description = models.TextField()
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Traceability
    leader_notified = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='leader_issue_reviews')
    admin_notes = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.status})"
