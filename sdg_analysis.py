
"""
sdg_analysis.py
---------------
Statistical, cleaning, validation, and SDG-target analysis logic.

This module is kept separate from the Streamlit application so that
the analytical functions can be tested and reused.
"""

import pandas as pd


# ---------------------------------------------------------------------------
# SDG target mapping
# ---------------------------------------------------------------------------
#
# IMPORTANT:
# "direction" tells us whether a higher or lower value represents progress.
#
# higher = higher value is better
# lower  = lower value is better
#
# Some national SDG targets use definitions that differ from the
# corresponding World Bank indicators. Therefore, target progress should
# be treated as directional rather than exact where definitions differ.
# ---------------------------------------------------------------------------

SDG_TARGETS = {
    "GDP_per_capita": {
        "sdg": "SDG 8",
        "target": None,
        "direction": None,
        "note": "No single numeric 2030 target; growth-rate based.",
    },

    "Life_expectancy": {
        "sdg": "SDG 3",
        "target": 73.0,
        "direction": "higher",
        "note": "National periodic plan target.",
    },

    "Unemployment": {
        "sdg": "SDG 8",
        "target": 5.0,
        "direction": "lower",
        "note": "National target; definition may differ from World Bank series.",
    },

    "Electricity_access": {
        "sdg": "SDG 7",
        "target": 100.0,
        "direction": "higher",
        "note": "Universal access goal.",
    },

    "CO2_per_capita": {
        "sdg": "SDG 13",
        "target": None,
        "direction": "lower",
        "note": "No single numeric 2030 ceiling used here.",
    },

    "Internet_usage": {
        "sdg": "SDG 9",
        "target": 90.0,
        "direction": "higher",
        "note": "National periodic plan target.",
    },

    "Poverty_rate": {
        "sdg": "SDG 1",
        "target": 5.0,
        "direction": "lower",
        "note": (
            "National poverty-line definition; not directly equivalent "
            "to the World Bank $-per-day poverty indicator."
        ),
    },
}


# ---------------------------------------------------------------------------
# Data quality
# ---------------------------------------------------------------------------

def check_data_quality(df: pd.DataFrame, value_columns: list) -> dict:
    """
    Check duplicate Country-Year rows, data types, negative values,
    and basic year validity.
    """

    report = {
        "duplicate_country_year_rows": int(
            df.duplicated(subset=["Country Code", "Year"]).sum()
        ),

        "invalid_year_rows": int(
            (~pd.to_numeric(df["Year"], errors="coerce").notna()).sum()
        ),

        "dtypes": df[value_columns].dtypes.astype(str).to_dict(),

        "negative_values": {
            col: int((df[col] < 0).sum())
            for col in value_columns
            if col in df
        },
    }

    return report


def validate_required_columns(
    df: pd.DataFrame,
    required_columns: list
) -> None:
    """
    Ensure all expected columns are present.
    """

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )


# ---------------------------------------------------------------------------
# Missing data
# ---------------------------------------------------------------------------

