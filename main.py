from fastapi import FastAPI, Request
from eitaa_cli import EitaaClient
from eitaa_cli.models import OtpCodeSettings

app = FastAPI()

# موقت برای تست
pending_auth = {}

# بعد از ورود موفق، کلاینت‌های واردشده را نگه می‌داریم
active_clients = {}


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


# ==========================================
# دریافت کد
# ==========================================

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

    old = pending_auth.pop(phone, None)

    if old:
        try:
            await old["client"].__aexit__(None, None, None)
        except Exception:
            pass

    try:

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
            "message": str(e)
        }


# ==========================================
# ورود
# ==========================================

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

    auth_data = pending_auth.get(phone)

    if not auth_data:
        return {
            "status": "error",
            "message": "درخواست کد پیدا نشد"
        }

    client = auth_data["client"]
    challenge = auth_data["challenge"]

    try:

        await client.auth.sign_in(
            challenge.phone_number,
            challenge.phone_code_hash,
            code
        )

        # ورود موفق
        pending_auth.pop(phone, None)

        # کلاینت واردشده را نگه می‌داریم
        active_clients[phone] = client

        return {
            "status": "ok",
            "message": "ورود به ایتا موفق بود"
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ==========================================
# دریافت همه گفتگوها
# ==========================================

@app.post("/chats")
async def chats(request: Request):

    try:
        data = await request.json()
    except Exception:
        data = {}

    phone = str(data.get("phone", "")).strip()

    if not phone:
        return {
            "status": "error",
            "message": "شماره موبایل وارد نشده است"
        }

    client = active_clients.get(phone)

    if not client:
        return {
            "status": "error",
            "message": "کاربر وارد نشده است"
        }

    try:

        result = await client.dialogs.list(100)

        return {
            "status": "ok",
            "message": "لیست گفتگوها دریافت شد",
            "data": result
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ==========================================
# فقط گروه‌ها
# ==========================================

@app.post("/chats/groups")
async def groups(request: Request):

    try:
        data = await request.json()
    except Exception:
        data = {}

    phone = str(data.get("phone", "")).strip()

    client = active_clients.get(phone)

    if not client:
        return {
            "status": "error",
            "message": "کاربر وارد نشده است"
        }

    try:

        result = await client.dialogs.groups(100)

        return {
            "status": "ok",
            "message": "گروه‌ها دریافت شدند",
            "data": result
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ==========================================
# فقط کانال‌ها
# ==========================================

@app.post("/chats/channels")
async def channels(request: Request):

    try:
        data = await request.json()
    except Exception:
        data = {}

    phone = str(data.get("phone", "")).strip()

    client = active_clients.get(phone)

    if not client:
        return {
            "status": "error",
            "message": "کاربر وارد نشده است"
        }

    try:

        result = await client.dialogs.channels(100)

        return {
            "status": "ok",
            "message": "کانال‌ها دریافت شدند",
            "data": result
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }
