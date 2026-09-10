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


# =========================================================
# SEND CODE
# =========================================================

@app.post("/auth/send-code")
async def send_code(request: Request):

    try:
        data = await request.json()
        phone = str(data.get("phone", "")).strip()

        if not phone:
            return {
                "status": "error",
                "message": "شماره موبایل وارد نشده است"
            }

        old_auth = pending_auth.get(phone)

        if old_auth:
            try:
                await old_auth["client"].__aexit__(
                    None, None, None
                )
            except Exception:
                pass

            pending_auth.pop(phone, None)

        old_client = active_clients.get(phone)

        if old_client:
            try:
                await old_client.__aexit__(
                    None, None, None
                )
            except Exception:
                pass

            active_clients.pop(phone, None)

        client = await EitaaClient.create(
            require_auth=False
        )

        await client.__aenter__()

        challenge = await client.auth.request_code(
            phone,
            settings=OtpCodeSettings()
        )

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


# =========================================================
# LOGIN
# =========================================================

@app.post("/auth/login")
async def login(request: Request):

    try:
        data = await request.json()

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

        auth_data = pending_auth.get(phone)

        if not auth_data:
            return {
                "status": "error",
                "message": "درخواست کد پیدا نشد"
            }

        client = auth_data["client"]
        challenge = auth_data["challenge"]

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


# =========================================================
# RESEND CODE
# =========================================================

@app.post("/auth/resend-code")
async def resend_code(request: Request):

    try:
        data = await request.json()
        phone = str(data.get("phone", "")).strip()

        auth_data = pending_auth.get(phone)

        if not auth_data:
            return {
                "status": "error",
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
# CHATS
# =========================================================

@app.post("/chats")
async def chats(request: Request):

    try:

        data = await request.json()

        phone = str(
            data.get("phone", "")
        ).strip()

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
                "message": "حساب وارد نشده است"
            }

        # دریافت گفتگوها
        result = await client.dialogs.list(
            limit=100
        )

        return {
            "status": "ok",
            "where": "chats",
            "message": "لیست گفتگوها دریافت شد",
            "data": result
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

        phone = str(
            data.get("phone", "")
        ).strip()

        client = active_clients.get(phone)

        if not client:
            return {
                "status": "error",
                "message": "حساب وارد نشده است"
            }

        result = await client.dialogs.groups(
            limit=100
        )

        return {
            "status": "ok",
            "message": "لیست گروه‌ها دریافت شد",
            "data": result
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

        phone = str(
            data.get("phone", "")
        ).strip()

        client = active_clients.get(phone)

        if not client:
            return {
                "status": "error",
                "message": "حساب وارد نشده است"
            }

        result = await client.dialogs.channels(
            limit=100
        )

        return {
            "status": "ok",
            "message": "لیست کانال‌ها دریافت شد",
            "data": result
        }

    except Exception as e:

        return {
            "status": "error",
            "where": "channels",
            "error_type": type(e).__name__,
            "message": str(e)
        }
