from fastapi import FastAPI, Request
from eitaa_cli import EitaaClient
from eitaa_cli.models import OtpCodeSettings

app = FastAPI()

# نگهداری موقت احراز هویت تا زمان ورود
pending_auth = {}

# نگهداری Clientهای واردشده
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


# ---------------------------------------------------------
# ارسال کد ورود
# ---------------------------------------------------------

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

        # اگر برای این شماره درخواست قبلی وجود دارد
        old_auth = pending_auth.get(phone)

        if old_auth:
            try:
                await old_auth["client"].__aexit__(None, None, None)
            except Exception:
                pass

            pending_auth.pop(phone, None)

        # اگر قبلاً Client فعال داشته‌ایم
        old_client = active_clients.get(phone)

        if old_client:
            try:
                await old_client.__aexit__(None, None, None)
            except Exception:
                pass

            active_clients.pop(phone, None)

        # ساخت Client جدید
        client = await EitaaClient.create(
            require_auth=False
        )

        # باز نگه داشتن اتصال
        await client.__aenter__()

        # درخواست کد تأیید
        challenge = await client.auth.request_code(
            phone,
            settings=OtpCodeSettings()
        )

        # ذخیره Client و Challenge
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


# ---------------------------------------------------------
# ورود با کد تأیید
# ---------------------------------------------------------

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

        # پیدا کردن درخواست قبلی
        auth_data = pending_auth.get(phone)

        if not auth_data:

            return {
                "status": "error",
                "message": "درخواست کد پیدا نشد. دوباره دریافت کد را بزنید."
            }

        client = auth_data["client"]
        challenge = auth_data["challenge"]

        # ورود به ایتا
        await client.auth.sign_in(
            challenge.phone_number,
            challenge.phone_code_hash,
            code
        )

        # اگر قبلاً Client فعال وجود دارد
        old_client = active_clients.get(phone)

        if old_client and old_client is not client:
            try:
                await old_client.__aexit__(None, None, None)
            except Exception:
                pass

        # ثبت Client واردشده
        active_clients[phone] = client

        # حذف اطلاعات موقت احراز هویت
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


# ---------------------------------------------------------
# درخواست مجدد کد
# ---------------------------------------------------------

@app.post("/auth/resend-code")
async def resend_code(request: Request):

    try:
        data = await request.json()

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
                "message": "درخواست قبلی برای این شماره پیدا نشد"
            }

        client = auth_data["client"]
        challenge = auth_data["challenge"]

        # درخواست کد مجدد
        new_challenge = await client.auth.resend_code(
            challenge.phone_number,
            challenge.phone_code_hash
        )

        # ذخیره Challenge جدید
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


# ---------------------------------------------------------
# دریافت تمام گفتگوها
# ---------------------------------------------------------

@app.post("/chats")
async def chats(request: Request):

    try:

        data = await request.json()

        phone = str(data.get("phone", "")).strip()

        if not phone:
            return {
                "status": "error",
                "message": "شماره موبایل وارد نشده است"
            }

        # خیلی مهم:
        # Client جدید نمی‌سازیم
        # همان Client زمان ورود را استفاده می‌کنیم
        client = active_clients.get(phone)

        if not client:

            return {
                "status": "error",
                "message": "این حساب وارد نشده است. ابتدا وارد ایتا شوید."
            }

        # دریافت گفتگوها
        result = await client.dialogs.list(
            limit=100
        )

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


# ---------------------------------------------------------
# دریافت گروه‌ها
# ---------------------------------------------------------

@app.post("/chats/groups")
async def groups(request: Request):

    try:

        data = await request.json()

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
                "message": "این حساب وارد نشده است. ابتدا وارد ایتا شوید."
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
            "message": str(e)
        }


# ---------------------------------------------------------
# دریافت کانال‌ها
# ---------------------------------------------------------

@app.post("/chats/channels")
async def channels(request: Request):

    try:

        data = await request.json()

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
                "message": "این حساب وارد نشده است. ابتدا وارد ایتا شوید."
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
            "message": str(e)
        }
