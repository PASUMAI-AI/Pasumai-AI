import os
import math
import sqlite3
import threading

import numpy as np
import pandas as pd
# XGBoost may be blocked by Windows Application Control on some PCs.
# GRAM AI should still start and use the remaining forecasting models.
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
    print("✓ XGBoost loaded successfully")
except Exception as e:
    xgb = None
    XGBOOST_AVAILABLE = False
    print("⚠ XGBoost unavailable on this machine.")
    print("  GRAM AI will continue without XGBoost.")
    print("  Reason:", str(e).splitlines()[-1] if str(e) else "Unknown")
    
import lightgbm as lgb


# =========================================================
# CONFIGURATION
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "gramai.db")

MODEL_CACHE = {}
MODEL_LOCK = threading.Lock()


# =========================================================
# ML FEATURES
# =========================================================

FEATURES = [
    "market_id",
    "lat",
    "lon",
    "market_fee_pct",
    "day_of_year",
    "month",

    "price_lag_1",
    "price_lag_3",
    "price_lag_7",

    "rolling_price_3",
    "rolling_price_7",

    "arrival_lag_1",
    "arrival_mean_3",
    "arrival_change",

    "temperature_c",
    "rainfall_mm",
    "demand_index",
]


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


# =========================================================
# LOAD DATASET FOR A CROP
# =========================================================

def load_crop_data(crop):
    connection = get_connection()

    query = """
        SELECT
            p.market_id,
            p.crop,
            p.price_date,
            p.modal_price,
            p.arrivals_qtl,
            p.temperature_c,
            p.rainfall_mm,
            p.demand_index,

            m.lat,
            m.lon,
            m.market_fee_pct,
            m.name,
            m.state,
            m.city

        FROM prices p

        JOIN markets m
            ON m.id = p.market_id

        WHERE p.crop = ?

        ORDER BY
            p.market_id,
            p.price_date
    """

    rows = connection.execute(
        query,
        (crop,)
    ).fetchall()

    connection.close()

    dataframe = pd.DataFrame(
        [dict(row) for row in rows]
    )

    if dataframe.empty:
        return dataframe

    dataframe["price_date"] = pd.to_datetime(
        dataframe["price_date"]
    )

    return dataframe


# =========================================================
# FEATURE ENGINEERING
# =========================================================

def create_features(dataframe):

    market_frames = []

    for market_id, market_data in dataframe.groupby(
        "market_id"
    ):

        market_data = market_data.sort_values(
            "price_date"
        ).copy()

        # ---------------------------
        # DATE FEATURES
        # ---------------------------

        market_data["day_of_year"] = (
            market_data["price_date"]
            .dt
            .dayofyear
        )

        market_data["month"] = (
            market_data["price_date"]
            .dt
            .month
        )

        # ---------------------------
        # PRICE LAGS
        # ---------------------------

        market_data["price_lag_1"] = (
            market_data["modal_price"]
            .shift(1)
        )

        market_data["price_lag_3"] = (
            market_data["modal_price"]
            .shift(3)
        )

        market_data["price_lag_7"] = (
            market_data["modal_price"]
            .shift(7)
        )

        # ---------------------------
        # PRICE ROLLING FEATURES
        # ---------------------------

        market_data["rolling_price_3"] = (
            market_data["modal_price"]
            .shift(1)
            .rolling(3)
            .mean()
        )

        market_data["rolling_price_7"] = (
            market_data["modal_price"]
            .shift(1)
            .rolling(7)
            .mean()
        )

        # ---------------------------
        # ARRIVAL FEATURES
        # ---------------------------

        market_data["arrival_lag_1"] = (
            market_data["arrivals_qtl"]
            .shift(1)
        )

        market_data["arrival_mean_3"] = (
            market_data["arrivals_qtl"]
            .shift(1)
            .rolling(3)
            .mean()
        )

        market_data["arrival_change"] = (
            market_data["arrivals_qtl"]
            .shift(1)
            -
            market_data["arrivals_qtl"]
            .shift(2)
        )

        # Target is today's actual price
        market_data["target"] = (
            market_data["modal_price"]
        )

        market_frames.append(
            market_data
        )

    if not market_frames:
        return pd.DataFrame()

    result = pd.concat(
        market_frames,
        ignore_index=True
    )

    result = result.dropna(
        subset=FEATURES + ["target"]
    )

    return result


