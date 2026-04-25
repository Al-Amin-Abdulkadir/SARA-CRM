from fastapi import FastAPI
from app.config.settings import settings


app = FastAPI(title=settings.app_name, version="1.0.0", debug=settings.debug)

@app.get("/health")
def health_check():
    return {
        "status" : "Successful",
        "app" : settings.app_name
    }
