from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.db.models import Sum, Count
from django.http import HttpResponse, JsonResponse
from .models import DailyReport, FinalReport, Team, User, LeaveRequest, IssueReport
from django.utils import timezone
from datetime import datetime, timedelta
from .forms import DailyReportForm, LeaveRequestForm, IssueReportForm
import openpyxl
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa

@login_required
def leave_request(request):
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.user = request.user
            leave.status = 'pending'
            leave.save()
            messages.success(request, "Leave request submitted successfully. Waiting for Team Leader approval.")
            return redirect('employee_dashboard')
    else:
        form = LeaveRequestForm()
    
    my_leaves = LeaveRequest.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'reports/leave_request.html', {'form': form, 'my_leaves': my_leaves})

@login_required
def approve_leave(request, leave_id):
    if request.user.role != 'team_leader' and request.user.role != 'admin' and request.user.role != 'superadmin':
        return redirect('home')
    
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    # Ensure leader can only approve their own team members' leaves
    if request.user.role == 'team_leader' and leave.user.team != request.user.led_team:
        messages.error(request, "You can only approve leaves for your own team.")
        return redirect('team_leader_dashboard')

    if 'approve' in request.POST:
        leave.status = 'approved'
        leave.approved_by = request.user
        leave.save()
        messages.success(request, f"Leave request for {leave.user.get_full_name()} approved.")
    elif 'reject' in request.POST:
        leave.status = 'rejected'
        leave.save()
        messages.warning(request, f"Leave request for {leave.user.get_full_name()} rejected.")
    elif 'review' in request.POST:
        leave.status = 'reviewing'
        leave.save()
        messages.info(request, f"Leave request for {leave.user.get_full_name()} is now in review.")
        
    return redirect(request.META.get('HTTP_REFERER', 'home'))

def logout_view(request):
    if request.user.is_authenticated and request.user.current_session_start:
        now = timezone.localtime()
        diff = now - request.user.current_session_start
        delta_ms = int(diff.total_seconds() * 1000)
        request.user.accumulated_ms += delta_ms
        request.user.current_session_start = None
        # Keep first_timer_start so it persists across login/logout session resumes
        request.user.last_timer_date = now.date() 
        request.user.save()
    logout(request)
    return redirect('login')

@login_required
def home(request):
    if request.user.role == 'superadmin':
        return redirect('superadmin_dashboard')
    if request.user.role == 'manager':
        return redirect('manager_dashboard')
    
    # Employee, Team Leader, and Admin all need time-tracking capabilities, 
    # so their central routing brings them to the employee dashboard initially.
    return redirect('employee_dashboard')

@login_required
def employee_dashboard(request):
    reports = DailyReport.objects.filter(user=request.user).order_by('-date')
    form = DailyReportForm()
    now = timezone.localtime()
    
    # --- DATE RESET LOGIC (Midnight Flip) ---
    # Trigger reset if today is a different day than the last recorded timer activity
    if request.user.last_timer_date and request.user.last_timer_date != now.date():
        request.user.accumulated_ms = 0
        request.user.first_timer_start = None
        if request.user.current_session_start:
            request.user.current_session_start = now
            request.user.first_timer_start = now
        request.user.last_timer_date = now.date()
        request.user.save()

    # --- AUTO-START LOGIC ---
    if request.user.role == 'employee' and not request.user.current_session_start:
        reports_today = DailyReport.objects.filter(user=request.user, created_at__date=now.date()).count()
        if reports_today < 3:
            # Auto-start session
            if request.user.accumulated_ms == 0:
                request.user.first_timer_start = now
            request.user.current_session_start = now
            request.user.last_timer_date = now.date()
            request.user.save()

    # Session tracking
    session_start = request.user.current_session_start
    session_start_iso = session_start.isoformat() if session_start else ""
    first_start = request.user.first_timer_start
    first_start_iso = first_start.isoformat() if first_start else ""
    accumulated_ms = request.user.accumulated_ms

    if request.method == 'POST':
        # Enforce 3 reports per day limit
        reports_today = DailyReport.objects.filter(user=request.user, created_at__date=timezone.localtime().date()).count()
        if reports_today >= 3:
            messages.error(request, "You have already submitted 3 reports today.")
            return redirect('employee_dashboard')

        form = DailyReportForm(request.POST)
        if form.is_valid():
            try:
                report = form.save(commit=False)
                report.user = request.user
                report.save()
                return redirect('employee_dashboard')
            except Exception as e:
                messages.error(request, f"Error saving report: {str(e)}")

    return render(request, 'reports/employee_dashboard.html', {
        'reports': reports, 
        'form': form,
        'session_start_iso': session_start_iso,
        'first_start_iso': first_start_iso,
        'accumulated_ms': accumulated_ms,
        'server_now_iso': now.isoformat()
    })

