"""Model-side feature engineering and baseline evaluation utilities."""

from .feature_engineering import (
    FeatureContractError,
    build_feature_manifest,
    build_week03_features,
    get_model_feature_columns,
)
from .naive_baseline import (
    add_naive_predictions,
    assign_chronological_splits,
    evaluate_naive_baselines,
)

__all__ = [
    "FeatureContractError",
    "add_naive_predictions",
    "assign_chronological_splits",
    "build_feature_manifest",
    "build_week03_features",
    "evaluate_naive_baselines",
    "get_model_feature_columns",
]
