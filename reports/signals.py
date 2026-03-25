from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone


@receiver(user_logged_in)
def track_login_time(sender, request, user, **kwargs):
    now = timezone.localtime()
    hour = now.hour

    # Only start the session timer during official working hours:
    # 10:00 AM – 12:59 PM  OR  2:00 PM – 9:59 PM
    if (10 <= hour < 13) or (14 <= hour < 22):
        reports_today = user.reports.filter(date=now.date()).count()
        if reports_today < 3:
            user.current_session_start = now
        else:
            user.current_session_start = None
    else:
        # Outside working hours → clear any stale session
        user.current_session_start = None

    user.is_online = True
    user.last_active = now
    user.save(update_fields=['current_session_start', 'is_online', 'last_active'])


@receiver(user_logged_out)
def track_logout_time(sender, request, user, **kwargs):
    if user:
        user.current_session_start = None
        user.is_online = False
        user.save(update_fields=['current_session_start', 'is_online'])