# =========================================================
# EVALUATION METRICS
# =========================================================

def calculate_metrics(actual, predicted):

    actual = np.asarray(
        actual,
        dtype=float
    )

    predicted = np.asarray(
        predicted,
        dtype=float
    )

    # ---------------------------
    # MAE
    # ---------------------------

    mae = np.mean(
        np.abs(
            actual - predicted
        )
    )

    # ---------------------------
    # RMSE
    # ---------------------------

    rmse = np.sqrt(
        np.mean(
            (actual - predicted) ** 2
        )
    )

    # ---------------------------
    # MAPE
    # ---------------------------

    safe_actual = np.where(
        np.abs(actual) < 1e-8,
        1,
        actual
    )

    mape = (
        np.mean(
            np.abs(
                (actual - predicted)
                /
                safe_actual
            )
        )
        * 100
    )

    # ---------------------------
    # R²
    # ---------------------------

    ss_residual = np.sum(
        (actual - predicted) ** 2
    )

    ss_total = np.sum(
        (
            actual
            -
            np.mean(actual)
        ) ** 2
    )

    if ss_total > 1e-9:
        r2 = (
            1
            -
            ss_residual
            /
            ss_total
        )
    else:
        r2 = 0

    return {
        "MAE": round(float(mae), 2),
        "RMSE": round(float(rmse), 2),
        "MAPE": round(float(mape), 2),
        "R2": round(float(r2), 4),
    }


# =========================================================
# TRAIN XGBOOST + LIGHTGBM
# =========================================================

