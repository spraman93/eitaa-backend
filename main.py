from fastapi import FastAPI, Request
from eitaa_cli import EitaaClient
from eitaa_cli.models import OtpCodeSettings

app = FastAPI()


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


@app.post("/auth/send-code")
async def send_code(request: Request):

    data = await request.json()
    phone = data.get("phone", "").strip()

    if not phone:
        return {
            "status": "error",
            "message": "شماره موبایل وارد نشده است"
        }

    try:
        client = await EitaaClient.create(require_auth=False)

        async with client:
            challenge = await client.auth.request_code(
                phone,
                settings=OtpCodeSettings()
            )

        return {
            "status": "ok",
            "message": "کد درخواست شد",
            "phone": challenge.phone_number,
            "delivery": str(challenge.delivery),
            "next_delivery": str(challenge.next_delivery),
            "timeout_seconds": challenge.timeout_seconds,
            "phone_code_hash": challenge.phone_code_hash
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
