import numpy as np

from scripts.analyze_week04_validation_errors import summarize_residuals


def test_summarize_residuals_tracks_bias_and_direction() -> None:
    residual = np.asarray([-2.0, 0.0, 1.0, 3.0])
    result = summarize_residuals(residual, np.abs(residual))

    assert result["evaluated_rows"] == 4
    assert result["mae"] == 1.5
    assert result["mean_error"] == 0.5
    assert result["underprediction_rate"] == 0.25
    assert result["overprediction_rate"] == 0.5
    assert result["exact_rate"] == 0.25
