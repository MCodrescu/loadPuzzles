"""
Integration test for ChessAnalyzer with MCodrescu username.
This test uses real Chess.com API calls and Stockfish engine.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.chess_analyzer import ChessAnalyzer


@pytest.mark.integration
def test_chess_analyzer_live_with_mcodrescu(monkeypatch):
    """
    Integration test: Fetch and analyze a real game for MCodrescu from Chess.com.
    
    This test:
    1. Creates a ChessAnalyzer for MCodrescu
    2. Fetches actual games from Chess.com API
    3. Analyzes the first game using the Stockfish engine
    4. Verifies the analysis structure is correct
    
    Note: Requires internet access and Stockfish binary at the expected path.
    """
    # Set up environment
    monkeypatch.setenv(
        "STOCKFISH_PATH", 
        "/workspaces/loadPuzzles/bin/stockfish-ubuntu-x86-64-avx2"
    )
    
    # Create analyzer
    analyzer = ChessAnalyzer(
        username="MCodrescu",
        stockfish_path=os.environ["STOCKFISH_PATH"]
    )
    
    # Fetch games from current month
    import datetime
    now = datetime.datetime.utcnow()
    games = analyzer.get_games(now.year, now.month)
    
    # Verify we got games
    assert len(games) > 0, "No games found for MCodrescu in current month"
    
    # Analyze first game
    first_game = games[0]
    analysis = analyzer.analyze_game(first_game)
    
    # Verify analysis structure
    assert isinstance(analysis, list)
    assert len(analysis) > 0, "No moves were analyzed"
    
    # Verify each move has required fields
    for i, move in enumerate(analysis):
        assert "fen_before" in move, f"Move {i}: missing fen_before"
        assert "fen" in move, f"Move {i}: missing fen"
        assert "san" in move, f"Move {i}: missing san (Standard Algebraic Notation)"
        assert "coord" in move, f"Move {i}: missing coord (UCI notation)"
        assert "eval_change" in move, f"Move {i}: missing eval_change"
        assert "current_eval" in move, f"Move {i}: missing current_eval"
        assert "eval_after" in move, f"Move {i}: missing eval_after"
        assert "bestline" in move, f"Move {i}: missing bestline"
        assert "turn" in move, f"Move {i}: missing turn"
        assert move["turn"] in ["white", "black"], f"Move {i}: invalid turn value"
    
    # Print summary
    print(f"\n✓ Successfully analyzed {len(analysis)} moves from game")
    print(f"  Game UUID: {first_game.get('uuid')}")
    print(f"  Date: {first_game.get('end_time')}")
    print(f"  White: {first_game.get('white', {}).get('username')}")
    print(f"  Black: {first_game.get('black', {}).get('username')}")
    
    # Show first few moves
    for i, move in enumerate(analysis[:3]):
        print(f"\n  Move {i + 1}:")
        print(f"    {move['san']} ({move['coord']})")
        print(f"    Eval: {move['current_eval']} → {move['eval_after']}")
        print(f"    Change: {move['eval_change']:+d}")


if __name__ == "__main__":
    # Run with: pytest tests/test_chess_analyzer_integration.py -v -s
    pytest.main([__file__, "-v", "-s"])
