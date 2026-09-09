from fastapi import FastAPI

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