@login_required
def start_timer(request):
    if request.method == 'POST':
        now = timezone.localtime()
        
        # Enforce 3 reports per day limit
        reports_today = DailyReport.objects.filter(user=request.user, created_at__date=now.date()).count()
        if reports_today >= 3:
            messages.error(request, "You have already submitted 3 reports today. Maximum allowed is 3 per day.")
            return redirect('employee_dashboard')
            
        if request.user.accumulated_ms == 0:
            request.user.first_timer_start = now
            
        request.user.current_session_start = now
        request.user.last_timer_date = now.date()
        request.user.save()
        messages.success(request, "Work session started successfully.")
    return redirect('employee_dashboard')

@login_required
def heartbeat(request):
    if request.method == 'POST':
        now = timezone.localtime()
        request.user.last_active = now
        request.user.is_online = True
        
        # Handle Date Change: Reset timer if day has flipped
        if request.user.last_timer_date and request.user.last_timer_date != now.date():
            request.user.accumulated_ms = 0
            request.user.first_timer_start = None
            if request.user.current_session_start:
                request.user.current_session_start = now
                request.user.first_timer_start = now
            request.user.last_timer_date = now.date()

        # If timer is running, calculate delta and add to accumulation
        if request.user.current_session_start:
            diff = now - request.user.current_session_start
            delta_ms = int(diff.total_seconds() * 1000)
            
            # Failsafe cap: 120s per heartbeat
            if delta_ms > 0:
                request.user.accumulated_ms += min(delta_ms, 120000)
            
            request.user.current_session_start = now
        
        try:
            request.user.save()
            return JsonResponse({
                'status': 'ok', 
                'accumulated_ms': request.user.accumulated_ms,
                'session_start_iso': request.user.current_session_start.isoformat() if request.user.current_session_start else "",
                'server_now': now.isoformat()
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def pause_timer(request):
    if request.method == 'POST':
        if request.user.current_session_start:
            now = timezone.localtime()
            diff = now - request.user.current_session_start
            delta_ms = int(diff.total_seconds() * 1000)
            
            request.user.accumulated_ms += delta_ms
            request.user.current_session_start = None
            request.user.save()
            messages.success(request, "Work session paused successfully.")
        return redirect('employee_dashboard')
    return redirect('employee_dashboard')

@login_required
def stop_timer(request):
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            # You could store duration in session if needed
        except:
            pass
        request.user.current_session_start = None
        request.user.first_timer_start = None
        request.user.accumulated_ms = 0 # Reset after submission
        request.user.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def submit_report(request):
    duration = request.GET.get('duration', '0.0')
    duration_str = request.GET.get('timer', '00:00:00')
    
    if request.method == 'POST':
        # ALWAYS stop and reset timer when report is actually submitted
        request.user.current_session_start = None
        request.user.first_timer_start = None
        request.user.accumulated_ms = 0
        request.user.save()

        now = timezone.localtime()
        # Enforce 3 reports per day limit
        reports_today = DailyReport.objects.filter(user=request.user, created_at__date=now.date()).count()
        if reports_today >= 3:
            messages.error(request, "You have already submitted 3 reports today.")
            return redirect('employee_dashboard')

        form = DailyReportForm(request.POST)
        if form.is_valid():
            try:
                report = form.save(commit=False)
                report.user = request.user
                report.status = 'pending'
                report.save()
                messages.success(request, "Report submitted successfully! Waiting for approval.")
                return redirect('employee_dashboard')
            except Exception as e:
                messages.error(request, f"Submission error: {str(e)}")
    else:
        form = DailyReportForm(initial={
            'date': timezone.localtime().date(),
            'hours_worked': duration,
            'work_duration_calc': duration_str
        })
        try:
            form.fields['hours_worked'].widget.attrs['max'] = float(duration) + 0.1
        except:
            form.fields['hours_worked'].widget.attrs['max'] = 12
        
    return render(request, 'reports/submit_report.html', {'form': form, 'duration_str': duration_str})

@login_required
def team_leader_dashboard(request):
    if not request.user.is_team_leader():
        return redirect('home')
    
    team = request.user.led_team
    if not team:
        return render(request, 'reports/team_leader_dashboard.html', {'error': 'You are not assigned to any team as leader.'})
    
    # Fetch pending daily reports (timesheets) — Exclude self-reports for admin approval
    reports = DailyReport.objects.select_related('user').filter(
        user__team=team, 
        status='pending'
    ).exclude(user=request.user).order_by('-created_at')

    # Fetch pending/reviewing leave requests
    leave_requests = LeaveRequest.objects.select_related('user').filter(
        user__team=team, 
        status__in=['pending', 'reviewing']
    ).order_by('-created_at')

    # Fetch processed leave requests (approved/rejected history)
    processed_leaves = LeaveRequest.objects.select_related('user').filter(
        user__team=team,
        status__in=['approved', 'rejected']
    ).order_by('-updated_at')[:20] # Last 20 processed
    
    # Fetch pending/reviewing issue reports for display
    issue_reports = IssueReport.objects.select_related('user').filter(
        leader_notified=request.user, 
        status__in=['pending', 'reviewing']
    ).order_by('-created_at')

    # Metrics for the Boxes
    member_count = team.members.filter(role='employee').count()
    pending_leaves_count = leave_requests.count()
    pending_count = reports.count()
    issue_count = issue_reports.count()

    return render(request, 'reports/team_leader_dashboard.html', {
        'reports': reports,
        'leave_requests': leave_requests,
        'processed_leaves': processed_leaves,
        'issue_reports': issue_reports,
        'team_name': team.name,
        'team': team,
        'member_count': member_count,
        'pending_leaves_count': pending_leaves_count,
        'pending_count': pending_count,
        'issue_count': issue_count
    })

@login_required
def approve_report(request, report_id):
    report = get_object_or_404(DailyReport, id=report_id)
    
    if report.status != 'pending':
        messages.info(request, "This report has already been processed.")
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    # Team Leader logic — Accept direct employee reports
    if request.user.role == 'team_leader':
        if report.user == request.user:
            messages.error(request, "You cannot approve your own report. It must be approved by a Sub-Admin.")
            return redirect(request.META.get('HTTP_REFERER', 'home'))
            
        if report.user.team == request.user.led_team and report.user.role == 'employee':
            # Save to FinalReport (Permanent)
            FinalReport.objects.create(
                employee=report.user,
                leader=request.user,
                team=report.user.team,
                work_description=report.work_description,
                hours_worked=report.hours_worked,
                work_duration_calc=report.work_duration_calc,
                level='employee_level',
                status='accepted',
                date=report.date
            )
            report.status = 'accepted'
            report.accepted_by_leader_user = request.user
            report.save()
            messages.success(request, f"Employee report from {report.user.get_full_name()} accepted and saved to database.")
    
    # Sub-Admin logic — Accept direct Team Leader reports
    elif request.user.role == 'admin':
        if report.user.role == 'team_leader':
            # Save to FinalReport (Permanent)
            FinalReport.objects.create(
                leader=report.user,
                subadmin=request.user,
                team=report.user.team,
                work_description=report.work_description,
                hours_worked=report.hours_worked,
                work_duration_calc=report.work_duration_calc,
                level='leader_level',
                status='accepted',
                date=report.date
            )
            report.status = 'accepted'
            report.accepted_by_subadmin_user = request.user
            report.save()
            messages.success(request, f"Leader report from {report.user.get_full_name()} accepted and saved to database.")
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))
@login_required
def reject_report(request, report_id):
    # As per current requirements, only superadmins can reject reports.
    # Leaders, sub-admins and managers cannot reject.
    if request.user.role in ['team_leader', 'admin', 'manager'] and not request.user.is_superuser:
        messages.error(request, "You do not have permission to reject reports.")
        return redirect(request.META.get('HTTP_REFERER', 'home'))
    
    report = get_object_or_404(DailyReport, id=report_id)
    if request.user.role == 'superadmin' or request.user.is_superuser:
        if report.status == 'pending':
            report.status = 'rejected'
            report.save()
            messages.success(request, f"Report from {report.user.get_full_name()} has been rejected.")
        else:
            messages.info(request, "This report has already been processed.")
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def admin_dashboard(request):
    if request.user.role != 'admin' and request.user.role != 'superadmin':
        return redirect('home')
    
    # Sub-admin visibility: PENDING reports from Team Leaders
    pending_reports = DailyReport.objects.filter(user__role='team_leader', status='pending').order_by('-date')
    
    # Sub-admin visibility: FINAL reports (all levels)
    final_reports = FinalReport.objects.all().order_by('-date')
    
    # Filtering for Final Reports
    team_id = request.GET.get('team_id')
    leader_id = request.GET.get('leader_id')
    month = request.GET.get('month')
    
    if team_id:
        final_reports = final_reports.filter(team_id=team_id)
    if leader_id:
        final_reports = final_reports.filter(leader_id=leader_id)
    if month:
        try:
            year, m = month.split('-')
            final_reports = final_reports.filter(date__year=year, date__month=m)
        except ValueError:
            pass
    
    summary = final_reports.aggregate(total_hours=Sum('hours_worked'), count=Count('id'))
    teams = Team.objects.all()
    # Leaders for filtering
    leaders = User.objects.filter(role='team_leader')
    
    return render(request, 'reports/admin_dashboard.html', {
        'pending_reports': pending_reports,
        'final_reports': final_reports,
        'summary': summary,
        'teams': teams,
        'leaders': leaders
    })