def train_crop_models(
    crop,
    force_retrain=False
):

    # Return cached model
    if (
        crop in MODEL_CACHE
        and not force_retrain
    ):
        return MODEL_CACHE[crop]

    with MODEL_LOCK:

        # Check cache again after waiting for lock
        if (
            crop in MODEL_CACHE
            and not force_retrain
        ):
            return MODEL_CACHE[crop]

        raw_data = load_crop_data(
            crop
        )

        if raw_data.empty:
            raise ValueError(
                f"No dataset found for {crop}"
            )

        feature_data = create_features(
            raw_data
        )

        if len(feature_data) < 100:
            raise ValueError(
                "Not enough training records."
            )

        # =====================================================
        # TIME-AWARE VALIDATION
        #
        # Last 3 valid observations from every market become
        # validation data.
        # =====================================================

        validation_indexes = (
            feature_data
            .groupby("market_id")
            .tail(3)
            .index
        )

        validation_data = (
            feature_data
            .loc[validation_indexes]
        )

        training_data = (
            feature_data
            .drop(validation_indexes)
        )

        X_train = (
            training_data[FEATURES]
            .astype(float)
        )

        y_train = (
            training_data["target"]
            .astype(float)
        )

        X_validation = (
            validation_data[FEATURES]
            .astype(float)
        )

        y_validation = (
            validation_data["target"]
            .astype(float)
        )

        # =====================================================
        # XGBOOST
        # =====================================================

        xgb_train_matrix = xgb.DMatrix(
            X_train,
            label=y_train,
            feature_names=FEATURES
        )

        xgb_validation_matrix = xgb.DMatrix(
            X_validation,
            feature_names=FEATURES
        )

        xgb_model = xgb.train(

            {
                "objective": "reg:squarederror",

                # Faster training for Render
                "eta": 0.08,

                "max_depth": 4,

                "subsample": 0.85,

                "colsample_bytree": 0.85,

                "min_child_weight": 2,

                "lambda": 1.0,

                "alpha": 0.05,

                "seed": 42,

                "verbosity": 0,

                # IMPORTANT FOR RENDER
                "nthread": 2,
            },

            xgb_train_matrix,

            # Reduced from 180
            num_boost_round=70,
        )

        xgb_predictions = (
            xgb_model.predict(
                xgb_validation_matrix
            )
        )

        xgb_metrics = calculate_metrics(
            y_validation,
            xgb_predictions
        )

        # =====================================================
        # LIGHTGBM
        # =====================================================

        lgb_training_dataset = lgb.Dataset(

            X_train,

            label=y_train,

            feature_name=FEATURES,

            free_raw_data=False
        )

        lightgbm_model = lgb.train(

            {
                "objective": "regression",

                "metric": "rmse",

                # Faster training
                "learning_rate": 0.08,

                "num_leaves": 20,

                "max_depth": 5,

                "feature_fraction": 0.9,

                "bagging_fraction": 0.85,

                "bagging_freq": 1,

                "min_data_in_leaf": 10,

                "lambda_l1": 0.05,

                "lambda_l2": 1.0,

                "seed": 42,

                "verbosity": -1,

                # IMPORTANT FOR RENDER
                "num_threads": 2,
            },

            lgb_training_dataset,

            # Reduced from 180
            num_boost_round=70,
        )

        lightgbm_predictions = (
            lightgbm_model.predict(
                X_validation
            )
        )

        lightgbm_metrics = (
            calculate_metrics(
                y_validation,
                lightgbm_predictions
            )
        )

        # =====================================================
        # ADAPTIVE MODEL SELECTION
        # =====================================================

        xgb_mape = (
            xgb_metrics["MAPE"]
        )

        lgb_mape = (
            lightgbm_metrics["MAPE"]
        )

        mape_difference = abs(
            xgb_mape
            -
            lgb_mape
        )

        # If both models are extremely close,
        # use weighted ensemble.
        if mape_difference <= 0.35:

            selected_model = "ENSEMBLE"

        elif xgb_mape < lgb_mape:

            selected_model = "XGBOOST"

        else:

            selected_model = "LIGHTGBM"

        result = {

            "raw": raw_data,

            "features": feature_data,

            "xgb_model": xgb_model,

            "lightgbm_model": lightgbm_model,

            "xgb_metrics": xgb_metrics,

            "lightgbm_metrics": lightgbm_metrics,

            "selected_model": selected_model,
        }

        # Save in memory
        MODEL_CACHE[crop] = result

        return result


# =========================================================
# SINGLE FUTURE PREDICTION
# =========================================================

def predict_single_row(
    model_bundle,
    feature_row
):

    dataframe = pd.DataFrame(
        [feature_row],
        columns=FEATURES
    ).astype(float)

    # ---------------------------
    # XGBOOST PREDICTION
    # ---------------------------

    xgb_matrix = xgb.DMatrix(
        dataframe,
        feature_names=FEATURES
    )

    xgb_price = float(
        model_bundle[
            "xgb_model"
        ].predict(
            xgb_matrix
        )[0]
    )

    # ---------------------------
    # LIGHTGBM PREDICTION
    # ---------------------------

    lightgbm_price = float(

        model_bundle[
            "lightgbm_model"
        ].predict(
            dataframe
        )[0]
    )

    selected_model = (
        model_bundle[
            "selected_model"
        ]
    )

    # ---------------------------
    # FINAL PREDICTION
    # ---------------------------

    if selected_model == "XGBOOST":

        final_price = xgb_price

    elif selected_model == "LIGHTGBM":

        final_price = lightgbm_price

    else:

        # Weighted by inverse MAPE

        xgb_error = max(
            model_bundle[
                "xgb_metrics"
            ]["MAPE"],
            0.1
        )

        lgb_error = max(
            model_bundle[
                "lightgbm_metrics"
            ]["MAPE"],
            0.1
        )

        xgb_weight = (
            1
            /
            xgb_error
        )

        lgb_weight = (
            1
            /
            lgb_error
        )

        final_price = (

            xgb_price
            *
            xgb_weight

            +

            lightgbm_price
            *
            lgb_weight

        ) / (

            xgb_weight
            +
            lgb_weight
        )

    return (
        xgb_price,
        lightgbm_price,
        final_price
    )


