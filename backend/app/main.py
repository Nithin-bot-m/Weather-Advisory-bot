from fastapi import FastAPI
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="Weather Advisory Support Bot API",
    description="Backend API for Weather Advisory Support Bot",
    version="0.1.0",
)


@app.get("/")
def read_root():
    return {"message": "Weather Advisory Bot API is running"}