@login_required
def manager_dashboard(request):
    if request.user.role != 'manager' and request.user.role != 'superadmin':
        return redirect('home')
    
    # Manager sees reports accepted by sub-admin (sent to manager)
    # or all reports for monitoring as requested
    reports = DailyReport.objects.all().order_by('-date')
    
    # Filter only fully qualified reports by default maybe?
    # Actually, "Sirf monitoring karega" suggests visibility of all stages.
    
    # Filtering
    user_id = request.GET.get('user_id')
    team_id = request.GET.get('team_id')
    month = request.GET.get('month')
    
    if user_id:
        reports = reports.filter(user_id=user_id)
    if team_id:
        reports = reports.filter(user__team_id=team_id)
    if month:
        try:
            year, m = month.split('-')
            reports = reports.filter(date__year=year, date__month=m)
        except ValueError:
            pass
            
    summary = reports.aggregate(total_hours=Sum('hours_worked'), count=Count('id'))
    teams = Team.objects.all()
    users = User.objects.all()
    
    return render(request, 'reports/manager_dashboard.html', {
        'reports': reports, 
        'summary': summary, 
        'teams': teams, 
        'users': users
    })

@login_required
def admin_team_detail(request, team_id):
    if not request.user.is_admin_role():
        return redirect('home')
    team = get_object_or_404(Team, id=team_id)
    employees = User.objects.filter(team=team, role='employee')
    
    return render(request, 'reports/admin_team_detail.html', {'team': team, 'employees': employees})

