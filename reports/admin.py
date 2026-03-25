from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Team, DailyReport

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'role', 'team', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Team', {'fields': ('role', 'team')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role & Team', {'fields': ('role', 'team')}),
    )

class DailyReportAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'hours_worked', 'status', 'created_at']
    list_filter = ['status', 'date', 'user__team']
    search_fields = ['user__username', 'work_description']
    actions = ['approve_reports', 'reject_reports']

    @admin.action(description="Approve selected reports")
    def approve_reports(self, request, queryset):
        queryset.update(status='approved')

    @admin.action(description="Reject selected reports")
    def reject_reports(self, request, queryset):
        queryset.update(status='rejected')

class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'leader']
    search_fields = ['name']

admin.site.register(User, CustomUserAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(DailyReport, DailyReportAdmin)
