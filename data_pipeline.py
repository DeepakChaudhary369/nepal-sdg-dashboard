
"""
data_pipeline.py
----------------
Fetches Nepal SDG-related indicators directly from the World Bank API.

Produces:

    data/nepal_sdg_data.csv
    data/regional_comparison.csv
"""

import os
from functools import reduce

import pandas as pd
import wbgapi as wb

from sdg_analysis import (
    check_data_quality,
    validate_required_columns,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__),
    "data"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

START_YEAR = 2000
END_YEAR = 2024


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------

INDICATORS = {
    "NY.GDP.PCAP.CD": "GDP_per_capita",
    "SP.DYN.LE00.IN": "Life_expectancy",
    "SL.UEM.TOTL.ZS": "Unemployment",
    "EG.ELC.ACCS.ZS": "Electricity_access",
    "EN.GHG.CO2.PC.CE.AR5": "CO2_per_capita",
    "IT.NET.USER.ZS": "Internet_usage",
    "SI.POV.DDAY": "Poverty_rate",
    "BX.TRF.PWKR.DT.GD.ZS": "Remittances_pct_GDP",
    "ST.INT.RCPT.CD": "Tourism_receipts_USD",
    "SE.ADT.LITR.ZS": "Literacy_rate",
    "SH.STA.MMRT": "Maternal_mortality",
    "SI.POV.GINI": "Gini_index",
}


REGIONAL_INDICATORS = {
    "NY.GDP.PCAP.CD": "GDP_per_capita",
    "SP.DYN.LE00.IN": "Life_expectancy",
    "SL.UEM.TOTL.ZS": "Unemployment",
    "EG.ELC.ACCS.ZS": "Electricity_access",
    "IT.NET.USER.ZS": "Internet_usage",
}


COUNTRIES = {
    "NPL": "Nepal",
    "BGD": "Bangladesh",
    "BTN": "Bhutan",
    "IND": "India",
}


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def fetch_indicator(
    code: str,
    economies,
    column_name: str
) -> pd.DataFrame:
    """
    Fetch one World Bank indicator.

    Returns:
        Country Code
        Year
        Indicator value
    """

    economies_list = (
        [economies]
        if isinstance(economies, str)
        else list(economies)
    )

    try:

        raw = wb.data.DataFrame(
            code,
            economies_list,
            time=range(
                START_YEAR,
                END_YEAR + 1
            ),
            index=["economy", "time"],
            columns="series",
            skipBlanks=True,
            numericTimeKeys=True,
        )

    except Exception as exc:

        raise RuntimeError(
            f"Failed to fetch World Bank indicator "
            f"{code}: {exc}"
        ) from exc

    if raw.empty:
        raise ValueError(
            f"No data returned for indicator {code}"
        )

    df = raw.reset_index()

    df = df.rename(
        columns={
            "economy": "Country Code",
            "time": "Year",
            code: column_name,
        }
    )

    expected_columns = [
        "Country Code",
        "Year",
        column_name,
    ]

    validate_required_columns(
        df,
        expected_columns
    )

    df["Year"] = pd.to_numeric(
        df["Year"],
        errors="coerce"
    )

    df[column_name] = pd.to_numeric(
        df[column_name],
        errors="coerce"
    )

    return df[
        expected_columns
    ]


# ---------------------------------------------------------------------------
# Nepal dataset
# ---------------------------------------------------------------------------

def build_nepal_dataset() -> pd.DataFrame:

    frames = []

    for code, name in INDICATORS.items():

        print(
            f"Fetching Nepal: {name} ({code})..."
        )

        try:

            frame = fetch_indicator(
                code,
                "NPL",
                name
            )

        except (RuntimeError, ValueError) as exc:

            print(
                f"  WARNING: skipping {name} ({code}) — {exc}"
            )
            continue

        frames.append(frame)

    if not frames:
        raise RuntimeError(
            "All Nepal indicator fetches failed — no data to build."
        )

    merged = reduce(
        lambda left, right: pd.merge(
            left,
            right,
            on=["Country Code", "Year"],
            how="outer"
        ),
        frames
    )

    merged["Country Name"] = "Nepal"

    merged = (
        merged
        .sort_values("Year")
        .reset_index(drop=True)
    )

    return merged

