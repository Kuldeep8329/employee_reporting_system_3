import os
import shutil
from django.conf import settings
from reports.models import User

# Configuration
USERNAME = 'Think_thank-01'
SEARCH_DIR = r'C:\Users\Admin\.gemini\antigravity\brain\7085a400-9986-4319-b6e8-4fcb610ed4a9'
TARGET_DIR = os.path.join(settings.MEDIA_ROOT, 'profile_photos')

def update_photo():
    # 1. Find newest image artifact
    files = [os.path.join(SEARCH_DIR, f) for f in os.listdir(SEARCH_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not files:
        print("No images found in brain directory.")
        return
    
    newest_file = max(files, key=os.path.getmtime)
    print(f"Newest artifact found: {newest_file}")
    
    # 2. Get the user
    try:
        user = User.objects.get(username=USERNAME)
    except User.DoesNotExist:
        print(f"User {USERNAME} not found.")
        return

    # 3. Create target directory if needed
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # 4. Copy and Rename
    ext = os.path.splitext(newest_file)[1]
    filename = f"vaishnavi_mahajan{ext}"
    target_path = os.path.join(TARGET_DIR, filename)
    shutil.copy2(newest_file, target_path)
    print(f"Copied to {target_path}")
    
    # 5. Update DB
    user.profile_photo = f"profile_photos/{filename}"
    user.save()
    print(f"User {USERNAME} profile photo updated successfully.")

if __name__ == "__main__":
    update_photo()
