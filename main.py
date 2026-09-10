from fastapi import FastAPI, Request
from eitaa_cli import EitaaClient
from eitaa_cli.models import OtpCodeSettings

app = FastAPI()

pending_auth = {}
active_clients = {}


@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Eitaa Manager Backend is running"
    }


@app.get("/status")
async def status():
    return {
        "status": "ok",
        "pending_auth": list(pending_auth.keys()),
        "active_clients": list(active_clients.keys())
    }


@app.post("/auth/send-code")
async def send_code(request: Request):
    try:
        data = await request.json()

        phone = str(data.get("phone", "")).strip()

        if not phone:
            return {
                "status": "error",
                "where": "send-code",
                "message": "شماره موبایل وارد نشده است"
            }

        # بستن احراز هویت قبلی
        old_auth = pending_auth.get(phone)

        if old_auth:
            try:
                await old_auth["client"].__aexit__(None, None, None)
            except Exception:
                pass

            pending_auth.pop(phone, None)

        # بستن کلاینت فعال قبلی
        old_client = active_clients.get(phone)

        if old_client:
            try:
                await old_client.__aexit__(None, None, None)
            except Exception:
                pass

            active_clients.pop(phone, None)

        # ساخت کلاینت جدید
        client = await EitaaClient.create(
            require_auth=False
        )

        await client.__aenter__()

        # درخواست کد
        challenge = await client.auth.request_code(
            phone,
            settings=OtpCodeSettings()
        )

        # نگهداری کلاینت و challenge
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
            "where": "send-code",
            "error_type": type(e).__name__,
            "message": str(e)
        }


@app.post("/auth/login")
async def login(request: Request):
    try:
        data = await request.json()

        phone = str(data.get("phone", "")).strip()
        code = str(data.get("code", "")).strip()

        if not phone:
            return {
                "status": "error",
                "where": "login",
                "message": "شماره موبایل وارد نشده است"
            }

        if not code:
            return {
                "status": "error",
                "where": "login",
                "message": "کد تأیید وارد نشده است"
            }

        auth_data = pending_auth.get(phone)

        if not auth_data:
            return {
                "status": "error",
                "where": "login",
                "message": "درخواست کد پیدا نشد"
            }

        client = auth_data["client"]
        challenge = auth_data["challenge"]

        # ورود با همان client و همان challenge
        await client.auth.sign_in(
            challenge.phone_number,
            challenge.phone_code_hash,
            code
        )

        active_clients[phone] = client

        pending_auth.pop(phone, None)

        return {
            "status": "ok",
            "message": "ورود به ایتا موفق بود"
        }

    except Exception as e:
        return {
            "status": "error",
            "where": "login",
            "error_type": type(e).__name__,
            "message": str(e)
        }


@app.post("/auth/resend-code")
async def resend_code(request: Request):
    try:
        data = await request.json()

        phone = str(data.get("phone", "")).strip()

        if not phone:
            return {
                "status": "error",
                "where": "resend-code",
                "message": "شماره موبایل وارد نشده است"
            }

        auth_data = pending_auth.get(phone)

        if not auth_data:
            return {
                "status": "error",
                "where": "resend-code",
                "message": "درخواست قبلی پیدا نشد"
            }

        client = auth_data["client"]
        challenge = auth_data["challenge"]

        new_challenge = await client.auth.resend_code(
            challenge.phone_number,
            challenge.phone_code_hash
        )

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
            "where": "resend-code",
            "error_type": type(e).__name__,
            "message": str(e)
        }


# =========================================================
# TEST CHATS
# =========================================================

@app.post("/chats")
async def chats(request: Request):
    try:
        data = await request.json()

        phone = str(data.get("phone", "")).strip()

        if not phone:
            return {
                "status": "error",
                "where": "chats",
                "message": "شماره موبایل وارد نشده است"
            }

        client = active_clients.get(phone)

        if not client:
            return {
                "status": "error",
                "where": "chats",
                "message": "حساب وارد نشده است",
                "phone": phone
            }

        # ---------------------------------------------
        # مرحله 1: اجرای واقعی dialogs.list
        # ---------------------------------------------

        result = await client.dialogs.list(
            limit=100
        )

        # ---------------------------------------------
        # فعلاً result را برنمی‌گردانیم
        # چون ممکن است آبجکت خام قابل JSON نباشد.
        # ---------------------------------------------

        return {
            "status": "ok",
            "where": "chats",
            "message": "dialogs.list با موفقیت اجرا شد",
            "result_type": type(result).__name__
        }

    except Exception as e:
        return {
            "status": "error",
            "where": "chats",
            "error_type": type(e).__name__,
            "message": str(e)
        }


# =========================================================
# GROUPS
# =========================================================

@app.post("/chats/groups")
async def groups(request: Request):
    try:
        data = await request.json()

        phone = str(data.get("phone", "")).strip()

        if not phone:
            return {
                "status": "error",
                "where": "groups",
                "message": "شماره موبایل وارد نشده است"
            }

        client = active_clients.get(phone)

        if not client:
            return {
                "status": "error",
                "where": "groups",
                "message": "حساب وارد نشده است"
            }

        result = await client.dialogs.groups(
            limit=100
        )

        return {
            "status": "ok",
            "where": "groups",
            "message": "groups با موفقیت اجرا شد",
            "result_type": type(result).__name__
        }

    except Exception as e:
        return {
            "status": "error",
            "where": "groups",
            "error_type": type(e).__name__,
            "message": str(e)
        }


# =========================================================
# CHANNELS
# =========================================================

@app.post("/chats/channels")
async def channels(request: Request):
    try:
        data = await request.json()

        phone = str(data.get("phone", "")).strip()

        if not phone:
            return {
                "status": "error",
                "where": "channels",
                "message": "شماره موبایل وارد نشده است"
            }

        client = active_clients.get(phone)

        if not client:
            return {
                "status": "error",
                "where": "channels",
                "message": "حساب وارد نشده است"
            }

        result = await client.dialogs.channels(
            limit=100
        )

        return {
            "status": "ok",
            "where": "channels",
            "message": "channels با موفقیت اجرا شد",
            "result_type": type(result).__name__
        }

    except Exception as e:
        return {
            "status": "error",
            "where": "channels",
            "error_type": type(e).__name__,
            "message": str(e)
            }
