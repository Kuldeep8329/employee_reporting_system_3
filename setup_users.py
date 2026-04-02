import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reports.models import User, Team

def create_user(username, password, first_name, last_name, role, team=None):
    user, created = User.objects.get_or_create(username=username)
    user.set_password(password)
    user.first_name = first_name
    user.last_name = last_name
    user.role = role
    if team:
        user.team = team
    user.save()
    if created:
        print(f"Created user: {username} ({role})")
    else:
        print(f"Updated user: {username} ({role})")
    return user

def setup():
    # 1. Subadmin
    subadmin = create_user('Chanakya01', 'Aniket@2004', 'Aniket', 'mali', 'admin')

    # Manager
    manager = create_user('dev_manager', 'sagar@123', 'Sagar', 'Manager', 'manager')

    # 2. Teams and their Leaders/Employees
    teams_data = [
        {
            'name': 'NextGen Team',
            'leader': {'username': 'NextGen_ld', 'password': 'Kuldeep@2003', 'first_name': 'Kuldeep', 'last_name': 'Mahajan'},
            'employees': [
                {'username': 'NextGen-01', 'password': 'Shruti@123', 'first_name': 'Shruti', 'last_name': 'Bhadane'},
                {'username': 'NextGen-02', 'password': 'Akshuu@03', 'first_name': 'Akansha', 'last_name': 'Dhake'},
                {'username': 'NextGen-03', 'password': 'Chetan@123', 'first_name': 'Chetan', 'last_name': 'throat'},
            ]
        },
        {
            'name': 'Think Thank Team',
            'leader': {'username': 'Think_Thank_ld', 'password': 'Yogi@123', 'first_name': 'Yogesh', 'last_name': 'Chitrakathi'},
            'employees': [
                {'username': 'Think_thank-01', 'password': 'Anshu@Lv39', 'first_name': 'vaishanvi', 'last_name': 'Mahajan'},
                {'username': 'Think_thank-02', 'password': 'Payal@1443', 'first_name': 'Payal', 'last_name': 'Bhangale'},
                {'username': 'Think_thank-03', 'password': 'Jayesh@2003', 'first_name': 'Jayesh', 'last_name': 'Joshi'},
            ]
        },
        {
            'name': 'Dev Team',
            'leader': {'username': 'Dev_ld', 'password': 'Khushal@123', 'first_name': 'Khushal', 'last_name': 'Mali'},
            'employees': [
                {'username': 'Dev-01', 'password': 'Goutham@121', 'first_name': 'Rohini', 'last_name': 'Gunukonda'},
                {'username': 'Dev-02', 'password': 'Neha@20', 'first_name': 'Neha', 'last_name': 'Ingale'},
                {'username': 'Dev-03', 'password': 'Durgesh07', 'first_name': 'Durgesh', 'last_name': 'Suryavanshi'},
            ]
        }
    ]

    for t_data in teams_data:
        # Create team
        team, created = Team.objects.get_or_create(name=t_data['name'])
        if created:
            print(f"Created team: {team.name}")
        
        # Create/Update leader
        l_data = t_data['leader']
        leader = create_user(l_data['username'], l_data['password'], l_data['first_name'], l_data['last_name'], 'team_leader', team)
        
        # Link leader to team
        team.leader = leader
        team.save()

        # Create/Update employees
        for e_data in t_data['employees']:
            if isinstance(e_data, dict):
                create_user(e_data['username'], e_data['password'], e_data['first_name'], e_data['last_name'], 'employee', team)

if __name__ == "__main__":
    setup()
