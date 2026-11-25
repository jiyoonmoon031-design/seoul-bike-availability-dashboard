from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modeling.final_model import (  # noqa: E402
    sha256_file,
)
from src.modeling.inference import (  # noqa: E402
    build_prediction_response,
    load_inventory,
    load_point_in_time_features,
    validate_prediction_request,
)
from src.modeling.model_comparison import FittedBaselines  # noqa: E402
from src.modeling.runtime_fallback import apply_runtime_feature_fallback  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen Week 05 model using "
            "the model-backend prediction contract"
        )
    )

    parser.add_argument(
        "--request",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--feature-table",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--inventory",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--model",
        type=Path,
        default=Path("models/week05/final_model.joblib"),
    )

    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("reports/week05/" "final_model_metadata.json"),
    )

    parser.add_argument(
        "--feature-names",
        type=Path,
        default=Path("reports/week05/" "feature_names.json"),
    )

    parser.add_argument(
        "--fallback-baselines",
        type=Path,
    )

    parser.add_argument(
        "--fallback-metadata",
        type=Path,
    )

    parser.add_argument(
        "--output",
        type=Path,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    request_path = args.request.expanduser().resolve()
    feature_path = args.feature_table.expanduser().resolve()
    inventory_path = args.inventory.expanduser().resolve()
    model_path = args.model.expanduser().resolve()
    metadata_path = args.metadata.expanduser().resolve()
    feature_names_path = args.feature_names.expanduser().resolve()

    request = validate_prediction_request(
        json.loads(request_path.read_text(encoding="utf-8"))
    )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    feature_names = json.loads(feature_names_path.read_text(encoding="utf-8"))

    expected_sha256 = metadata["model_artifact"]["sha256"]

    actual_sha256 = sha256_file(model_path)

    if actual_sha256 != expected_sha256:
        raise RuntimeError("model artifact SHA256 does not " "match final metadata")

    candidate = joblib.load(model_path)

    if candidate.model_id != metadata["model_id"]:
        raise RuntimeError("serialized model_id does not " "match metadata")

    raw_feature_order = feature_names["raw_feature_order"]

    if list(candidate.feature_columns) != list(raw_feature_order):
        raise RuntimeError(
            "serialized model feature order " "does not match feature_names.json"
        )

    baselines = None

    if bool(args.fallback_baselines) != bool(args.fallback_metadata):
        raise RuntimeError(
            "--fallback-baselines and --fallback-metadata " "must be supplied together"
        )

    if args.fallback_baselines is not None:
        fallback_path = args.fallback_baselines.expanduser().resolve()
        fallback_metadata_path = args.fallback_metadata.expanduser().resolve()

        fallback_metadata = json.loads(
            fallback_metadata_path.read_text(encoding="utf-8")
        )

        expected_fallback_sha256 = fallback_metadata["artifact"]["sha256"]

        actual_fallback_sha256 = sha256_file(fallback_path)

        if actual_fallback_sha256 != expected_fallback_sha256:
            raise RuntimeError(
                "fallback baseline artifact SHA256 " "does not match Week 11 metadata"
            )

        baselines = joblib.load(fallback_path)

        if not isinstance(
            baselines,
            FittedBaselines,
        ):
            raise RuntimeError("serialized fallback artifact is not " "FittedBaselines")

    frame = load_point_in_time_features(
        feature_path,
        feature_columns=raw_feature_order,
        station_ids=request["station_ids"],
        base_time=request["base_time"],
    )

    inventory = load_inventory(inventory_path)

    response = build_prediction_response(
        candidate=candidate,
        request=request,
        feature_frame=frame,
        inventory=inventory,
        model_version=metadata["model_version"],
        baselines=baselines,
    )

    response = apply_runtime_feature_fallback(
        response=response,
        request=request,
        inventory=inventory,
        baselines=baselines,
    )

    rendered = json.dumps(
        response,
        ensure_ascii=False,
        indent=2,
    )

    if args.output:
        output_path = args.output.expanduser().resolve()

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            rendered + "\n",
            encoding="utf-8",
        )
    else:
        print(rendered)


if __name__ == "__main__":
    main()
