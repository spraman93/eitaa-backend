from fastapi import FastAPI, Request
from eitaa_cli import EitaaClient
from eitaa_cli.models import OtpCodeSettings

app = FastAPI()

# موقت برای تست
# بعداً این بخش را با ذخیره‌سازی دائمی و امن جایگزین می‌کنیم.
pending_auth = {}


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "eitaa-manager"
    }


@app.get("/status")
def status():
    return {
        "status": "ok",
        "message": "Backend is running"
    }


# --------------------------------
# درخواست کد ورود
# --------------------------------

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

    try:

        client = await EitaaClient.create(
            require_auth=False
        )

        async with client:

            challenge = await client.auth.request_code(
                phone,
                settings=OtpCodeSettings()
            )

        # اطلاعات لازم برای مرحله ورود
        # روی سرور نگه داشته می‌شود
        pending_auth[phone] = {
            "phone": challenge.phone_number,
            "phone_code_hash": challenge.phone_code_hash
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


# --------------------------------
# ورود با کد تأیید
# --------------------------------

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
            "message": "درخواست کد پیدا نشد؛ دوباره کد دریافت کنید"
        }

    try:

        client = await EitaaClient.create(
            require_auth=False
        )

        async with client:

            authorization = await client.auth.sign_in(
                auth_data["phone"],
                auth_data["phone_code_hash"],
                code
            )

        # بعد از ورود موفق، challenge را حذف می‌کنیم
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
