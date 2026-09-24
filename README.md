# Nepal SDG Data Analytics Dashboard

Tracks Nepal's progress on Sustainable Development Goal indicators (2000–2024),
benchmarks it against regional peers, and surfaces the gap to Nepal's own 2030
national targets — as an interactive dashboard rather than a static notebook.

## Project structure

```
nepal_sdg_project/
├── data_pipeline.py       # Pulls World Bank indicators directly via API (wbgapi)
├── sdg_analysis.py        # Cleaning, interpolation, SDG target-gap, corrected correlation
├── visualizations.py      # Reusable matplotlib plotting functions (for notebook use)
├── dashboard_app.py       # Interactive Streamlit dashboard
├── requirements.txt
├── data/                  # Generated CSVs (created by data_pipeline.py)
└── README.md
```

## How to run it

```bash
pip install -r requirements.txt

# 1. Fetch the data (replaces manual zip download + Colab upload)
python data_pipeline.py

# 2. Launch the dashboard
streamlit run dashboard_app.py
```

If you'd rather work in a notebook first (e.g. to write up the analysis
narrative), import from the same modules instead of duplicating logic:

```python
from sdg_analysis import sdg_target_gap, yoy_change_correlation, interpolate_indicators
from visualizations import plot_indicator, plot_regional_comparison
import pandas as pd

nepal = pd.read_csv("data/nepal_sdg_data.csv")
plot_indicator(nepal, "GDP_per_capita", "Nepal GDP per Capita", "US$")
```

## What changed from the original notebook

- **Data pipeline**: manual zip-file upload replaced with a direct World Bank
  API pull (`data_pipeline.py`), and extended with regional peers (Bangladesh,
  Bhutan, India) and Nepal-specific indicators (remittances, tourism receipts,
  literacy, maternal mortality, Gini index).
- **SDG framing**: each indicator is now mapped to its SDG goal and compared
  against Nepal's own 2030 national target (`sdg_analysis.sdg_target_gap`).
  See the caveat in `sdg_analysis.py` about definitional differences between
  national targets and World Bank series.
- **Correlation**: computed on year-over-year % change instead of raw levels,
  since raw levels mostly share a common time trend
  (`sdg_analysis.yoy_change_correlation`), and raw-level pairs with fewer than
  10 overlapping observations are blanked out rather than reported as if
  reliable (`sdg_analysis.level_correlation`).
- **Missing data**: interpolated for slow-moving structural indicators only
  (life expectancy, electricity, internet, CO2); poverty is left as sparse
  survey-year points rather than interpolated, since survey rounds are 5–8
  years apart.
- **Visualization**: seven copy-pasted matplotlib blocks consolidated into one
  reusable function with earthquake (2015) / COVID-19 (2020) annotations
  (`visualizations.plot_indicator`); the dashboard itself uses Plotly for
  interactivity (hover, zoom, year-range filtering).
- **Structure**: one long notebook split into a pipeline, an analysis module,
  a plotting module, and the dashboard — each independently testable and
  reusable.

## Known limitations to mention in your write-up

- SDG targets sourced from Nepal's national plans may not match the exact
  indicator definition used by the World Bank series being tracked.
- CO2 and GDP per capita have no single clean numeric 2030 target, so they're
  tracked but not scored against a target.
- Poverty data is sparse (survey years only) — treat any trend line through it
  as illustrative, not a fitted trend.