# =========================================================
# PREDICTABILITY SCORE
# =========================================================

def calculate_predictability_score(

    model_bundle,

    price_history,

    xgboost_prediction,

    lightgbm_prediction,

    horizon,

    record_count
):

    selected = (
        model_bundle[
            "selected_model"
        ]
    )

    # =====================================================
    # 1. MODEL ACCURACY
    # 30%
    # =====================================================

    if selected == "XGBOOST":

        selected_mape = (
            model_bundle[
                "xgb_metrics"
            ]["MAPE"]
        )

    elif selected == "LIGHTGBM":

        selected_mape = (
            model_bundle[
                "lightgbm_metrics"
            ]["MAPE"]
        )

    else:

        selected_mape = (

            model_bundle[
                "xgb_metrics"
            ]["MAPE"]

            +

            model_bundle[
                "lightgbm_metrics"
            ]["MAPE"]

        ) / 2

    model_accuracy = max(

        0,

        min(
            100,

            100
            -
            selected_mape
            *
            4
        )
    )

    # =====================================================
    # 2. MODEL AGREEMENT
    # 20%
    # =====================================================

    average_prediction = max(

        abs(
            (
                xgboost_prediction
                +
                lightgbm_prediction
            )
            /
            2
        ),

        1
    )

    disagreement_percentage = (

        abs(
            xgboost_prediction
            -
            lightgbm_prediction
        )

        /
        average_prediction

        *
        100
    )

    model_agreement = max(

        0,

        min(

            100,

            100
            -
            disagreement_percentage
            *
            6
        )
    )

    # =====================================================
    # 3. HISTORICAL PRICE STABILITY
    # 20%
    # =====================================================

    history_array = np.asarray(
        price_history,
        dtype=float
    )

    mean_price = max(
        float(
            np.mean(
                history_array
            )
        ),
        1
    )

    coefficient_of_variation = (

        float(
            np.std(
                history_array
            )
        )

        /
        mean_price

        *
        100
    )

    historical_stability = max(

        0,

        min(

            100,

            100
            -
            coefficient_of_variation
            *
            6
        )
    )

    # =====================================================
    # 4. DATA AVAILABILITY
    # 15%
    # =====================================================

    data_availability = max(

        0,

        min(

            100,

            record_count
            /
            30
            *
            100
        )
    )

    # =====================================================
    # 5. HORIZON RELIABILITY
    # 15%
    # =====================================================

    horizon_scores = {

        1: 96,

        3: 88,

        7: 76,
    }

    horizon_reliability = (
        horizon_scores.get(
            horizon,
            70
        )
    )

    # =====================================================
    # FINAL PREDICTABILITY SCORE
    # =====================================================

    score = (

        0.30
        *
        model_accuracy

        +

        0.20
        *
        model_agreement

        +

        0.20
        *
        historical_stability

        +

        0.15
        *
        data_availability

        +

        0.15
        *
        horizon_reliability
    )

    # =====================================================
    # CLASSIFICATION
    # =====================================================

    if score >= 85:

        level = "HIGH"

    elif score >= 70:

        level = "GOOD"

    elif score >= 50:

        level = "MODERATE"

    else:

        level = "LOW"

    return {

        "score": round(
            score,
            1
        ),

        "level": level,

        "components": {

            "model_accuracy":
                round(
                    model_accuracy,
                    1
                ),

            "model_agreement":
                round(
                    model_agreement,
                    1
                ),

            "historical_stability":
                round(
                    historical_stability,
                    1
                ),

            "data_availability":
                round(
                    data_availability,
                    1
                ),

            "horizon_reliability":
                round(
                    horizon_reliability,
                    1
                ),
        },
    }


# =========================================================
# EXPLAINABILITY
# =========================================================

def get_feature_importance(
    model_bundle
):

    readable_names = {

        "market_id":
            "Market Identity",

        "lat":
            "Latitude",

        "lon":
            "Longitude",

        "market_fee_pct":
            "Market Charges",

        "day_of_year":
            "Season / Day",

        "month":
            "Month",

        "price_lag_1":
            "Previous-Day Price",

        "price_lag_3":
            "3-Day Lag Price",

        "price_lag_7":
            "7-Day Lag Price",

        "rolling_price_3":
            "3-Day Average Price",

        "rolling_price_7":
            "7-Day Average Price",

        "arrival_lag_1":
            "Previous Arrivals",

        "arrival_mean_3":
            "3-Day Average Arrivals",

        "arrival_change":
            "Arrival Change",

        "temperature_c":
            "Temperature",

        "rainfall_mm":
            "Rainfall",

        "demand_index":
            "Demand Index",
    }

    selected_model = (
        model_bundle[
            "selected_model"
        ]
    )

    # =====================================================
    # LIGHTGBM FEATURE IMPORTANCE
    # =====================================================

    if selected_model == "LIGHTGBM":

        raw_importance = (

            model_bundle[
                "lightgbm_model"
            ].feature_importance(
                importance_type="gain"
            )
        )

        values = {

            feature:
                float(value)

            for feature, value

            in zip(
                FEATURES,
                raw_importance
            )
        }

    # =====================================================
    # XGBOOST / ENSEMBLE EXPLANATION
    # =====================================================

    else:

        raw_importance = (

            model_bundle[
                "xgb_model"
            ].get_score(
                importance_type="gain"
            )
        )

        values = {

            feature:
                float(
                    raw_importance.get(
                        feature,
                        0
                    )
                )

            for feature
            in FEATURES
        }

    total_importance = (
        sum(
            values.values()
        )
        or
        1
    )

    result = []

    for feature, value in values.items():

        percentage = (

            value

            /
            total_importance

            *
            100
        )

        result.append({

            "feature":
                readable_names[
                    feature
                ],

            "importance":
                round(
                    percentage,
                    1
                ),
        })

    result.sort(

        key=lambda item:
            item["importance"],

        reverse=True
    )

    return result[:8]


# =========================================================
# FORECAST ONE MARKET
# =========================================================

