from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return "Eitaa Manager Backend is ONLINE"

@app.get("/status")
def status():
    return {
        "status": "ok",
        "message": "Backend is running"
    }
