from datetime import datetime, timedelta

from flask import abort, Flask, make_response, redirect, render_template, request, session
from flask_wtf.csrf import CSRFProtect
from googleapiclient.discovery import build as google_build
import google_auth_oauthlib.flow

from api.data import bp as data_api_blueprint
import config
from models import User
from tenants import get_tenant_for_domain

app = Flask(__name__, template_folder="templates")
app.secret_key = config.FLASK_SECRET_KEY
app.register_blueprint(data_api_blueprint, url_prefix="/api/data")
CSRFProtect(app)

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
    return render_template("index.html", tenant=request.tenant)

@app.route("/login")
def login():
    return render_template("login.html", tenant=request.tenant)

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
