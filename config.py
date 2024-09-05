from datetime import datetime
from dotenv import dotenv_values
from pymongo import aggregation

env = dotenv_values('.env')

DB_URI = env["DB_URI"]
DEFAULT_DASHBOARD_TITLE = env["DEFAULT_DASHBOARD_TITLE"]
ENV_TYPE = env["ENV_TYPE"].lower()
FLASK_SECRET_KEY = env["FLASK_SECRET_KEY"]
JWT_SECRET = env["JWT_SECRET"]
MIXPANEL_PROJECT_TOKEN = env["MIXPANEL_PROJECT_TOKEN"]

if ENV_TYPE=="dev":
    import os
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

class Tenant:
    subregion_indexes = dict(
        state = 1, # district
        district = 2, # subdistrict/ulb
        subdistrict = 4, # village
        ulb = 3, # zone
        zone = 4, # ward
    )
    dashboard_title = DEFAULT_DASHBOARD_TITLE
    data_start_date = datetime(2000, 1, 1)
    domains = []
    stages = ["suspected", "tested", "confirmed", "deaths"]
    stage_definitions = dict(
        suspected = "",
        tested = "",
        confirmed = "",
        deaths = "",
    )
    scope_region = None
    splittable_region_types = []
    tenant_id = ""
