import re
import json
import secrets
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, session, send_file
from flask_login import login_user, logout_user, login_required, current_user
from db import db
from models import User
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
    AuthenticatorAttachment,
    PublicKeyCredentialDescriptor,
)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes

RP_ID = "pois2000.duckdns.org"
RP_NAME = "KIS 자동매매"
ORIGIN = "https://pois2000.duckdns.org:6001"

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            return redirect(request.args.get("next") or "/")
        flash("아이디 또는 비밀번호가 올바르지 않습니다.")
    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email_local = request.form.get("email_local", "").strip()
        email_domain = request.form.get("email_domain", "").strip()
        birth_y = request.form.get("birth_year", "")
        birth_m = request.form.get("birth_month", "")
        birth_d = request.form.get("birth_day", "")

        errors = []
        if not username or len(username) < 6 or len(username) > 20:
            errors.append("아이디는 6~20자로 입력해주세요.")
        if User.query.filter_by(username=username).first():
            errors.append("이미 사용 중인 아이디입니다.")
        if len(password) < 8 or len(password) > 20:
            errors.append("비밀번호는 8~20자로 입력해주세요.")
        if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password) or not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
            errors.append("비밀번호는 문자, 숫자, 특수문자를 포함해야 합니다.")
        if password != password2:
            errors.append("비밀번호가 일치하지 않습니다.")
        if not name:
            errors.append("이름을 입력해주세요.")
        if phone and (not phone.isdigit() or len(phone) != 11):
            errors.append("휴대폰 번호 11자리를 입력해주세요.")

        if errors:
            for e in errors:
                flash(e)
            return render_template("signup.html")

        email = f"{email_local}@{email_domain}" if email_local and email_domain else ""
        birth = f"{birth_y}-{birth_m.zfill(2)}-{birth_d.zfill(2)}" if birth_y and birth_m and birth_d else ""

        login_method = request.form.get("login_method", "password")

        user = User(username=username, name=name, phone=phone, email=email,
                     birth_date=birth, login_method=login_method)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        if login_method == "webauthn":
            # 지문 등록을 위해 로그인 후 등록 페이지로 이동
            login_user(user)
            return redirect("/register-fingerprint")

        flash("회원가입이 완료되었습니다. 로그인해주세요.")
        return redirect("/login")

    return render_template("signup.html")


@bp.route("/api/auth/check-username")
def check_username():
    username = request.args.get("username", "").strip()
    if len(username) < 6:
        return jsonify({"available": False, "msg": "6자 이상 입력해주세요."})
    exists = User.query.filter_by(username=username).first() is not None
    if exists:
        return jsonify({"available": False, "msg": "사용할 수 없는 아이디입니다."})
    return jsonify({"available": True, "msg": "사용 가능한 아이디입니다."})


@bp.route("/api/auth/token", methods=["POST"])
def api_token():
    """모바일 앱용 토큰 인증"""
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        token = secrets.token_urlsafe(32)
        user.remember_token = token
        db.session.commit()
        return jsonify({"success": True, "token": token, "name": user.name})
    return jsonify({"success": False, "msg": "아이디 또는 비밀번호가 올바르지 않습니다."}), 401


@bp.route("/api/auth/verify-token", methods=["POST"])
def verify_token():
    """모바일 앱 토큰 검증"""
    data = request.get_json()
    token = data.get("token", "")
    user = User.query.filter_by(remember_token=token).first()
    if user and token:
        return jsonify({"success": True, "username": user.username, "name": user.name})
    return jsonify({"success": False}), 401


@bp.route("/api/auth/mobile-login", methods=["POST"])
def mobile_login():
    """모바일 앱에서 토큰으로 세션 로그인 (WebView용)"""
    data = request.get_json()
    token = data.get("token", "")
    user = User.query.filter_by(remember_token=token).first()
    if user and token:
        login_user(user, remember=True)
        return jsonify({"success": True})
    return jsonify({"success": False}), 401


@bp.route("/download/kis-trader")
@login_required
def download_project():
    """프로젝트 zip 다운로드"""
    import os
    zip_path = os.path.expanduser("~/Desktop/kis-trader.zip")
    if os.path.exists(zip_path):
        return send_file(zip_path, as_attachment=True, download_name="kis-trader.zip")
    return "파일을 찾을 수 없습니다.", 404


