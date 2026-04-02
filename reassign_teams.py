import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'employee_reporting_system.settings')
django.setup()

from reports.models import User, Team

# 1. Identity Check
print("--- USERS ---")
users = User.objects.all()
for u in users:
    print(f"{u.id}: {u.username} - {u.first_name} {u.last_name}")

print("\n--- TEAMS ---")
teams = Team.objects.all()
for t in teams:
    leader_name = t.leader.get_full_name() if t.leader else "None"
    print(f"Team {t.id}: {t.name} (Leader: {leader_name})")

# Reassignment Logic
def reassign():
    # Durgesh -> Kuldeep
    durgesh = (User.objects.filter(first_name__icontains='Durgesh') | 
               User.objects.filter(username__icontains='Durgesh')).first()
    kuldeep = (User.objects.filter(first_name__icontains='Kuldeep') | 
               User.objects.filter(username__icontains='Kuldeep')).first()
    
    # Chetan -> Khushal
    chetan = (User.objects.filter(first_name__icontains='Chetan') | 
               User.objects.filter(username__icontains='Chetan')).first()
    khushal = (User.objects.filter(first_name__icontains='Khushal') | 
               User.objects.filter(username__icontains='Khushal')).first()

    print("\nAttempting Reassignment:")
    if durgesh and kuldeep:
        # Find Kuldeep's group
        # Kuldeep might not be the leader of a team yet. The request says "give the leader there access"
        # We need check if he leads a team.
        kuldeep_team = Team.objects.filter(leader=kuldeep).first()
        if not kuldeep_team:
             print(f"Kuldeep has no team. Creating one or promoting...")
             # Maybe he's a leader but team isn't set?
             # I'll check his role.
             if kuldeep.role != 'team_leader':
                 kuldeep.role = 'team_leader'
                 kuldeep.save()
             # If no team exists with him as leader, we find a team that might belong to him
             # or create a generic one? Usually user wants us to find the existing one.
        
        if kuldeep_team:
            durgesh.team = kuldeep_team
            durgesh.save()
            print(f"Reassigned {durgesh.username} to Team: {kuldeep_team.name}")
        else:
            print(f"FAILED: No team found for Kuldeep.")

    if chetan and khushal:
        khushal_team = Team.objects.filter(leader=khushal).first()
        if not khushal_team:
             if khushal.role != 'team_leader':
                 khushal.role = 'team_leader'
                 khushal.save()
        
        if khushal_team:
            chetan.team = khushal_team
            chetan.save()
            print(f"Reassigned {chetan.username} to Team: {khushal_team.name}")
        else:
            print(f"FAILED: No team found for Khushal.")

if __name__ == "__main__":
    reassign()
