from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class PhoneRequest(BaseModel):
    phone: str


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
def send_code(data: PhoneRequest):
    phone = data.phone.strip()

    if not phone:
        return {
            "status": "error",
            "message": "Phone number is required"
        }

    return {
        "status": "ok",
        "message": "Phone received successfully",
        "phone": phone
    }
