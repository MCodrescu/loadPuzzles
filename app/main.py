from fastapi import FastAPI, HTTPException
from app.chess_analyzer import main

app = FastAPI()

@app.post("/analyze")
def analyze(username: str):
    if not username:
        raise HTTPException(status_code=400, detail="username is required")
    return main(username)
