from royal_analyzer.controller import RoyalAnalyzerController
from royal_analyzer.dice_decoder import decode_die, parse_grid_area
from royal_analyzer.models import CombinationType, GameResult
from royal_analyzer.prediction_engine import PredictionEngine
from royal_analyzer.statistics import classify_combination
from royal_analyzer.storage import Storage


def test_decode_die_map():
    assert decode_die([(2, 2)]) == 1
    assert decode_die([(1, 1), (3, 3)]) == 2
    assert decode_die([(1, 1), (2, 2), (3, 3)]) == 3
    assert decode_die([(1, 1), (1, 3), (3, 1), (3, 3)]) == 4
    assert decode_die([(1, 1), (1, 3), (2, 2), (3, 1), (3, 3)]) == 5
    assert decode_die([(1, 1), (1, 3), (2, 1), (2, 3), (3, 1), (3, 3)]) == 6


def test_parse_grid_area():
    assert parse_grid_area("grid-area: 2 / 3;") == (2, 3)


def test_classify_combination():
    assert classify_combination([1, 1, 1, 1, 1]) == CombinationType.PENTA_TRICK
    assert classify_combination([1, 1, 1, 1, 2]) == CombinationType.QUADRO_TRICK
    assert classify_combination([1, 1, 1, 2, 2]) == CombinationType.TRICK_DOUBLE
    assert classify_combination([1, 1, 2, 2, 3]) == CombinationType.DOUBLE_TRICK
    assert classify_combination([1, 2, 3, 4, 5]) == CombinationType.SERIES
    assert classify_combination([1, 1, 1, 2, 3]) == CombinationType.HAT_TRICK
    assert classify_combination([1, 1, 2, 3, 4]) == CombinationType.DOUBLE


def test_prediction_enumerates_42_options():
    engine = PredictionEngine()
    assert len(engine.all_options()) == 42
    recs = engine.recommend([GameResult((1, 2, 3, 4, 5), combination=CombinationType.SERIES)])
    assert len(recs) == 5
    assert recs[0].rank == 1


def test_storage_roundtrip_and_duplicate_detection(tmp_path):
    storage = Storage(tmp_path / "test.sqlite3")
    game = GameResult((1, 1, 2, 3, 4), combination=CombinationType.DOUBLE)
    assert storage.add_game(game)
    assert not storage.add_game(game)
    games = storage.list_games()
    assert games[0].dice == (1, 1, 2, 3, 4)
    assert games[0].combination == CombinationType.DOUBLE
    storage.close()


def test_controller_settles_prediction_and_updates_stats(tmp_path):
    storage = Storage(tmp_path / "controller.sqlite3")
    controller = RoyalAnalyzerController(storage=storage)
    first = GameResult((1, 2, 3, 4, 5), combination=CombinationType.SERIES)
    controller.handle_result(first)
    assert controller.last_recommendations
    second = GameResult((controller.last_recommendations[0].option.first_die, 6, 6, 6, 6), combination=controller.last_recommendations[0].option.combination)
    controller.handle_result(second)
    stats = storage.prediction_stats()
    assert stats.total >= 1
    storage.close()
