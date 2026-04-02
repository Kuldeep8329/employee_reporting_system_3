import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports.models import User

# Mapping: (username, photo_path)
updates = [
    ('Dev-03', 'profile_photos/durgesh_suryavanshi.jpg'),
    ('Think_thank-03', 'profile_photos/jayesh_joshi.jpg'),
    ('Chanakya01', 'profile_photos/aniket_mali.jpg'),
    ('Dev_ld', 'profile_photos/khushal_mali.jpg'),
]

for username, photo_path in updates:
    try:
        user = User.objects.get(username=username)
        user.profile_photo = photo_path
        user.save()
        print(f"Updated profile photo for {user.get_full_name()} ({username})")
    except User.DoesNotExist:
        print(f"Error: User {username} not found.")
    except Exception as e:
        print(f"Error updating {username}: {str(e)}")
