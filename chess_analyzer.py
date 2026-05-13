import os
import datetime
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

import io
import chess.pgn
import pandas as pd
from stockfish import Stockfish
from chessdotcom import ChessDotComClient


class ChessAnalyzer:
    """
    Analyzes chess games fetched from Chess.com using the Stockfish engine.

    Retrieves games for a given player and evaluates each position to identify
    blunders and best moves.
    """

    def __init__(self, username: str, stockfish_path: str, user_agent: str = "chesspuzzles"):
        """
        Initialize the ChessAnalyzer.

        Args:
            username: Chess.com username to fetch games for.
            stockfish_path: Absolute path to the Stockfish binary.
            user_agent: User-agent string sent to the Chess.com API.
        """
        self.username = username
        self.client = ChessDotComClient(user_agent=user_agent)
        self.sf = Stockfish(stockfish_path)
        self.sf.set_turn_perspective(False)

    def get_games(self, year: int, month: int) -> list:
        """
        Fetch all games played by the user in a given month.

        Args:
            year: The year to fetch games for.
            month: The month (1–12) to fetch games for.

        Returns:
            A list of game dictionaries as returned by the Chess.com API.
        """
        return self.client.get_player_games_by_month(self.username, year, month).json.get("games")

    def analyze_game(self, game: dict) -> list[dict]:
        """
        Analyze every position in a single game using Stockfish.

        For each move, computes the evaluation before and after the move,
        the evaluation change, and Stockfish's top recommended continuations.

        Args:
            game: A game dictionary from the Chess.com API containing a "pgn" key.

        Returns:
            A list of dictionaries, one per move, each containing:
                - fen_before: FEN string of the position before the move.
                - fen: FEN string of the position after the move.
                - san: The move in Standard Algebraic Notation.
                - coord: The move in UCI coordinate notation (e.g. "e2e4").
                - eval_change: Change in centipawn evaluation after the move.
                - current_eval: Centipawn evaluation before the move.
                - eval_after: Centipawn evaluation after the move.
                - bestline: List of UCI moves representing Stockfish's top continuation.
                - turn: "white" or "black" indicating whose turn it was after the move.
        """
        pgn = io.StringIO(game.get("pgn"))
        all_positions = list(chess.pgn.read_game(pgn).mainline())
        result = []

        for i in range(len(all_positions) - 1):
            current_pos = all_positions[i]
            next_pos = all_positions[i + 1]

            current_fen = current_pos.board().fen()
            next_fen = next_pos.board().fen()

            move = next_pos.move
            move_san = current_pos.board().san(move) if move else None
            move_coord = current_pos.board().uci(move) if move else None

            self.sf.set_fen_position(current_fen)
            current_eval = self.sf.get_evaluation()

            self.sf.set_fen_position(next_fen)
            next_eval = self.sf.get_evaluation()
            best_line = self.sf.get_top_moves()

            eval_change = (
                next_eval.get("value") - current_eval.get("value")
                if current_eval and next_eval else None
            )

            result.append({
                "fen_before": current_fen,
                "fen": next_fen,
                "san": move_san,
                "coord": move_coord,
                "eval_change": eval_change,
                "current_eval": current_eval.get("value"),
                "eval_after": next_eval.get("value"),
                "bestline": [m.get("Move") for m in best_line],
                "turn": "white" if next_pos.board().turn else "black",
            })

        return result

    def get_top_blunders(self, game: dict, n: int = 3) -> list[dict]:
        """
        Return the moves with the largest negative evaluation swings in a game.

        Args:
            game: A game dictionary from the Chess.com API.
            n: Number of top blunders to return. Defaults to 3.

        Returns:
            A list of up to n move dictionaries sorted by eval_change descending
            (i.e. the moves where the position deteriorated most).
        """
        df = pd.DataFrame(self.analyze_game(game))
        return df.sort_values("eval_change", ascending=False).head(n).to_dict(orient="records")
    
    def load_to_db(self, results: list[dict], table_name: str = "chess_puzzles") -> None:
        """
        Load analysis results into a PostgreSQL table.

        Adds a deterministic `puzzle_id` (UUID derived from username + position + move)
        and a `username` column before inserting. The `bestline` list is serialized
        to a JSON string for storage. Reads connection details from the environment:
            PGHOST, PGDATABASE, PGUSER, PGPASSWORD, and optionally PGPORT (default 5432).

        Args:
            results: List of move dictionaries returned by `analyze_game`.
            table_name: Target table name in the database. Defaults to "chess_puzzles".
        """
        import os
        import json
        import uuid
        from urllib.parse import quote_plus
        from sqlalchemy import create_engine

        df = pd.DataFrame(results)
        df["username"] = self.username
        df["puzzle_id"] = df.apply(
            lambda row: str(uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{self.username}:{row['fen_before']}:{row['coord']}"
            )),
            axis=1,
        )
        df["bestline"] = df["bestline"].apply(json.dumps)

        host = os.environ["PGHOST"]
        port = os.environ.get("PGPORT", "5432")
        dbname = os.environ["PGDATABASE"]
        user = os.environ["PGUSER"]
        password = quote_plus(os.environ["PGPASSWORD"])

        engine = create_engine(
            f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
        )
        try:
            df.to_sql(table_name, engine, if_exists="append", index=False)
        finally:
            engine.dispose()

def _get_engine():
    host = os.environ["PGHOST"]
    port = os.environ.get("PGPORT", "5432")
    dbname = os.environ["PGDATABASE"]
    user = os.environ["PGUSER"]
    password = quote_plus(os.environ["PGPASSWORD"])
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}")


def main(username: str) -> dict:
    """
    Incrementally load chess game analysis for a Chess.com user into PostgreSQL.

    Fetches games for the current calendar month, queries the database for game
    UIDs already analyzed for this user, and only analyzes and loads the remaining
    games. Intended to be called from a serverless function handler.

    Reads STOCKFISH_PATH, PGHOST, PGDATABASE, PGUSER, PGPASSWORD, and optionally
    PGPORT from the environment.

    Args:
        username: Chess.com username to process.

    Returns:
        A dict with:
            - games_analyzed: Number of new games analyzed this run.
            - rows_loaded: Total move rows inserted into the database.
    """
    analyzer = ChessAnalyzer(
        username=username,
        stockfish_path=os.environ["STOCKFISH_PATH"],
    )

    now = datetime.datetime.utcnow()
    games = analyzer.get_games(now.year, now.month)

    if not games:
        return {"games_analyzed": 0, "rows_loaded": 0}

    engine = _get_engine()
    try:
        with engine.connect() as conn:
            try:
                rows = conn.execute(
                    text(
                        "SELECT DISTINCT game_uid FROM chess_puzzles "
                        "WHERE username = :username"
                    ),
                    {"username": username},
                ).fetchall()
                analyzed_uids = {row[0] for row in rows}
            except Exception:
                # Table doesn't exist yet on the first run
                analyzed_uids = set()
    finally:
        engine.dispose()

    new_games = [
        g for g in games
        if g.get("uuid") not in analyzed_uids
    ]

    total_rows = 0
    for game in new_games:
        game_uid = game.get("uuid")
        results = analyzer.analyze_game(game)
        for row in results:
            row["game_uid"] = game_uid
        analyzer.load_to_db(results)
        total_rows += len(results)

    return {"games_analyzed": len(new_games), "rows_loaded": total_rows}