def missing_data_summary(
    df: pd.DataFrame,
    value_columns: list
) -> pd.DataFrame:
    """
    Return available and missing observations for each indicator.
    """

    rows = []

    for col in value_columns:

        if col not in df.columns:
            continue

        total = len(df)

        available = int(df[col].notna().sum())
        missing = int(df[col].isna().sum())

        completeness = (
            available / total * 100
            if total > 0
            else 0
        )

        rows.append({
            "Indicator": col,
            "Available observations": available,
            "Missing observations": missing,
            "Completeness (%)": completeness,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------

def interpolate_indicators(
    df: pd.DataFrame,
    columns_to_interpolate: list
) -> pd.DataFrame:
    """
    Linearly interpolate slow-moving structural indicators.

    Only gaps BETWEEN known observations are filled.

    Missing values before the first observation or after the last
    observation are deliberately NOT extrapolated.

    Sparse survey-based indicators such as poverty are excluded.
    """

    out = df.copy().sort_values("Year")

    for col in columns_to_interpolate:

        if col in out.columns:

            out[col] = (
                out[col]
                .interpolate(
                    method="linear",
                    limit_area="inside"
                )
            )

    return out


# ---------------------------------------------------------------------------
# Change summary
# ---------------------------------------------------------------------------

def compute_change_summary(
    df: pd.DataFrame,
    indicators: list
) -> pd.DataFrame:
    """
    Calculate first-available to last-available change.

    This is NOT necessarily a year-over-year change.
    """

    rows = []

    for col in indicators:

        if col not in df.columns:
            continue

        data = (
            df[["Year", col]]
            .dropna()
            .sort_values("Year")
        )

        if len(data) < 2:
            continue

        first = data.iloc[0]
        last = data.iloc[-1]

        abs_change = last[col] - first[col]

        pct_change = (
            abs_change / first[col] * 100
            if first[col] != 0
            else None
        )

        rows.append({
            "Indicator": col,
            "First Year": int(first["Year"]),
            "First Value": first[col],
            "Last Year": int(last["Year"]),
            "Last Value": last[col],
            "Absolute Change": abs_change,
            "Percentage Change": pct_change,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# SDG target gap
# ---------------------------------------------------------------------------

def sdg_target_gap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare the latest available indicator value with its 2030 target.

    Progress is direction-aware:

    higher-is-better:
        progress = current / target * 100

    lower-is-better:
        progress = target / current * 100

    No numeric target:
        progress is left blank.
    """

    rows = []

    for col, meta in SDG_TARGETS.items():

        if col not in df.columns:
            continue

        data = (
            df[["Year", col]]
            .dropna()
            .sort_values("Year")
        )

        if data.empty:
            continue

        latest = data.iloc[-1]

        year = int(latest["Year"])
        value = float(latest[col])

        target = meta["target"]
        direction = meta["direction"]

        gap = None
        progress = None

        if target is not None:

            if direction == "higher":

                # Positive means the current value is still below target.
                gap = target - value

                if target != 0:
                    progress = value / target * 100

            elif direction == "lower":

                # Positive means the current value is still above target.
                gap = value - target

                if value != 0:
                    progress = target / value * 100

        rows.append({
            "Indicator": col,
            "SDG": meta["sdg"],
            "Latest Year": year,
            "Latest Value": value,
            "2030 Target": target,
            "Direction": direction,
            "Gap to Target": gap,
            "Progress toward Target (%)": progress,
            "Note": meta["note"],
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pairwise observation counts
# ---------------------------------------------------------------------------

def pairwise_observation_counts(
    df: pd.DataFrame,
    columns: list
) -> pd.DataFrame:
    """
    Count overlapping non-null observations for each indicator pair.
    """

    available_columns = [
        col for col in columns
        if col in df.columns
    ]

    mask = (
        df[available_columns]
        .notna()
        .astype(int)
    )

    return mask.T.dot(mask)


# ---------------------------------------------------------------------------
# Raw-level correlation
# ---------------------------------------------------------------------------

def level_correlation(
    df: pd.DataFrame,
    columns: list,
    min_overlap: int = 10
) -> pd.DataFrame:
    """
    Raw-level correlation.

    Pairs with fewer than min_overlap observations are blanked out.
    """

    available_columns = [
        col for col in columns
        if col in df.columns
    ]

    corr = df[available_columns].corr()

    counts = pairwise_observation_counts(
        df,
        available_columns
    )

    return corr.where(counts >= min_overlap)


# ---------------------------------------------------------------------------
# Correct Year-over-Year calculation
# ---------------------------------------------------------------------------

def yoy_change(
    df: pd.DataFrame,
    columns: list
) -> pd.DataFrame:
    """
    Calculate genuine year-over-year percentage changes.

    A change is only calculated when two consecutive observations
    correspond to consecutive calendar years.

    For example:

        2019 -> 2020  = valid YoY

        2019 -> 2022  = NOT treated as YoY
    """

    available_columns = [
        col for col in columns
        if col in df.columns
    ]

    data = (
        df[["Year"] + available_columns]
        .drop_duplicates(subset=["Year"])
        .sort_values("Year")
        .set_index("Year")
    )

    change = data.pct_change() * 100

    year_difference = (
        data.index.to_series()
        .diff()
    )

    # Remove changes where the previous observation
    # was not exactly one year earlier.
    invalid_yoy = year_difference != 1

    change.loc[invalid_yoy, :] = pd.NA

    return change


# ---------------------------------------------------------------------------
# YoY correlation
# ---------------------------------------------------------------------------

def yoy_change_correlation(
    df: pd.DataFrame,
    columns: list,
    min_overlap: int = 10
) -> pd.DataFrame:
    """
    Correlation of genuine year-over-year percentage changes.

    This is preferable to raw-level correlation when the goal is to
    examine whether indicators move together from one year to the next.
    """

    yoy = yoy_change(
        df,
        columns
    )

    corr = yoy.corr()

    counts = yoy.notna().astype(int).T.dot(
        yoy.notna().astype(int)
    )

    return corr.where(
        counts >= min_overlap
    )

