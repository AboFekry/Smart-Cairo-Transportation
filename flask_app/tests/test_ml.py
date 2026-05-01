"""
Unit tests for ml_predictor.py and train_model.py.

Run from flask_app/:
    pytest tests/ -v
"""
from __future__ import annotations

import sys
import os
import math
import csv
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import ml_predictor
from train_model import build_features, train_and_evaluate

import pandas as pd


# ============================================================================
# ml_predictor — in-process interface
# ============================================================================
class TestMLPredictor:
    def test_train_returns_dict(self):
        result = ml_predictor.train()
        assert isinstance(result, dict)

    def test_r2_above_threshold(self):
        result = ml_predictor.train()
        assert result["test_r2"] > 0.80, (
            f"R² = {result['test_r2']} below acceptable threshold 0.80"
        )

    def test_feature_importances_sum_to_one(self):
        result = ml_predictor.train()
        total = sum(fi["importance"] for fi in result["feature_importances"])
        assert math.isclose(total, 1.0, abs_tol=0.01)

    def test_predict_for_hour_returns_roads(self):
        ml_predictor.train()
        result = ml_predictor.predict_for_hour(8.0)
        assert "roads" in result
        assert len(result["roads"]) > 0

    def test_predict_road_fields(self):
        ml_predictor.train()
        road = ml_predictor.predict_for_hour(8.0)["roads"][0]
        assert "predicted_vehicles_per_hour" in road
        assert "capacity" in road
        assert "vc_ratio" in road

    def test_vc_ratio_calculated_correctly(self):
        ml_predictor.train()
        road = ml_predictor.predict_for_hour(8.0)["roads"][0]
        expected = road["predicted_vehicles_per_hour"] / road["capacity"]
        # vc_ratio may be rounded to 3 dp — use a relaxed tolerance
        assert math.isclose(road["vc_ratio"], expected, rel_tol=0.01)

    def test_predict_representative_hours(self):
        """Spot-check morning, afternoon, evening, night instead of all 24."""
        ml_predictor.train()
        for h in (2, 8, 14, 18):
            r = ml_predictor.predict_for_hour(float(h))
            assert len(r["roads"]) > 0, f"No roads returned for hour {h}"

    def test_hourly_profile_length(self):
        ml_predictor.train()
        result = ml_predictor.hourly_profile("1", "3")
        assert "hourly" in result
        assert len(result["hourly"]) == 24

    def test_hourly_profile_values_non_negative(self):
        ml_predictor.train()
        result = ml_predictor.hourly_profile("1", "3")
        for h in result["hourly"]:
            assert h["vehicles_per_hour"] >= 0


# ============================================================================
# train_model.py — standalone CLI
# ============================================================================
class TestBuildFeatures:
    def _minimal_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "hour": [8, 14, 18, 2, 8, 14, 18, 2],
            "distance_km": [5.0] * 8,
            "capacity": [2000] * 8,
            "mean_endpoint_population": [100000] * 8,
            "is_existing": [1] * 8,
            "vehicles_per_hour": [1800, 1200, 1600, 400, 1900, 1100, 1500, 350],
        })

    def test_returns_correct_shapes(self):
        df = self._minimal_df()
        X, y = build_features(df)
        assert X.shape == (8, 6)
        assert y.shape == (8,)

    def test_hour_cyclic_encoding(self):
        df = self._minimal_df()
        X, _ = build_features(df)
        # hour_sin = sin(2π * 8/24) for hour=8
        expected_sin = math.sin(2 * math.pi * 8 / 24)
        assert math.isclose(X[0, 0], expected_sin, abs_tol=1e-6)

    def test_missing_column_raises(self):
        df = self._minimal_df().drop(columns=["capacity"])
        with pytest.raises(ValueError, match="missing required columns"):
            build_features(df)

    def test_nan_rows_dropped(self):
        df = self._minimal_df()
        df.loc[3, "vehicles_per_hour"] = float("nan")
        X, y = build_features(df)
        assert X.shape[0] == 7   # one row dropped


class TestTrainAndEvaluate:
    def _write_temp_csv(self) -> str:
        rows = [
            {"road_id": f"1-{i}", "from_node": "1", "to_node": str(i),
             "period": "morning", "hour": 8, "distance_km": float(i),
             "capacity": 2000, "mean_endpoint_population": 100000,
             "is_existing": 1, "vehicles_per_hour": 1500 + i * 10}
            for i in range(2, 20)
        ]
        # Duplicate across periods to have enough rows
        full_rows = []
        for p, h in [("morning", 8), ("afternoon", 14), ("evening", 18), ("night", 2)]:
            for r in rows:
                full_rows.append({**r, "period": p, "hour": h,
                                   "vehicles_per_hour": r["vehicles_per_hour"] - (0 if p == "morning" else 200)})
        fh = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        )
        writer = csv.DictWriter(fh, fieldnames=list(full_rows[0].keys()))
        writer.writeheader()
        writer.writerows(full_rows)
        fh.close()
        return fh.name

    def test_train_completes(self, tmp_path):
        csv_path = self._write_temp_csv()
        out = str(tmp_path / "model.joblib")
        metrics = train_and_evaluate(
            csv_path=csv_path,
            output_path=out,
            n_estimators=10,   # fast for testing
            verbose=False,
        )
        assert metrics["test_r2"] is not None
        os.unlink(csv_path)

    def test_model_file_written(self, tmp_path):
        csv_path = self._write_temp_csv()
        out = str(tmp_path / "model.joblib")
        train_and_evaluate(csv_path=csv_path, output_path=out,
                           n_estimators=10, verbose=False)
        assert os.path.exists(out)
        os.unlink(csv_path)

    def test_metrics_json_written(self, tmp_path):
        csv_path = self._write_temp_csv()
        out = str(tmp_path / "model.joblib")
        train_and_evaluate(csv_path=csv_path, output_path=out,
                           n_estimators=10, verbose=False)
        json_path = str(tmp_path / "model.metrics.json")
        assert os.path.exists(json_path)
        os.unlink(csv_path)

    def test_missing_csv_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            train_and_evaluate(
                csv_path="/nonexistent/path.csv",
                output_path=str(tmp_path / "m.joblib"),
                verbose=False,
            )

    def test_metrics_have_expected_keys(self, tmp_path):
        csv_path = self._write_temp_csv()
        out = str(tmp_path / "model.joblib")
        metrics = train_and_evaluate(csv_path=csv_path, output_path=out,
                                     n_estimators=10, verbose=False)
        for key in ("test_r2", "test_mae_vehicles_per_hour",
                    "test_rmse_vehicles_per_hour", "feature_importances"):
            assert key in metrics, f"Missing metric: {key}"
        os.unlink(csv_path)
