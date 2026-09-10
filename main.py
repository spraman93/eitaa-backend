from fastapi import FastAPI, Request
from eitaa_cli import EitaaClient
from eitaa_cli.models import OtpCodeSettings

app = FastAPI()

# موقت برای نگه‌داشتن درخواست OTP
pending_auth = {}


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "eitaa-manager"
    }


# =========================================================
# STATUS
# =========================================================

@app.get("/status")
async def status():
    return {
        "status": "ok",
        "message": "Backend is running"
    }


# =========================================================
# SEND CODE
# =========================================================

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

    # اگر درخواست قبلی برای همین شماره وجود داشت
    old = pending_auth.pop(phone, None)

    if old:
        try:
            await old["client"].close()
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


# =========================================================
# LOGIN
# =========================================================

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
            "message": "درخواست کد پیدا نشد؛ دوباره دریافت کد را بزنید"
        }

    client = auth_data["client"]
    challenge = auth_data["challenge"]

    try:

        # ورود با همان Client و همان Challenge
        await client.auth.sign_in(
            challenge.phone_number,
            challenge.phone_code_hash,
            code
        )

        # sign_in به صورت پیش‌فرض session را ذخیره می‌کند
        # پس بعداً می‌توانیم Client را دوباره بسازیم.

        pending_auth.pop(phone, None)

        return {
            "status": "ok",
            "message": "ورود به ایتا موفق بود"
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# =========================================================
# RESEND CODE
# =========================================================

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
            "message": "درخواست کد پیدا نشد"
        }

    client = auth_data["client"]
    challenge = auth_data["challenge"]

    try:

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
            "message": str(e)
        }


# =========================================================
# GET ALL CHATS
# =========================================================

@app.post("/chats")
async def chats(request: Request):

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

    client = None

    try:

        # Client را از Session ذخیره‌شده می‌سازیم
        client = await EitaaClient.create(
            profile=phone,
            require_auth=True
        )

        await client.__aenter__()

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

    finally:

        if client:
            try:
                await client.close()
            except Exception:
                pass


# =========================================================
# GET GROUPS
# =========================================================

@app.post("/chats/groups")
async def groups(request: Request):

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

    client = None

    try:

        client = await EitaaClient.create(
            profile=phone,
            require_auth=True
        )

        await client.__aenter__()

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

    finally:

        if client:
            try:
                await client.close()
            except Exception:
                pass


# =========================================================
# GET CHANNELS
# =========================================================

@app.post("/chats/channels")
async def channels(request: Request):

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

    client = None

    try:

        client = await EitaaClient.create(
            profile=phone,
            require_auth=True
        )

        await client.__aenter__()

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

    finally:

        if client:
            try:
                await client.close()
            except Exception:
                pass