@login_required
def leader_employee_detail(request, user_id):
    """Team Leader view for an individual employee's reports — restricted to own team."""
    if request.user.role != 'team_leader':
        return redirect('home')
    try:
        leader_team = request.user.led_team
    except Exception:
        return redirect('team_leader_dashboard')

    employee = get_object_or_404(User, id=user_id, role='employee', team=leader_team)
    reports = DailyReport.objects.filter(user=employee).order_by('-date')

    duration = request.GET.get('duration', '')
    today = timezone.localtime().date()
    if duration == 'today':
        reports = reports.filter(date=today)
    elif duration == '7_days':
        reports = reports.filter(date__gte=today - timedelta(days=7))
    elif duration == '30_days':
        reports = reports.filter(date__gte=today - timedelta(days=30))

    # Fetch this employee's leave history
    leave_history = LeaveRequest.objects.filter(user=employee, status__in=['approved', 'rejected']).order_by('-updated_at')

    return render(request, 'reports/leader_employee_detail.html', {
        'employee': employee,
        'reports': reports,
        'duration': duration,
        'team': leader_team,
        'leave_history': leave_history
    })

@login_required
def admin_employee_detail(request, user_id):
    if not request.user.is_admin_role():
        return redirect('home')
    # Allow viewing both employees and team leaders
    employee = get_object_or_404(User, id=user_id)
    if employee.role not in ['employee', 'team_leader']:
         return redirect('home')
         
    reports = DailyReport.objects.filter(user=employee).order_by('-date')
    
    # Optional duration filter for the page itself
    duration = request.GET.get('duration')
    if duration == 'today':
        reports = reports.filter(date=timezone.localtime().date())
    elif duration == '7_days':
        reports = reports.filter(date__gte=timezone.localtime().date() - timedelta(days=7))
    elif duration == '30_days':
        reports = reports.filter(date__gte=timezone.localtime().date() - timedelta(days=30))
        
    return render(request, 'reports/admin_employee_detail.html', {'employee': employee, 'reports': reports, 'duration': duration})

@login_required
def superadmin_dashboard(request):
    if request.user.role != 'superadmin':
        return redirect('home')
    
    users = User.objects.all()
    reports = DailyReport.objects.all()
    teams = Team.objects.all()
    
    return render(request, 'reports/superadmin_dashboard.html', {'users': users, 'reports': reports, 'teams': teams})

def export_excel_logic(reports, filename_prefix="reports"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Approved Reports"
    
    headers = ['Level', 'Employee', 'Leader', 'Sub-Admin', 'Team', 'Date', 'Description', 'Hours']
    ws.append(headers)
    
    for report in reports:
        ws.append([
            report.get_level_display(),
            report.employee.get_full_name() if report.employee else 'N/A',
            report.leader.get_full_name() if report.leader else 'N/A',
            report.subadmin.get_full_name() if report.subadmin else 'N/A',
            report.team.name if report.team else 'N/A',
            report.date.strftime('%Y-%m-%d'),
            report.work_description,
            report.hours_worked
        ])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename_prefix}_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    wb.save(response)
    return response

def export_excel_combined(data_list, filename_prefix="all_reports"):
    import openpyxl
    from io import BytesIO
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reports"
    headers = ['Status', 'Employee', 'Leader', 'Team', 'Date', 'Description', 'Hours']
    ws.append(headers)
    for r in data_list:
        ws.append([
            r.get('level', r.get('status', '--')),
            r.get('employee_name', r.get('employee', '--')),
            r.get('leader_name', r.get('leader', '--')),
            r.get('team_name', '--'),
            r.get('date'),
            r.get('description', '--'),
            r.get('hours', 0)
        ])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename_prefix}_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    wb.save(response)
    return response