def forecast_market(
    crop,
    market_id
):

    model_bundle = train_crop_models(
        crop
    )

    raw_data = (
        model_bundle[
            "raw"
        ]
    )

    market_data = (

        raw_data[
            raw_data[
                "market_id"
            ]
            ==
            market_id
        ]

        .sort_values(
            "price_date"
        )

        .copy()
    )

    if len(market_data) < 10:

        raise ValueError(
            "Not enough market history."
        )

    latest_row = (
        market_data.iloc[-1]
    )

    prices = [

        float(value)

        for value in
        market_data[
            "modal_price"
        ].tolist()
    ]

    arrivals = [

        float(value)

        for value in
        market_data[
            "arrivals_qtl"
        ].tolist()
    ]

    temperatures = [

        float(value)

        for value in
        market_data[
            "temperature_c"
        ].tolist()
    ]

    rainfall = [

        float(value)

        for value in
        market_data[
            "rainfall_mm"
        ].tolist()
    ]

    demand = [

        float(value)

        for value in
        market_data[
            "demand_index"
        ].tolist()
    ]

    latest_date = pd.Timestamp(

        market_data[
            "price_date"
        ].max()
    )

    # Recursive future prediction arrays

    predicted_prices = (
        prices.copy()
    )

    future_arrivals = (
        arrivals.copy()
    )

    future_temperature = (
        temperatures.copy()
    )

    future_rainfall = (
        rainfall.copy()
    )

    future_demand = (
        demand.copy()
    )

    forecast_results = []

    # =====================================================
    # GENERATE DAY 1 → DAY 7
    # =====================================================

    for day in range(
        1,
        8
    ):

        future_date = (

            latest_date

            +
            pd.Timedelta(
                days=day
            )
        )

        feature_row = {

            "market_id":
                float(
                    market_id
                ),

            "lat":
                float(
                    latest_row[
                        "lat"
                    ]
                ),

            "lon":
                float(
                    latest_row[
                        "lon"
                    ]
                ),

            "market_fee_pct":
                float(
                    latest_row[
                        "market_fee_pct"
                    ]
                ),

            "day_of_year":
                float(
                    future_date.dayofyear
                ),

            "month":
                float(
                    future_date.month
                ),

            "price_lag_1":
                predicted_prices[-1],

            "price_lag_3":
                predicted_prices[-3],

            "price_lag_7":
                predicted_prices[-7],

            "rolling_price_3":
                float(
                    np.mean(
                        predicted_prices[-3:]
                    )
                ),

            "rolling_price_7":
                float(
                    np.mean(
                        predicted_prices[-7:]
                    )
                ),

            "arrival_lag_1":
                future_arrivals[-1],

            "arrival_mean_3":
                float(
                    np.mean(
                        future_arrivals[-3:]
                    )
                ),

            "arrival_change":
                future_arrivals[-1]
                -
                future_arrivals[-2],

            "temperature_c":
                float(
                    np.mean(
                        future_temperature[-3:]
                    )
                ),

            "rainfall_mm":
                float(
                    np.mean(
                        future_rainfall[-3:]
                    )
                ),

            "demand_index":
                float(
                    np.mean(
                        future_demand[-3:]
                    )
                ),
        }

        (
            xgb_price,
            lightgbm_price,
            final_price

        ) = predict_single_row(

            model_bundle,

            feature_row
        )

        # Add recursive future values

        predicted_prices.append(
            final_price
        )

        future_arrivals.append(

            float(
                np.mean(
                    future_arrivals[-3:]
                )
            )
        )

        future_temperature.append(

            float(
                np.mean(
                    future_temperature[-3:]
                )
            )
        )

        future_rainfall.append(

            float(
                np.mean(
                    future_rainfall[-3:]
                )
            )
        )

        future_demand.append(

            float(
                np.mean(
                    future_demand[-3:]
                )
            )
        )

        # Only show 1 / 3 / 7 day forecasts

        if day in (
            1,
            3,
            7
        ):

            predictability = (
                calculate_predictability_score(

                    model_bundle,

                    prices[-30:],

                    xgb_price,

                    lightgbm_price,

                    day,

                    len(
                        market_data
                    )
                )
            )

            # Confidence band

            recent_volatility = float(

                np.std(
                    prices[-7:]
                )
            )

            model_difference = abs(

                xgb_price
                -
                lightgbm_price
            )

            uncertainty = max(

                20,

                recent_volatility
                *
                0.65,

                model_difference
            )

            forecast_results.append({

                "day":
                    day,

                "date":
                    future_date.strftime(
                        "%d %b"
                    ),

                "xgboost_price":
                    round(
                        xgb_price,
                        2
                    ),

                "lightgbm_price":
                    round(
                        lightgbm_price,
                        2
                    ),

                "predicted_price":
                    round(
                        final_price,
                        2
                    ),

                "lower":
                    round(
                        final_price
                        -
                        uncertainty,
                        2
                    ),

                "upper":
                    round(
                        final_price
                        +
                        uncertainty,
                        2
                    ),

                "predictability":
                    predictability,
            })

    # =====================================================
    # FEATURE IMPORTANCE
    # =====================================================

    feature_importance = (
        get_feature_importance(
            model_bundle
        )
    )

    explanation_features = [

        item["feature"].lower()

        for item in
        feature_importance[:3]
    ]

    explanation = (

        "The forecast is mainly influenced by "

        +
        ", ".join(
            explanation_features
        )

        +
        "."
    )

    # =====================================================
    # HISTORICAL GRAPH DATA
    # =====================================================

    history = []

    for _, row in (

        market_data
        .tail(12)
        .iterrows()
    ):

        history.append({

            "date":
                pd.Timestamp(
                    row[
                        "price_date"
                    ]
                ).strftime(
                    "%d %b"
                ),

            "price":
                round(
                    float(
                        row[
                            "modal_price"
                        ]
                    ),
                    2
                ),

            "arrivals":
                round(
                    float(
                        row[
                            "arrivals_qtl"
                        ]
                    ),
                    1
                ),
        })

    return {

        "crop":
            crop,

        "market": {

            "id":
                int(
                    market_id
                ),

            "name":
                str(
                    latest_row[
                        "name"
                    ]
                ),

            "city":
                str(
                    latest_row[
                        "city"
                    ]
                ),

            "state":
                str(
                    latest_row[
                        "state"
                    ]
                ),

            "lat":
                float(
                    latest_row[
                        "lat"
                    ]
                ),

            "lon":
                float(
                    latest_row[
                        "lon"
                    ]
                ),

            "market_fee_pct":
                float(
                    latest_row[
                        "market_fee_pct"
                    ]
                ),
        },

        "current_price":
            round(
                prices[-1],
                2
            ),

        "history":
            history,

        "forecasts":
            forecast_results,

        "selected_model":
            model_bundle[
                "selected_model"
            ],

        "metrics": {

            "XGBoost":
                model_bundle[
                    "xgb_metrics"
                ],

            "LightGBM":
                model_bundle[
                    "lightgbm_metrics"
                ],
        },

        "feature_importance":
            feature_importance,

        "explanation":
            explanation,
    }


