from datetime import datetime, timedelta

from flask import abort, Flask, make_response, redirect, render_template, request, send_file, session
from flask_wtf.csrf import CSRFProtect
from googleapiclient.discovery import build as google_build
import google_auth_oauthlib.flow

from api.data import bp as data_api_blueprint
import config
from models import CaseEntry, Region, User
import region_search
from tenants import get_tenant_for_domain

app = Flask(__name__, template_folder="templates")
app.secret_key = config.FLASK_SECRET_KEY
app.register_blueprint(data_api_blueprint, url_prefix="/api/data")
CSRFProtect(app)

region_search.init()

@app.before_request
def request_preprocessor():
    domain = request.headers["host"]
    request.tenant = get_tenant_for_domain(domain)
    if not request.tenant:
        return f'DOMAIN {domain} NOT CONFIGURED'

    request.user = User.get_by_jwt(
        request.cookies.get("auth"),
        request.tenant.tenant_id,
    )

    if not any([
        request.user,
        request.path.startswith("/login"),
        request.path.startswith("/static"),
        "google" in request.path,
    ]):
        return redirect("/login")

@app.route("/")
def index():
    return redirect("/region/" + request.tenant.scope_region)

@app.route("/region/<region_id>")
def dashboard_page(region_id):
    region = Region.objects(region_id=region_id).first()

    last_case_entry = CaseEntry.objects(regions=region_id).order_by("-record_date").first()
    last_recorded_case_date = last_case_entry.record_date.isoformat().split("T")[0]
    if not region:
        abort(404)
    else:
        return render_template(
            "index.html",
            tenant = request.tenant,
            latest_date = last_recorded_case_date,
        )

@app.route("/maps/subregions/<region_id>")
def subregion_map(region_id):
    region_id = region_id.replace("/", "")
    region = Region.objects(region_id=region_id).first()
    if not region:
        abort(404)
        return

    if region.in_scope(request.tenant.scope_region):
        return send_file("/".join(["source_files", "geojsons", "subregions", region_id]) + ".geojson")
    else:
        abort(401)

@app.route("/download_report/<filename>")
def download_report(filename):
    filepath = "source_files/reports/" + request.tenant.tenant_id + "/" + filename
    return send_file("/".join([
        "source_files/reports",
        request.tenant.tenant_id,
        filename
    ]))


@app.route("/region_search")
def region_search_fn():
    q = request.args.get("q")
    if not q:
        return {"results": []}
    return region_search.search(request.tenant.tenant_id, q)


@app.route("/login")
def login():
    return render_template("login.html", tenant=request.tenant)

@app.route("/logout")
def logout():
    resp = make_response(redirect("/"))
    resp.set_cookie(
        "auth",
        value="",
        httponly=True,
        expires=datetime.utcnow() + timedelta(days=7),
    )
    return resp

@app.route("/start-google-auth")
def start_google_auth():
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        "google-oauth-creds.json",
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
    )
    host_url = request.host_url
    flow.redirect_uri = host_url + "google-login-redirect"
    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scoped="true"
    )
    session["state"] = state
    session["page"] = request.args.get("page", "/")
    return redirect(authorization_url)

@app.route("/google-login-redirect")
def google_login_redirect():
    state = request.args.get("state", "")
    if state != session["state"]:
        abort(401)

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        "google-oauth-creds.json",
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
    )

    host_url = request.host_url
    flow.redirect_uri = host_url + "google-login-redirect"
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials

    user_info_service = google_build("oauth2", "v2", credentials=credentials)
    user_info = user_info_service.userinfo().get().execute()
    email = user_info["email"]

    user = User.objects(user_id=email, tenant_id=request.tenant.tenant_id).first()
    if not user:
        abort(401, "User Not Found in Database")
        return

    resp = make_response(redirect("/"))
    resp.set_cookie(
        "auth",
        value=user.generate_jwt(),
        httponly=True,
        expires=datetime.utcnow() + timedelta(days=7),
    )
    return resp


if __name__=="__main__":
    app.run(host="0.0.0.0", port="2816", debug=True, use_reloader=True)