@login_required
def export_excel(request):
    # Determine records to include: Strictly separate PENDING (active) and FINALIZED (archived)
    if request.user.role == 'team_leader':
        # Team Leader gets their team's PENDING DailyReports + All FINALIZED reports
        daily_reports = DailyReport.objects.filter(user__team=request.user.led_team, status='pending')
        final_reports = FinalReport.objects.filter(team=request.user.led_team)
    elif request.user.role in ['admin', 'superadmin', 'manager']:
        # Admin roles see all PENDING + all FINALIZED
        daily_reports = DailyReport.objects.filter(status='pending')
        final_reports = FinalReport.objects.all()
    else:
        # Default fallback (e.g. Employee only sees their own finalized if they can export)
        daily_reports = DailyReport.objects.none()
        final_reports = FinalReport.objects.filter(employee=request.user)

    # Apply Common Filtering to both querysets
    team_id = request.GET.get('team_id')
    leader_id = request.GET.get('leader_id')
    user_id = request.GET.get('user_id')
    month = request.GET.get('month')
    duration = request.GET.get('duration')
    
    if team_id:
        daily_reports = daily_reports.filter(user__team_id=team_id)
        final_reports = final_reports.filter(team_id=team_id)
    if leader_id:
        daily_reports = daily_reports.filter(user__team__leader_id=leader_id)
        final_reports = final_reports.filter(leader_id=leader_id)
    if user_id:
        daily_reports = daily_reports.filter(user_id=user_id)
        final_reports = final_reports.filter(employee_id=user_id)
    if month:
        try:
            year, m = month.split('-')
            daily_reports = daily_reports.filter(date__year=year, date__month=m)
            final_reports = final_reports.filter(date__year=year, date__month=m)
        except ValueError:
            pass
        
    if duration == 'today':
        today = timezone.localtime().date()
        daily_reports = daily_reports.filter(date=today)
        final_reports = final_reports.filter(date=today)
    elif duration == '7_days':
        # Exactly last 7 cycles including today
        d = timezone.localtime().date() - timedelta(days=6)
        daily_reports = daily_reports.filter(date__gte=d)
        final_reports = final_reports.filter(date__gte=d)
    elif duration == '30_days':
        # Exactly last 30 cycles including today
        d = timezone.localtime().date() - timedelta(days=29)
        daily_reports = daily_reports.filter(date__gte=d)
        final_reports = final_reports.filter(date__gte=d)
        
    # Combine results into a list of simplified objects/dicts for logic helper
    combined_list = []
    
    # Process DailyReports (Status=Pending, Accepted_by_leader, etc.)
    for r in daily_reports.order_by('-date'):
        combined_list.append({
            'level': r.get_status_display(),
            'employee_name': r.user.get_full_name() or r.user.username,
            'leader_name': (r.user.team.leader.get_full_name() if r.user.team and r.user.team.leader else "--"),
            'subadmin_name': "--",
            'team_name': r.user.team.name if r.user.team else "--",
            'date': r.date,
            'description': r.work_description,
            'hours': r.hours_worked
        })
        
    # Process FinalReports (Status=Accepted)
    for r in final_reports.order_by('-date'):
        combined_list.append({
            'level': r.get_level_display(),
            'employee_name': r.employee.get_full_name() if r.employee else (r.leader.get_full_name() if r.level == 'leader_level' else "--"),
            'leader_name': r.leader.get_full_name() if r.leader else "--",
            'subadmin_name': r.subadmin.get_full_name() if r.subadmin else "--",
            'team_name': r.team.name if r.team else "--",
            'date': r.date,
            'description': r.work_description,
            'hours': r.hours_worked
        })

    # Since export_excel_logic handles querysets, I should probably adapt it or use a simpler helper
    # I'll create a new helper just for this combined format
    return export_excel_combined(combined_list, filename_prefix=f"{request.user.role}_all_reports")

# Processing continued for PDF logic...
@login_required
def export_pdf(request):
    if request.user.role == 'team_leader':
        daily_reports = DailyReport.objects.filter(user__team=request.user.led_team, status='pending')
        final_reports = FinalReport.objects.filter(team=request.user.led_team)
    elif request.user.role in ['admin', 'superadmin', 'manager']:
        daily_reports = DailyReport.objects.filter(status='pending')
        final_reports = FinalReport.objects.all()
    else:
        daily_reports = DailyReport.objects.none()
        final_reports = FinalReport.objects.filter(employee=request.user)
    
    # Common Filtering
    team_id = request.GET.get('team_id')
    leader_id = request.GET.get('leader_id')
    user_id = request.GET.get('user_id')
    month = request.GET.get('month')
    duration = request.GET.get('duration')
    
    if team_id:
        daily_reports = daily_reports.filter(user__team_id=team_id)
        final_reports = final_reports.filter(team_id=team_id)
    if leader_id:
        daily_reports = daily_reports.filter(user__team__leader_id=leader_id)
        final_reports = final_reports.filter(leader_id=leader_id)
    if user_id:
        daily_reports = daily_reports.filter(user_id=user_id)
        final_reports = final_reports.filter(employee_id=user_id)
    if month:
        try:
            year, m = month.split('-')
            daily_reports = daily_reports.filter(date__year=year, date__month=m)
            final_reports = final_reports.filter(date__year=year, date__month=m)
        except ValueError:
            pass

    if duration == 'today':
        today = timezone.localtime().date()
        daily_reports = daily_reports.filter(date=today)
        final_reports = final_reports.filter(date=today)
    elif duration == '7_days':
        d = timezone.localtime().date() - timedelta(days=6)
        daily_reports = daily_reports.filter(date__gte=d)
        final_reports = final_reports.filter(date__gte=d)
    elif duration == '30_days':
        d = timezone.localtime().date() - timedelta(days=29)
        daily_reports = daily_reports.filter(date__gte=d)
        final_reports = final_reports.filter(date__gte=d)
        
    combined_list = []
    # Simplified unified structure for PDF
    for r in daily_reports.order_by('-date'):
        combined_list.append({
            'status': r.get_status_display(),
            'employee': r.user.get_full_name() or r.user.username,
            'leader': (r.user.team.leader.get_full_name() if r.user.team and r.user.team.leader else "--"),
            'team': r.user.team.name if r.user.team else "--",
            'date': r.date,
            'description': r.work_description,
            'hours': r.hours_worked
        })
    for r in final_reports.order_by('-date'):
        combined_list.append({
            'status': 'Saved / Finalized',
            'employee': r.employee.get_full_name() if r.employee else (r.leader.get_full_name() if r.level == 'leader_level' else "--"),
            'leader': r.leader.get_full_name() if r.leader else "--",
            'team': r.team.name if r.team else "--",
            'date': r.date,
            'description': r.work_description,
            'hours': r.hours_worked
        })

    template_path = 'reports/pdf_report.html'
    context = {'reports': combined_list, 'date': datetime.now(), 'request': request}
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="final_reports_{datetime.now().strftime("%Y%m%d")}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
       return HttpResponse('Error generating PDF')
    return response

