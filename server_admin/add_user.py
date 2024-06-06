import sys

from models import User

user = User()
user.user_id = sys.argv[1]
user.tenant_id = sys.argv[2].lower()
user.name = sys.argv[3]
user.home_region = sys.argv[4].lower()
user.save()
