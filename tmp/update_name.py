import os
import sys
import django

# Add project root to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports.models import User

# Update "Rohini Ganukonda" to "Rohini Gunukonda"
try:
    # First search case-insensitively
    user = User.objects.filter(first_name__iexact='Rohini', last_name__iexact='Ganukonda').first()
    if user:
        old_name = f"{user.first_name} {user.last_name}"
        user.last_name = 'Gunukonda'
        user.save()
        print(f"Updated user: {user.username} - {old_name} -> {user.first_name} {user.last_name}")
    else:
        print("User with name Rohini Ganukonda not found.")
except Exception as e:
    print(f"Error: {e}")
