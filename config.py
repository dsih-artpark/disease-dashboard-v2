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
    # admin region indexes used for different subregion types
    subregion_indexes = dict(
        state = 1, # district
        district = 2, # subdistrict/ulb
        subdistrict = 4, # village
        ulb = 3, # zone
        zone = 4, # ward
    )

    # will be displayed on the dashboard UI
    dashboard_title = DEFAULT_DASHBOARD_TITLE

    # Earliest date for which data is available
    data_start_date = datetime(2000, 1, 1)

    # list of domains that needs to be connected to this tenant
    domains = []

    # disease stages to be shown for this tenant
    stages = ["suspected", "tested", "confirmed", "deaths"]

    # definitions of each stage
    stage_definitions = dict(
        suspected = "",
        tested = "",
        confirmed = "",
        deaths = "",
    )

    # topmost region for this tenant
    # this region and all regions under it will
    #     be accessible to this tenant
    scope_region = None

    # the region types which can have subregions
    # typically, this everything except village and ward
    splittable_region_types = []

    # a unqiue tenant ID for this tenant
    # difficult to change once dashboard is operational
    tenant_id = ""