# =========================================================
# MULTI-MARKET COMPARISON
# =========================================================

COMPARE_NEAREST_MARKETS = 60


def nearest_market_ids(market_ids, origin_lat, origin_lon, limit):
    """Return up to `limit` of market_ids, closest to the origin first."""
    connection = get_connection()
    rows = connection.execute(
        "SELECT id, lat, lon FROM markets"
    ).fetchall()
    connection.close()

    wanted = set(market_ids)
    lat0 = math.radians(origin_lat)

    def squared_distance(row):
        # Equirectangular approximation; only the ordering matters here.
        dx = math.radians(row["lon"] - origin_lon) * math.cos(lat0)
        dy = math.radians(row["lat"] - origin_lat)
        return dx * dx + dy * dy

    ranked = sorted(
        (r for r in rows
         if r["id"] in wanted and r["lat"] is not None and r["lon"] is not None),
        key=squared_distance
    )
    return [int(r["id"]) for r in ranked[:limit]]


def compare_markets(

    crop,

    quantity_qtl,

    origin_lat,

    origin_lon,

    horizon=7
):

    if horizon not in (
        1,
        3,
        7
    ):

        horizon = 7

    # Train ONCE and cache
    model_bundle = train_crop_models(
        crop
    )

    raw_data = (
        model_bundle[
            "raw"
        ]
    )

    market_ids = sorted(

        set(

            int(value)

            for value in
            raw_data[
                "market_id"
            ].unique()
        )
    )

    # Forecasting every market is slow now that Tamil Nadu alone has 300+.
    # Far markets lose on transport cost anyway, so compare the nearest ones.
    market_ids = nearest_market_ids(
        market_ids,
        origin_lat,
        origin_lon,
        limit=COMPARE_NEAREST_MARKETS
    )

    results = []

    # =====================================================
    # COMPARE ALL MARKETS
    # =====================================================

    for market_id in market_ids:

        try:

            market_forecast = (
                forecast_market(

                    crop,

                    market_id
                )
            )

        except Exception:

            continue

        target_forecast = next(

            (

                item

                for item
                in market_forecast[
                    "forecasts"
                ]

                if item[
                    "day"
                ]
                ==
                horizon
            ),

            None
        )

        if not target_forecast:

            continue

        market = (
            market_forecast[
                "market"
            ]
        )

        # =====================================================
        # DISTANCE
        # =====================================================

        latitude = (
            market["lat"]
        )

        longitude = (
            market["lon"]
        )

        distance_km = (

            111

            *
            math.sqrt(

                (
                    origin_lat
                    -
                    latitude
                ) ** 2

                +

                (

                    (
                        origin_lon
                        -
                        longitude
                    )

                    *
                    math.cos(
                        math.radians(
                            origin_lat
                        )
                    )

                ) ** 2
            )
        )

        # =====================================================
        # TRANSPORT COST
        #
        # Demo prototype rate
        # =====================================================

        transport_cost = max(

            120,

            distance_km
            *
            18.5
        )

        predicted_price = (

            target_forecast[
                "predicted_price"
            ]
        )

        # =====================================================
        # GROSS FARMER VALUE
        # =====================================================

        gross_value = (

            predicted_price

            *
            quantity_qtl
        )

        # =====================================================
        # MARKET CHARGES
        # =====================================================

        market_charges = (

            gross_value

            *
            (
                market[
                    "market_fee_pct"
                ]
                /
                100
            )
        )

        # =====================================================
        # NET REALIZABLE PRICE / INCOME
        # =====================================================

        net_realizable = (

            gross_value

            -
            transport_cost

            -
            market_charges
        )

        # =====================================================
        # CURRENT MARKET VALUE
        # =====================================================

        current_gross = (

            market_forecast[
                "current_price"
            ]

            *
            quantity_qtl
        )

        current_market_charges = (

            current_gross

            *
            (
                market[
                    "market_fee_pct"
                ]
                /
                100
            )
        )

        current_net = (

            current_gross

            -
            transport_cost

            -
            current_market_charges
        )

        expected_gain = (

            net_realizable

            -
            current_net
        )

        results.append({

            "market_id":
                market_id,

            "market":
                market[
                    "name"
                ],

            "state":
                market[
                    "state"
                ],

            "distance_km":
                round(
                    distance_km,
                    1
                ),

            "current_price":
                market_forecast[
                    "current_price"
                ],

            "predicted_price":
                predicted_price,

            "predictability_score":
                target_forecast[
                    "predictability"
                ]["score"],

            "predictability_level":
                target_forecast[
                    "predictability"
                ]["level"],

            "transport_cost":
                round(
                    transport_cost,
                    2
                ),

            "market_charges":
                round(
                    market_charges,
                    2
                ),

            "gross_value":
                round(
                    gross_value,
                    2
                ),

            "net_realizable":
                round(
                    net_realizable,
                    2
                ),

            "expected_gain_vs_current":
                round(
                    expected_gain,
                    2
                ),

            "action":
                "SHIFT MARKET",
        })

    # =====================================================
    # RANK BY NET FARMER INCOME
    # =====================================================

    results.sort(

        key=lambda item:
            item[
                "net_realizable"
            ],

        reverse=True
    )

    # =====================================================
    # FARMER RECOMMENDATION
    # =====================================================

    if results:

        best_market = (
            results[0]
        )

        gain_threshold = max(

            500,

            best_market[
                "net_realizable"
            ]
            *
            0.02
        )

        # Best market
        if (

            best_market[
                "expected_gain_vs_current"
            ]
            >
            gain_threshold

            and

            best_market[
                "predictability_score"
            ]
            >=
            70
        ):

            best_market[
                "action"
            ] = "WAIT"

        else:

            best_market[
                "action"
            ] = "SELL NOW"

        # Other markets
        for index in range(
            1,
            len(results)
        ):

            results[index][
                "action"
            ] = "SHIFT MARKET"

    # Only return top 12
    return results[:12]


# =========================================================
# OPTIONAL CACHE MANAGEMENT
# =========================================================

def clear_model_cache():

    MODEL_CACHE.clear()


def cached_crops():

    return list(
        MODEL_CACHE.keys()
    )