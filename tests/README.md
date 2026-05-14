# Test Suite

## Running the Tests

### Unit Tests (Mocked)
These tests run quickly and don't require external services:

```bash
pytest tests/test_chess_analyzer.py -v
```

### Integration Tests (Real Chess.com & Stockfish)
These tests call the real Chess.com API and use the Stockfish engine:

```bash
pytest tests/test_chess_analyzer_integration.py -v -s
```

The integration test specifically:
- Fetches real games for **MCodrescu** from Chess.com
- Analyzes the current month's games using Stockfish
- Verifies the analysis structure
- Prints a summary of analyzed moves

### Run All Tests
```bash
pytest tests/ -v
```

## Test Coverage

### Unit Tests (`test_chess_analyzer.py`)
- `test_chess_analyzer_initialization` - Verifies ChessAnalyzer setup
- `test_analyze_game_structure` - Verifies analysis returns correct data structure
- `test_main_function_no_new_games` - Tests main() with no games
- `test_main_function_with_games` - Tests main() with sample games

### Integration Tests (`test_chess_analyzer_integration.py`)
- `test_chess_analyzer_live_with_mcodrescu` - Live test with real data for MCodrescu

## Requirements

For integration tests, ensure you have:
1. Stockfish binary at: `/workspaces/loadPuzzles/bin/stockfish-ubuntu-x86-64-avx2`
2. Internet access (to reach Chess.com API)
3. All dependencies installed: `pip install -r requirements.txt` (or via pyproject.toml)