@login_required
def issue_tracker(request):
    """Employee view to report and see their issues."""
    issues = IssueReport.objects.filter(user=request.user).order_by('-created_at')
    if request.method == 'POST':
        form = IssueReportForm(request.POST)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.user = request.user
            # Automatically assign to their team leader
            if request.user.team and request.user.team.leader:
                issue.leader_notified = request.user.team.leader
            issue.save()
            messages.success(request, "Issue reported successfully. It is now pending leader review.")
            return redirect('issue_tracker')
    else:
        form = IssueReportForm()
    
    return render(request, 'reports/issue_tracker.html', {
        'form': form,
        'issues': issues
    })

@login_required
def leader_issue_action(request, issue_id, action):
    """Team Leader view to Accept, Reject, or Review an issue."""
    if request.user.role != 'team_leader':
        messages.error(request, "Only Team Leaders can perform this action.")
        return redirect('employee_dashboard')
    
    issue = get_object_or_404(IssueReport, id=issue_id, leader_notified=request.user)
    
    if action == 'accept':
        issue.status = 'accepted'
        messages.success(request, f"Issue '{issue.title}' accepted and escalated to Admin.")
    elif action == 'reject':
        issue.status = 'rejected'
        messages.success(request, f"Issue '{issue.title}' rejected.")
    elif action == 'review':
        issue.status = 'reviewing'
        messages.info(request, f"Issue '{issue.title}' is now in review.")
    
    issue.save()
    return redirect('team_leader_dashboard')

@login_required
def export_issues_pdf(request):
    """Generate PDF for issues, filtered by team or member."""
    if request.user.role != 'team_leader':
        return redirect('home')
    
    team = request.user.led_team
    issues = IssueReport.objects.filter(leader_notified=request.user).order_by('-created_at')
    
    # Filter by specific member if requested
    member_id = request.GET.get('member_id')
    if member_id:
        issues = issues.filter(user_id=member_id)
        
    template_path = 'reports/issues_pdf.html'
    context = {
        'issues': issues,
        'team_name': team.name,
        'date': timezone.now(),
        'generated_by': request.user.get_full_name() or request.user.username
    }
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="team_issues_{timezone.now().strftime("%Y%m%d")}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF')
    return response

@login_required
def admin_issue_list(request):
    """Admin view to see all accepted issues."""
    if request.user.role not in ['admin', 'superadmin', 'manager']:
        messages.error(request, "Access denied.")
        return redirect('employee_dashboard')
    
    # Show only accepted (for admin to resolve) or resolved (history)
    issues = IssueReport.objects.filter(status__in=['accepted', 'resolved']).order_by('-updated_at')
    
    if request.method == 'POST':
        issue_id = request.POST.get('issue_id')
        notes = request.POST.get('admin_notes', '')
        issue = get_object_or_404(IssueReport, id=issue_id)
        issue.status = 'resolved'
        issue.admin_notes = notes
        issue.save()
        messages.success(request, "Issue marked as Resolved.")
        return redirect('admin_issue_list')

    return render(request, 'reports/admin_issue_tracker.html', {'issues': issues})
