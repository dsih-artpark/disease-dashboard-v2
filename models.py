from datetime import datetime, timedelta
from os import truncate

import config
import jwt
from mongoengine import *

connect(host=config.DB_URI)

class CaseEntry(Document):
    record_id = StringField(unique=True, required=True)
    record_date = DateTimeField(required=True)

    source = StringField(required=True)
    source_filename = StringField(required=True)

    hierarchy = StringField(required=True)
    regions = ListField(StringField(), required=True)

    suspected = IntField(default=0)
    tested = IntField(default=0)
    confirmed = IntField(default=0)
    deaths = IntField(default=0)

    age_range = StringField(required=True)
    gender = StringField(required=True)
    test_type = StringField(required=True)

    meta = {
        "collection": "cases",
        "indexes": [
            ("regions", "record_date"),
            "source_filename"
        ]
    }

class Prediction(Document):
    region_id = StringField(required=True)
    parent_id = StringField(required=True)
    date = DateTimeField(required=True)

    computation_date = DateTimeField(required=True)
    source_filename = StringField(required=True)

    prediction = FloatField(default=-2)
    prediction_zone = IntField(default=-2)
    threshold_method = StringField()

    meta = {
        "collection": "predictions",
        "indexes": [
            {"fields": ["region_id", "date"], "unique": True},
            ("parent_id", "date"),
        ]
    }

class Region(Document):
    region_id = StringField(unique=True, required=True)
    region_type = StringField(required=True)
    name = StringField(required=True)
    parent_ids = ListField(StringField())
    parent_names = ListField(StringField())

    meta = {
        "collection": "regions",
        "indexes": ["parent_ids.0"]
    }

    def in_scope(self, region_id):
        return self.region_id==region_id or region_id in self.parent_ids

class SourceFile(Document):
    name = StringField(unique=True)
    data_type = StringField(required=True)
    import_date = DateTimeField(required=True, default=datetime.utcnow())
    import_errors = ListField(default=[])

    meta = {"collection": "source_files"}

class User(Document):
    user_id = StringField(required=True)
    tenant_id = StringField(required=True)

    name = StringField(required=True)
    home_region = StringField(required=True)

    permissions = ListField(StringField(), default=[])

    meta = {
        "collection": "users",
        "indexes": [{"fields": ["tenant_id", "user_id"], "unique": True}]
    }

    def generate_jwt(self):
        return jwt.encode({
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "exp": datetime.utcnow() + timedelta(days=7),
        }, config.JWT_SECRET, algorithm="HS256")

    @staticmethod
    def get_by_jwt(access_token, tenant_id):
        try:
            payload = jwt.decode(access_token, config.JWT_SECRET, algorithms=["HS256"])
            if payload["tenant_id"]==tenant_id:
                return User.objects(
                    user_id = payload["user_id"],
                    tenant_id = payload["tenant_id"],
                ).first()
            else:
                return None
        except:
            return User.objects(
                user_id = "__unauthenticated__",
                tenant_id = tenant_id,
            ).first()
