import logging
import traceback

from fastapi import FastAPI, HTTPException
from app.chess_analyzer import main

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("load_puzzles")

app = FastAPI()

@app.post("/analyze")
def analyze(username: str):
    if not username:
        raise HTTPException(status_code=400, detail="username is required")

    try:
        logger.info("Received analyze request for username=%s", username)
        result = main(username)
        logger.info("Analysis completed for username=%s: games_analyzed=%s rows_loaded=%s",
                    username, result.get("games_analyzed"), result.get("rows_loaded"))
        return result
    except Exception as exc:
        logger.error(
            "Error processing /analyze request for username=%s: %s\n%s",
            username,
            exc,
            traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail="Internal server error")
