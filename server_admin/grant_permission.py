import sys

from models import User

user_id = sys.argv[1]
tenant_id = sys.argv[2]
permission = sys.argv[3].lower()

user = User.objects(user_id=user_id, tenant_id=tenant_id).first()
if permission not in user.permissions:
    user.permissions.append(permission)
    user.permissions.sort()
user.save()
print("Granted, new permission list is:", user.permissions)
