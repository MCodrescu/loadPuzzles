import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.chess_analyzer import ChessAnalyzer, main


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("STOCKFISH_PATH", "/workspaces/loadPuzzles/bin/stockfish-ubuntu-x86-64-avx2")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DATABASE", "test_db")
    monkeypatch.setenv("POSTGRES_USER", "test_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test_password")


@pytest.fixture
def sample_game():
    """Sample chess game in PGN format."""
    return {
        "uuid": "test-game-uuid-123",
        "pgn": """[Event "Blitz"]
[Site "Chess.com"]
[Date "2024.05.14"]
[White "MCodrescu"]
[Black "Opponent"]
[Result "1-0"]

1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 1-0"""
    }


@pytest.fixture
def mock_analyzer():
    """Create a mock ChessAnalyzer."""
    with patch('app.chess_analyzer.ChessAnalyzer') as MockAnalyzer:
        analyzer = Mock()
        MockAnalyzer.return_value = analyzer
        
        # Mock get_games
        analyzer.get_games.return_value = []
        
        # Mock analyze_game
        analyzer.analyze_game.return_value = [
            {
                "fen_before": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
                "fen": "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2",
                "san": "c5",
                "coord": "c7c5",
                "eval_change": -25,
                "current_eval": 35,
                "eval_after": 10,
                "bestline": ["Nf3"],
                "turn": "white",
            }
        ]
        
        # Mock load_to_db
        analyzer.load_to_db.return_value = None
        
        yield MockAnalyzer


def test_chess_analyzer_initialization(mock_env):
    """Test that ChessAnalyzer initializes correctly."""
    analyzer = ChessAnalyzer(
        username="MCodrescu",
        stockfish_path="/workspaces/loadPuzzles/bin/stockfish-ubuntu-x86-64-avx2"
    )
    assert analyzer.username == "MCodrescu"
    assert analyzer.client is not None
    assert analyzer.sf is not None


def test_analyze_game_structure(mock_env, sample_game):
    """Test that analyze_game returns properly structured data."""
    analyzer = ChessAnalyzer(
        username="MCodrescu",
        stockfish_path="/workspaces/loadPuzzles/bin/stockfish-ubuntu-x86-64-avx2"
    )
    
    result = analyzer.analyze_game(sample_game)
    
    assert isinstance(result, list)
    assert len(result) > 0
    
    for move_analysis in result:
        assert "fen_before" in move_analysis
        assert "fen" in move_analysis
        assert "san" in move_analysis
        assert "coord" in move_analysis
        assert "eval_change" in move_analysis
        assert "current_eval" in move_analysis
        assert "eval_after" in move_analysis
        assert "bestline" in move_analysis
        assert "turn" in move_analysis


@patch('app.chess_analyzer._get_engine')
@patch('app.chess_analyzer.ChessAnalyzer.get_games')
def test_main_function_no_new_games(mock_get_games, mock_get_engine, mock_env):
    """Test main function when there are no new games to analyze."""
    # Mock the engine and database connection
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_engine.connect.return_value.__exit__.return_value = None
    mock_get_engine.return_value = mock_engine
    
    # Mock get_games to return empty list
    mock_get_games.return_value = []
    
    result = main("MCodrescu")
    
    assert result["games_analyzed"] == 0
    assert result["rows_loaded"] == 0


@patch('app.chess_analyzer._get_engine')
@patch('app.chess_analyzer.ChessAnalyzer')
def test_main_function_with_games(mock_analyzer_class, mock_get_engine, mock_env, sample_game):
    """Test main function with sample games."""
    # Mock the engine
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = []  # No previously analyzed games
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    mock_engine.connect.return_value.__exit__.return_value = None
    mock_get_engine.return_value = mock_engine
    
    # Mock the ChessAnalyzer
    mock_analyzer = MagicMock()
    mock_analyzer_class.return_value = mock_analyzer
    mock_analyzer.get_games.return_value = [sample_game]
    mock_analyzer.analyze_game.return_value = [
        {
            "fen_before": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            "fen": "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2",
            "san": "c5",
            "coord": "c7c5",
            "eval_change": -25,
            "current_eval": 35,
            "eval_after": 10,
            "bestline": ["Nf3"],
            "turn": "white",
            "game_uid": sample_game["uuid"],
        }
    ]
    
    result = main("MCodrescu")
    
    assert result["games_analyzed"] == 1
    assert result["rows_loaded"] == 1
    mock_analyzer.load_to_db.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