# ---------------------------------------------------------------------------
# Regional dataset
# ---------------------------------------------------------------------------

def build_regional_dataset() -> pd.DataFrame:

    frames = []

    for code, name in REGIONAL_INDICATORS.items():

        print(
            f"Fetching regional indicator: "
            f"{name} ({code})..."
        )

        try:

            frame = fetch_indicator(
                code,
                list(COUNTRIES.keys()),
                name
            )

        except (RuntimeError, ValueError) as exc:

            print(
                f"  WARNING: skipping {name} ({code}) — {exc}"
            )
            continue

        frames.append(frame)

    if not frames:
        raise RuntimeError(
            "All regional indicator fetches failed — no data to build."
        )

    merged = reduce(
        lambda left, right: pd.merge(
            left,
            right,
            on=["Country Code", "Year"],
            how="outer"
        ),
        frames
    )

    merged["Country"] = (
        merged["Country Code"]
        .map(COUNTRIES)
    )

    merged = (
        merged
        .sort_values(
            ["Country Code", "Year"]
        )
        .reset_index(drop=True)
    )

    return merged

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_nepal_dataset(
    df: pd.DataFrame
) -> None:

    required = [
        "Country Code",
        "Year",
        "Country Name",
        *INDICATORS.values(),
    ]

    validate_required_columns(
        df,
        required
    )

    report = check_data_quality(
        df,
        list(INDICATORS.values())
    )

    print("\n--- Nepal data quality report ---")
    print(
        f"Duplicate Country-Year rows: "
        f"{report['duplicate_country_year_rows']}"
    )

    print(
        f"Invalid year rows: "
        f"{report['invalid_year_rows']}"
    )

    negative_values = {
        key: value
        for key, value
        in report["negative_values"].items()
        if value > 0
    }

    if negative_values:
        print(
            "Negative values detected:",
            negative_values
        )

    if report["duplicate_country_year_rows"] > 0:

        raise ValueError(
            "Duplicate Country-Year rows detected."
        )


def validate_regional_dataset(
    df: pd.DataFrame
) -> None:

    required = [
        "Country Code",
        "Year",
        "Country",
        *REGIONAL_INDICATORS.values(),
    ]

    validate_required_columns(
        df,
        required
    )

    duplicate_count = int(
        df.duplicated(
            subset=[
                "Country Code",
                "Year"
            ]
        ).sum()
    )

    print("\n--- Regional data quality report ---")
    print(
        f"Duplicate Country-Year rows: "
        f"{duplicate_count}"
    )

    if duplicate_count > 0:

        raise ValueError(
            "Duplicate Country-Year rows detected "
            "in regional dataset."
        )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():

    print("=" * 60)
    print("NEPAL SDG DATA PIPELINE")
    print("=" * 60)

    print("\nFetching Nepal indicators...")

    nepal_df = build_nepal_dataset()

    validate_nepal_dataset(
        nepal_df
    )

    nepal_path = os.path.join(
        OUTPUT_DIR,
        "nepal_sdg_data.csv"
    )

    nepal_df.to_csv(
        nepal_path,
        index=False
    )

    print(
        f"\nSaved Nepal dataset:"
        f"\n{nepal_path}"
        f"\nShape: {nepal_df.shape}"
    )

    print("\nFetching regional indicators...")

    regional_df = build_regional_dataset()

    validate_regional_dataset(
        regional_df
    )

    regional_path = os.path.join(
        OUTPUT_DIR,
        "regional_comparison.csv"
    )

    regional_df.to_csv(
        regional_path,
        index=False
    )

    print(
        f"\nSaved regional dataset:"
        f"\n{regional_path}"
        f"\nShape: {regional_df.shape}"
    )

    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    main()
