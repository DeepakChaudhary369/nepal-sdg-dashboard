
"""
dashboard_app.py
----------------
Interactive Streamlit dashboard for Nepal SDG data.

Run:

    streamlit run dashboard_app.py

Before running, generate the CSV files using:

    python data_pipeline.py
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st

from sdg_analysis import (
    SDG_TARGETS,
    compute_change_summary,
    interpolate_indicators,
    missing_data_summary,
    sdg_target_gap,
    yoy_change,
    yoy_change_correlation,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(
    os.path.dirname(__file__),
    "data"
)

st.set_page_config(
    page_title="Nepal SDG Dashboard",
    page_icon="🇳🇵",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

@st.cache_data
def load_data():

    nepal_path = os.path.join(
        DATA_DIR,
        "nepal_sdg_data.csv"
    )

    regional_path = os.path.join(
        DATA_DIR,
        "regional_comparison.csv"
    )

    if not os.path.exists(nepal_path):
        raise FileNotFoundError(
            "nepal_sdg_data.csv not found. "
            "Run: python data_pipeline.py"
        )

    if not os.path.exists(regional_path):
        raise FileNotFoundError(
            "regional_comparison.csv not found. "
            "Run: python data_pipeline.py"
        )

    nepal = pd.read_csv(
        nepal_path
    )

    regional = pd.read_csv(
        regional_path
    )

    return nepal, regional


nepal_raw, regional = load_data()


# ---------------------------------------------------------------------------
# Indicator configuration
# ---------------------------------------------------------------------------

CORE_INDICATORS = [
    "GDP_per_capita",
    "Life_expectancy",
    "Unemployment",
    "Electricity_access",
    "CO2_per_capita",
    "Internet_usage",
    "Poverty_rate",
]

ADDITIONAL_INDICATORS = [
    "Remittances_pct_GDP",
    "Tourism_receipts_USD",
    "Literacy_rate",
    "Maternal_mortality",
    "Gini_index",
]

INTERPOLATE_COLS = [
    "Life_expectancy",
    "Electricity_access",
    "Internet_usage",
    "CO2_per_capita",
]


DISPLAY_NAMES = {
    "GDP_per_capita": "GDP per capita",
    "Life_expectancy": "Life expectancy",
    "Unemployment": "Unemployment",
    "Electricity_access": "Electricity access",
    "CO2_per_capita": "CO₂ per capita",
    "Internet_usage": "Internet usage",
    "Poverty_rate": "Poverty rate",
    "Remittances_pct_GDP": "Remittances (% GDP)",
    "Tourism_receipts_USD": "Tourism receipts",
    "Literacy_rate": "Literacy rate",
    "Maternal_mortality": "Maternal mortality",
    "Gini_index": "Gini index",
}


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("🇳🇵 Nepal SDG Dashboard")

year_min = int(
    nepal_raw["Year"].min()
)

year_max = int(
    nepal_raw["Year"].max()
)

year_range = st.sidebar.slider(
    "Year range",
    min_value=year_min,
    max_value=year_max,
    value=(year_min, year_max),
)

indicator_group = st.sidebar.radio(
    "Indicator group",
    [
        "Core SDG indicators",
        "Additional Nepal indicators",
    ],
)

if indicator_group == "Core SDG indicators":
    indicator_options = CORE_INDICATORS
else:
    indicator_options = [
        col
        for col in ADDITIONAL_INDICATORS
        if col in nepal_raw.columns
    ]


indicator = st.sidebar.selectbox(
    "Indicator",
    indicator_options,
)

view_mode = st.sidebar.radio(
    "View",
    [
        "Raw values",
        "Year-over-year % change",
        "SDG target progress",
    ],
)

fill_gaps = st.sidebar.checkbox(
    "Interpolate internal gaps for structural indicators",
    value=False,
    help=(
        "Only gaps between two known observations are "
        "interpolated. Edge values are not extrapolated."
    ),
)

compare_region = st.sidebar.checkbox(
    "Compare against regional peers",
    value=False,
)


# ---------------------------------------------------------------------------
# Prepare data
# ---------------------------------------------------------------------------

if fill_gaps:

    nepal = interpolate_indicators(
        nepal_raw,
        INTERPOLATE_COLS
    )

else:

    nepal = nepal_raw.copy()


nepal_filtered = nepal[
    (nepal["Year"] >= year_range[0])
    &
    (nepal["Year"] <= year_range[1])
].copy()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title(
    f"🇳🇵 Nepal Sustainable Development Dashboard "
    f"({year_min}–{year_max})"
)

st.caption(
    "Source: World Bank indicators | "
    f"Coverage: {year_min}–{year_max}"
)


# ---------------------------------------------------------------------------
# KPI cards
# ---------------------------------------------------------------------------

st.subheader("Current indicator snapshot")

latest_rows = []

for col in CORE_INDICATORS:

    if col not in nepal.columns:
        continue

    available = (
        nepal[["Year", col]]
        .dropna()
        .sort_values("Year")
    )

    if available.empty:
        continue

    latest = available.iloc[-1]

    latest_rows.append({
        "indicator": col,
        "value": latest[col],
        "year": int(latest["Year"]),
    })


kpi_columns = st.columns(4)

for index, item in enumerate(
    latest_rows[:4]
):

    col = kpi_columns[index]

    indicator_name = DISPLAY_NAMES.get(
        item["indicator"],
        item["indicator"]
    )

    value = item["value"]

    if item["indicator"] in [
        "GDP_per_capita",
        "Tourism_receipts_USD",
    ]:

        formatted_value = f"${value:,.0f}"

    elif item["indicator"] in [
        "Life_expectancy"
    ]:

        formatted_value = f"{value:.1f}"

    else:

        formatted_value = f"{value:.1f}"

    col.metric(
        indicator_name,
        formatted_value,
        f"{item['year']}"
    )


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

st.divider()

st.subheader(
    f"{DISPLAY_NAMES.get(indicator, indicator)}"
)


# ---------------------------------------------------------------------------
# Raw values
# ---------------------------------------------------------------------------

if view_mode == "Raw values":

    if (
        compare_region
        and indicator in regional.columns
    ):

        regional_filtered = regional[
            (regional["Year"] >= year_range[0])
            &
            (regional["Year"] <= year_range[1])
        ].copy()

        fig = px.line(
            regional_filtered.dropna(
                subset=[indicator]
            ),
            x="Year",
            y=indicator,
            color="Country",
            markers=True,
            title=(
                f"{DISPLAY_NAMES.get(indicator, indicator)} "
                f"— Nepal vs Regional Peers"
            ),
        )

    else:

        chart_data = nepal_filtered.dropna(
            subset=[indicator]
        )

        fig = px.line(
            chart_data,
            x="Year",
            y=indicator,
            markers=True,
            title=(
                f"Nepal — "
                f"{DISPLAY_NAMES.get(indicator, indicator)}"
            ),
        )

        # Historical context markers.
        events = {
            2015: "2015 Nepal earthquake",
            2020: "COVID-19 period",
        }

        for year, label in events.items():

            if (
                year_range[0]
                <= year
                <= year_range[1]
            ):

                fig.add_vline(
                    x=year,
                    line_dash="dash",
                    line_color="gray",
                )

                fig.add_annotation(
                    x=year,
                    y=1,
                    yref="paper",
                    text=label,
                    showarrow=False,
                    textangle=-90,
                )

    fig.update_layout(
        xaxis_title="Year",
        yaxis_title=DISPLAY_NAMES.get(
            indicator,
            indicator
        ),
        hovermode="x unified",
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ---------------------------------------------------------------------------
# YoY changes
# ---------------------------------------------------------------------------

elif view_mode == "Year-over-year % change":

    yoy = yoy_change(
        nepal_filtered,
        [indicator]
    ).reset_index()

    yoy = yoy.dropna(
        subset=[indicator]
    )

    fig = px.bar(
        yoy,
        x="Year",
        y=indicator,
        title=(
            f"{DISPLAY_NAMES.get(indicator, indicator)} "
            f"— Genuine Year-over-Year % Change"
        ),
    )

    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="Change (%)",
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.info(
        "YoY change is only calculated when consecutive "
        "calendar years are available. Multi-year gaps "
        "are not treated as year-over-year changes."
    )


# ---------------------------------------------------------------------------
# SDG target progress
# ---------------------------------------------------------------------------

elif view_mode == "SDG target progress":

    gap_table = sdg_target_gap(
        nepal_filtered
    )

    display_table = gap_table.copy()

    if not display_table.empty:

        display_table["Indicator"] = (
            display_table["Indicator"]
            .map(
                lambda x:
                DISPLAY_NAMES.get(x, x)
            )
        )

    st.dataframe(
        display_table,
        use_container_width=True,
        hide_index=True,
    )

    row = gap_table[
        gap_table["Indicator"] == indicator
    ]

    if not row.empty:

        record = row.iloc[0]

        target = record["2030 Target"]
        progress = record[
            "Progress toward Target (%)"
        ]

        if pd.notna(target):

            st.metric(
                label=(
                    f"{DISPLAY_NAMES.get(indicator, indicator)} "
                    f"— Progress toward 2030 target"
                ),
                value=f"{progress:.1f}%",
            )

            st.caption(
                f"Direction: {record['Direction']} is better. "
                f"Latest value: {record['Latest Value']:.2f}; "
                f"Target: {target:.2f}."
            )

            st.caption(
                f"Note: {record['Note']}"
            )

        else:

            st.info(
                "No single numeric 2030 target is defined "
                "for this indicator in the project's target mapping."
            )


# ---------------------------------------------------------------------------
# Regional comparison
# ---------------------------------------------------------------------------

st.divider()

st.subheader("Regional comparison")

regional_indicator_options = [
    col
    for col in CORE_INDICATORS
    if col in regional.columns
]

regional_indicator = st.selectbox(
    "Choose indicator for regional comparison",
    regional_indicator_options,
    format_func=lambda x:
        DISPLAY_NAMES.get(x, x),
)

regional_filtered = regional[
    (regional["Year"] >= year_range[0])
    &
    (regional["Year"] <= year_range[1])
].copy()

regional_chart = px.line(
    regional_filtered.dropna(
        subset=[regional_indicator]
    ),
    x="Year",
    y=regional_indicator,
    color="Country",
    markers=True,
    title=(
        f"{DISPLAY_NAMES.get(regional_indicator, regional_indicator)} "
        "— Nepal and Regional Peers"
    ),
)

regional_chart.update_layout(
    xaxis_title="Year",
    yaxis_title=DISPLAY_NAMES.get(
        regional_indicator,
        regional_indicator
    ),
    hovermode="x unified",
)

st.plotly_chart(
    regional_chart,
    use_container_width=True
)


# ---------------------------------------------------------------------------
# Data completeness
# ---------------------------------------------------------------------------

st.divider()

col1, col2 = st.columns(2)

with col1:

    st.subheader(
        "Data completeness"
    )

    completeness = missing_data_summary(
        nepal_filtered,
        CORE_INDICATORS
    )

    st.dataframe(
        completeness,
        use_container_width=True,
        hide_index=True,
    )

with col2:

    st.subheader(
        "First-to-last change"
    )

    change_summary = compute_change_summary(
        nepal_filtered,
        CORE_INDICATORS
    )

    st.dataframe(
        change_summary,
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------------------------
# Completeness chart
# ---------------------------------------------------------------------------

st.subheader(
    "Indicator completeness"
)

if not completeness.empty:

    completeness_chart = px.bar(
        completeness,
        x="Indicator",
        y="Completeness (%)",
        text="Completeness (%)",
        title="Available observations by indicator",
    )

    completeness_chart.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside",
    )

    completeness_chart.update_layout(
        yaxis_range=[0, 105],
        xaxis_title="Indicator",
        yaxis_title="Completeness (%)",
    )

    st.plotly_chart(
        completeness_chart,
        use_container_width=True
    )


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------

st.divider()

st.subheader(
    "Correlation of year-over-year percentage changes"
)

main_cols = [
    "GDP_per_capita",
    "Life_expectancy",
    "Unemployment",
    "Electricity_access",
    "Internet_usage",
]

yoy_corr = yoy_change_correlation(
    nepal_filtered,
    main_cols,
    min_overlap=10,
)

if not yoy_corr.empty:

    corr_fig = px.imshow(
        yoy_corr,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        aspect="auto",
        title=(
            "Correlation matrix — "
            "year-over-year percentage changes"
        ),
    )

    st.plotly_chart(
        corr_fig,
        use_container_width=True
    )

st.caption(
    "Correlation describes association between annual changes; "
    "it does not establish causation."
)


# ---------------------------------------------------------------------------
# Methodology
# ---------------------------------------------------------------------------

with st.expander(
    "⚠️ Methodology and limitations"
):

    st.markdown(
        """
### Data source

World Bank indicators covering Nepal from 2000 onward.

### Missing data

Only selected slow-moving structural indicators are
interpolated, and only for gaps between known observations.
Sparse survey-based indicators such as poverty are not
interpolated.

### SDG targets

Some Nepal national SDG targets use definitions that differ
from the corresponding World Bank indicators. Therefore,
target progress should be interpreted as directional rather
than as an exact measurement of official SDG performance.

### Correlation

The dashboard uses year-over-year percentage changes rather
than raw levels. This reduces the influence of common long-term
time trends.

Correlation does not imply causation.

### Historical events

The 2015 earthquake and 2020 COVID-19 period are shown as
contextual markers. Their presence on the chart does not mean
that the event alone caused a particular indicator change.
        """
    )


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

st.divider()

st.download_button(
    "Download filtered Nepal data as CSV",
    data=nepal_filtered.to_csv(
        index=False
    ),
    file_name=(
        "nepal_sdg_filtered.csv"
    ),
    mime="text/csv",
)