@bp.route("/download/ppt")
@login_required
def download_ppt():
    """PPT 다운로드"""
    import os
    ppt_path = os.path.expanduser("~/Desktop/KIS_자동매매_시스템.pptx")
    if os.path.exists(ppt_path):
        return send_file(ppt_path, as_attachment=True, download_name="KIS_자동매매_시스템.pptx")
    return "파일을 찾을 수 없습니다.", 404


# ─── WebAuthn 지문인식 ───────────────────────────────────────

@bp.route("/register-fingerprint")
@login_required
def register_fingerprint_page():
    return render_template("register_fingerprint.html")


@bp.route("/api/webauthn/register/options", methods=["POST"])
@login_required
def webauthn_register_options():
    """지문 등록 옵션 생성"""
    user = current_user
    existing_creds = user.webauthn_credentials or []
    exclude = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["credential_id"]))
        for c in existing_creds
    ]
    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=str(user.id).encode(),
        user_name=user.username,
        user_display_name=user.name or user.username,
        exclude_credentials=exclude,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )
    session["webauthn_register_challenge"] = bytes_to_base64url(options.challenge)
    return options_to_json(options), 200, {"Content-Type": "application/json"}


@bp.route("/api/webauthn/register/verify", methods=["POST"])
@login_required
def webauthn_register_verify():
    """지문 등록 검증"""
    challenge = session.pop("webauthn_register_challenge", None)
    if not challenge:
        return jsonify({"success": False, "msg": "챌린지가 만료되었습니다."}), 400

    try:
        body = request.get_json()
        credential = verify_registration_response(
            credential=body,
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
        )
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 400

    user = current_user
    creds = list(user.webauthn_credentials or [])
    creds.append({
        "credential_id": bytes_to_base64url(credential.credential_id),
        "public_key": bytes_to_base64url(credential.credential_public_key),
        "sign_count": credential.sign_count,
    })
    user.webauthn_credentials = creds
    user.login_method = "webauthn"
    db.session.commit()
    return jsonify({"success": True, "msg": "지문이 등록되었습니다."})


@bp.route("/api/webauthn/login/options", methods=["POST"])
def webauthn_login_options():
    """지문 로그인 옵션 생성"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    user = User.query.filter_by(username=username).first()
    if not user or not user.webauthn_credentials:
        return jsonify({"success": False, "msg": "등록된 지문이 없습니다."}), 400

    allow = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(c["credential_id"]))
        for c in user.webauthn_credentials
    ]
    options = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=allow,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    session["webauthn_login_challenge"] = bytes_to_base64url(options.challenge)
    session["webauthn_login_user_id"] = user.id
    return options_to_json(options), 200, {"Content-Type": "application/json"}


@bp.route("/api/webauthn/login/verify", methods=["POST"])
def webauthn_login_verify():
    """지문 로그인 검증"""
    challenge = session.pop("webauthn_login_challenge", None)
    user_id = session.pop("webauthn_login_user_id", None)
    if not challenge or not user_id:
        return jsonify({"success": False, "msg": "챌린지가 만료되었습니다."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "msg": "사용자를 찾을 수 없습니다."}), 400

    # 매칭되는 credential 찾기
    body = request.get_json()
    raw_id = body.get("rawId", body.get("id", ""))
    matched = None
    for c in (user.webauthn_credentials or []):
        if c["credential_id"] == raw_id:
            matched = c
            break

    if not matched:
        return jsonify({"success": False, "msg": "등록된 지문과 일치하지 않습니다."}), 400

    try:
        result = verify_authentication_response(
            credential=body,
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            credential_public_key=base64url_to_bytes(matched["public_key"]),
            credential_current_sign_count=matched["sign_count"],
        )
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 400

    # sign_count 업데이트
    matched["sign_count"] = result.new_sign_count
    user.webauthn_credentials = list(user.webauthn_credentials)
    db.session.commit()

    login_user(user, remember=True)
    return jsonify({"success": True, "msg": "로그인 성공"})
