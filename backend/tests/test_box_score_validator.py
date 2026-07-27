"""BoxScoreValidator quarantine rules."""
from app.services.box_score_validator import BoxScoreValidator


def test_valid_sparse_record():
    result = BoxScoreValidator.validate_player_record(
        {"points": 22, "rebounds": 5, "assists": 7, "three_pointers_made": 2, "minutes_played": 34}
    )
    assert result["status"] == BoxScoreValidator.STATUS_VALID


def test_invalid_fgm_gt_fga():
    result = BoxScoreValidator.validate_player_record(
        {
            "points": 10,
            "field_goals_made": 6,
            "field_goals_attempted": 5,
            "three_pointers_made": 0,
            "free_throws_made": 0,
            "minutes_played": 20,
        }
    )
    assert result["status"] == BoxScoreValidator.STATUS_INVALID
    assert any("FGM" in f for f in result["failures"])


def test_invalid_points_identity_when_fg_present():
    result = BoxScoreValidator.validate_player_record(
        {
            "points": 99,
            "field_goals_made": 4,
            "field_goals_attempted": 10,
            "three_pointers_made": 1,
            "free_throws_made": 1,
            "minutes_played": 20,
        }
    )
    # expected = 2*(4-1)+3*1+1 = 10
    assert result["status"] == BoxScoreValidator.STATUS_INVALID
    assert any("points" in f for f in result["failures"])


def test_warning_zero_minutes_with_points():
    result = BoxScoreValidator.validate_player_record(
        {"points": 8, "rebounds": 0, "assists": 0, "three_pointers_made": 0, "minutes_played": 0}
    )
    assert result["status"] == BoxScoreValidator.STATUS_WARNING
