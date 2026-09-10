from fastapi import FastAPI, Request
from eitaa_cli import EitaaClient
from eitaa_cli.models import OtpCodeSettings

app = FastAPI()

# موقت برای تست
# کلید = شماره تلفن
# مقدار = Client و Challenge مربوط به همان درخواست
pending_auth = {}


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "eitaa-manager"
    }


@app.get("/status")
async def status():
    return {
        "status": "ok",
        "message": "Backend is running"
    }


# ==================================================
# درخواست کد ورود
# ==================================================

@app.post("/auth/send-code")
async def send_code(request: Request):

    try:
        data = await request.json()
    except Exception:
        return {
            "status": "error",
            "message": "JSON نامعتبر است"
        }

    phone = str(data.get("phone", "")).strip()

    if not phone:
        return {
            "status": "error",
            "message": "شماره موبایل وارد نشده است"
        }

    # اگر قبلاً برای این شماره Client داشتیم،
    # آن را می‌بندیم.
    old = pending_auth.pop(phone, None)

    if old:
        try:
            await old["client"].__aexit__(None, None, None)
        except Exception:
            pass

    try:

        # Client جدید
        client = await EitaaClient.create(
            require_auth=False
        )

        # Client را باز نگه می‌داریم
        await client.__aenter__()

        # درخواست کد
        challenge = await client.auth.request_code(
            phone,
            settings=OtpCodeSettings()
        )

        # همان Client + همان Challenge
        # برای مرحله login نگه داشته می‌شود
        pending_auth[phone] = {
            "client": client,
            "challenge": challenge
        }

        return {
            "status": "ok",
            "message": "کد تأیید ارسال شد",
            "delivery": str(challenge.delivery),
            "next_delivery": str(challenge.next_delivery),
            "timeout_seconds": challenge.timeout_seconds
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ==================================================
# ورود با کد تأیید
# ==================================================

@app.post("/auth/login")
async def login(request: Request):

    try:
        data = await request.json()
    except Exception:
        return {
            "status": "error",
            "message": "JSON نامعتبر است"
        }

    phone = str(data.get("phone", "")).strip()
    code = str(data.get("code", "")).strip()

    if not phone:
        return {
            "status": "error",
            "message": "شماره موبایل وارد نشده است"
        }

    if not code:
        return {
            "status": "error",
            "message": "کد تأیید وارد نشده است"
        }

    # Challenge همان درخواست قبلی
    auth_data = pending_auth.get(phone)

    if not auth_data:
        return {
            "status": "error",
            "message": "درخواست کد پیدا نشد؛ دوباره کد دریافت کنید"
        }

    client = auth_data["client"]
    challenge = auth_data["challenge"]

    try:

        # ورود با همان Client
        # و همان phone_code_hash
        authorization = await client.auth.sign_in(
            challenge.phone_number,
            challenge.phone_code_hash,
            code
        )

        # ورود موفق
        pending_auth.pop(phone, None)

        # توکن را در پاسخ برنمی‌گردانیم
        return {
            "status": "ok",
            "message": "ورود به ایتا موفق بود"
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ==================================================
# درخواست کد مجدد
# ==================================================

@app.post("/auth/resend-code")
async def resend_code(request: Request):

    try:
        data = await request.json()
    except Exception:
        return {
            "status": "error",
            "message": "JSON نامعتبر است"
        }

    phone = str(data.get("phone", "")).strip()

    if not phone:
        return {
            "status": "error",
            "message": "شماره موبایل وارد نشده است"
        }

    auth_data = pending_auth.get(phone)

    if not auth_data:
        return {
            "status": "error",
            "message": "درخواست کد پیدا نشد؛ دوباره دریافت کد را بزنید"
        }

    client = auth_data["client"]
    challenge = auth_data["challenge"]

    try:

        # درخواست روش بعدی که خود ایتا اعلام کرده
        new_challenge = await client.auth.resend_code(
            challenge.phone_number,
            challenge.phone_code_hash
        )

        # Challenge جدید را جایگزین می‌کنیم
        pending_auth[phone] = {
            "client": client,
            "challenge": new_challenge
        }

        return {
            "status": "ok",
            "message": "کد مجدد درخواست شد",
            "delivery": str(new_challenge.delivery),
            "next_delivery": str(new_challenge.next_delivery),
            "timeout_seconds": new_challenge.timeout_seconds
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }
