from flask import Blueprint, abort, request

from models import User

bp = Blueprint("users", __name__)

@bp.route("/list")
def list_users():
    if not request.user:
        abort(401)
        return
    if "user_management" not in request.user.permissions:
        abort(401)
        return

    query = User.objects(tenant_id = request.tenant.tenant_id)
    result = []
    for obj in query:
        result.append(dict(
            user_id = obj.user_id,
            name = obj.name,
            home_region = obj.home_region,
            permissions = obj.permissions,
        ))
    return {"users": result}

@bp.route("/add_user", methods=["POST"])
def add_user():
    if not request.user:
        abort(401)
        return
    if "user_management" not in request.user.permissions:
        abort(401)
        return

    data = request.json
    user_exists = User.objects(
        user_id = data["user_id"],
        tenant_id = request.tenant.tenant_id,
    ).first()
    if user_exists:
        return {"message": "User Already Exists"}
    else:
        user = User(
            user_id = data["user_id"],
            tenant_id = request.tenant.tenant_id,
            name = data["name"],
            home_region = data["home_region"],
        )
        user.save()
        return {"message": "User Added Successfully"}

@bp.route("/delete_user", methods=["POST"])
def delete_user():
    if not request.user:
        abort(401)
        return
    if "user_management" not in request.user.permissions:
        abort(401)
        return

    user = User.objects(
        user_id = request.json["user_id"],
        tenant_id = request.tenant.tenant_id,
    ).first()
    if not user:
        return {"message": "User Does Not Exist"}

    if user.user_id==request.user.user_id:
        return {"message": "You Cannot Delete Yourself"}
    if "user_management" in user.permissions:
        return {"message": "Cannot Delete User Admin"}

    user.delete()
    return {"message": "User Deleted"}
