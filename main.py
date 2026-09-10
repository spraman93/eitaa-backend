from fastapi import FastAPI, Request

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


@app.api_route("/auth/send-code", methods=["GET", "POST"])
async def send_code(request: Request):
    if request.method == "GET":
        return {
            "status": "ok",
            "method": "GET",
            "message": "send-code endpoint is working"
        }

    try:
        data = await request.json()
    except Exception:
        data = {}

    phone = data.get("phone", "")

    return {
        "status": "ok",
        "method": "POST",
        "message": "Phone received successfully",
        "phone": phone
    }    return {
        "status": "ok",
        "message": "Phone received successfully",
        "phone": phone
    }
