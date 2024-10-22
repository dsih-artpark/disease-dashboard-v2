# Disease Dashboard

## Documentation (WIP)

### 1. Architecture Notes
Key points about the architecture and tooling:
- This codebase supports multi-tenancy. This means multiple organizations can have multiple dashboards running under multiple domain names using the same application instance and database.
- Uses [Flask](https://flask.palletsprojects.com/en/3.0.x/) (Python) as the backend server.
- Uses [MongoDB](https://www.mongodb.com/) for data persistence, and [mongoengine](http://mongoengine.org/) as the ORM 
- The frontend tooling uses [Jinja](https://palletsprojects.com/projects/jinja/) for HTML templating, good old CSS for styling and vanilla JS + d3.js for rendering visualizations.
- The tested and recommended deployment stack is [gunicorn](https://gunicorn.org/) + [NGINX](https://nginx.org/en/)
- Google OAuth is used for authentication of users. As of now all users need to have a Google managed email (personal / business) to be authenticated and use this dashboard.
- [Mixpanel](https://mixpanel.com/home/) is used for product analytics.

### 2. Setting Up
#### 2.1. Fill in the .env file
Create a .env to contain the application secrets. This file is mentioned under `.gitignore` and should not be commited to git. A sample `.env` with the required variables is shown below:

```
DB_URI=mongodb://username:password@example.com:27017
DEFAULT_DASHBOARD_TITLE=Shown on dashboard header, can be customized per tenant
ENV_TYPE=dev/staging/prod
FLASK_SECRET_KEY=a long string used by flask for security features
JWT_SECRET=a long string used to manage auth tokens
MIXPANEL_PROJECT_TOKEN=get from mixpanel dashboard
```

#### 2.2. Add Google OAuth Credentials
- Create a new OAuth app on Google Developer Console and download the credentials to allow for authentication using Google.
- Place the downloaded credentials at `./google-oauth-creds.json`. Add all the domains and corresponding redirect URIs that will be used for the dashboard, including `localhost` for testing purposes.
- The redirect URI for a given domain, say `example.com` will be `https://example.com/google-login-redirect`. `http` may be used instead of `https` only for localhost, and only if `ENV_TYPE` is set to `dev`.

#### 2.3. Configure Tenants
A tenant class is provided under `config.py` to use as the super class to define tenants. All subclasses of `config.Tenant` which are placed inside the `tenants/` directory will be used as Tenants.

#### 2.4. Import Regions
The dashboard works on the basis of hierarchical regions - which could be states, districts, villages, muncipalities, wards, etc. The dashboard can import regions from a CSV file with the following headers:
- `regionID`: A unique identifier for the region, of the format '<region_type>_<string_id>', e.g.: state_29, country_IN.
- `regionName`: The name to displayed to dashboard users.
- `parentID`: The regionID of the region which this region falls under.

The csv containing the data can be imported using the following command:
```
python -m server_admin.import_regions <path_to_csv>
```

Once the regions are imported, the auto-complete objects cache needs to be generated. This cache is used on the front-end to provide the search box. It can be done using the following command:
```
python -m server_admin.generate_autocomplete_objs 
```

#### 2.5. Adding Map Files
GeoJSON Map files for each individual region can be placed in the `source_files/geojsons/individual/` directory, with the naming convention `<region_id>.geojson`. So, the map file for `state_29` will be `source_files/geojsons/individual/state_29.geojson`. 

To ensure the dashboard loads quickly, the map files need to compressed by removing points. The map compressions works by removing closely located points on the boundary, thereby reducing precision yet maintaining a decent visual representation. The compressed maps may be used only for representational purposes and not for boundary based calculations such as determining which region a given point falls under. After the maps are compressed, the subregion-wise GeoJSON maps can be built. These two steps can be done as follows:
```
./server_admin/compress_maps.sh
python -m server_admin.generate_subregion_maps
```

#### 2.6. Adding/Managing Users
A user record on the database consists of the following fields:
- `user_id`: The email id using which the user logs in. Must be unique in conjunction with `tenant_id`.
- `tenant_id`: The dashboard tenant id corresponding to this user record.
- `name`: Name of the user (for displaying on front-ends)
- `home_region`: The first region that opens up when the user visits the dashboard
- `permmissions`: A list of strings containing special permissions granted to this user.

To add an user, the following command may be used:
```
python -m server_admin.add_user <user_id> <tenant_id> <user_name> <home_region>
# e.g.:
python -m server_admin.add_user mj@gmail.com ka 'Manjunath M' state_29
```

Granting Permissions:
```
python3 -m server_admin.grant_permission userid@email.com tenant_id permission_name
# e.g.:
python3 -m server_admin.grant_permission dmo@gmail.com ka predictions
python3 -m server_admin.grant_permission dmo@gmail.com ka user_management
python3 -m server_admin.grant_permission dmo@gmail.com ka report_download
```

Revoking Permissions:
```
python3 -m server_admin.revoke_permission userid@email.com tenant_id permission_name
# e.g.:
python3 -m server_admin.revoke_permission dmo@gmail.com ka predictions
python3 -m server_admin.revoke_permission dmo@gmail.com ka user_management
python3 -m server_admin.revoke_permission dmo@gmail.com ka report_download
```

> NOTE: Users with the `user_management` permission can add/remove users from the dashboard UI by visiting `example.dashboard.com/admin`.

#### 2.7. Managing Data
The dashboard displays three types of data:
1. Cases: Will be read as CSV files from `/source_files/case_data`.
2. Predictions: Will be read as CSV files from `/source_files/predictions`.
3. Serotypes: Will be read as CSV files from `/source_files/serotype`.

Once data is added/updated in these directories, the `sync_sources` script needs to be run:
```
python -m server_admin.sync_sources
```

The sync process works as follows:
- Files that were unchanged since last sync: Database rows from these files are left as is.
- Files that were modified since last sync: Existing database rows from these files are all dropped, and the whole file is reimported.
- Files deleted since last sync: Rows from these files are dropped from the database.
- Files added since last sync: All rows from these files are imported into the database.

> NOTE: The sync_sources script can be run as a cron job, in conjunction with syncing the source directories with an external data storage (S3) or a data warehouse.

#### 2.8. Running and Deploying
Once the above setup is done, the server can be started for testing/development purposes as follows:
```
python flask_app.py
```

Once the server starts, the dashboard can be viewed by visiting `http://localhost:2816/` in the browser. 
The in-built flask server is only convenient for testing and not recommended for production. For production deployment, a robust server such `gunicorn` can be used with a reverse proxy (e.g. `NGINX`). The following command may be used to start the server with `gunicorn`:
```
gunicorn -w 2 --bind unix:app.sock -m 007 flask_app:app
```
