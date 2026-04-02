from django import forms
from .models import DailyReport, LeaveRequest, IssueReport

class IssueReportForm(forms.ModelForm):
    class Meta:
        model = IssueReport
        fields = ['title', 'module_page', 'issue_type', 'severity', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief title of the issue'}),
            'module_page': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Dashboard, Login Page, etc.'}),
            'issue_type': forms.Select(attrs={'class': 'form-control'}),
            'severity': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe the issue in detail...'}),
        }

class DailyReportForm(forms.ModelForm):
    class Meta:
        model = DailyReport
        fields = ['date', 'work_description', 'hours_worked', 'work_duration_calc']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'readonly': 'readonly'}),
            'work_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'hours_worked': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
            'work_duration_calc': forms.HiddenInput(),
        }

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Please provide a reason for your leave...'}),
        }
        labels = {
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'reason': 'Reason for Leave'
        }
