"""
visualizations.py
------------------
Reusable matplotlib plotting functions. Replaces the seven copy-pasted
plotting blocks from the original notebook with one parameterized function.
"""

import matplotlib.pyplot as plt
import seaborn as sns

EVENTS = {
    2015: "2015 Earthquake",
    2020: "COVID-19",
}


def plot_indicator(df, column, title, ylabel, show_events=True, kind="line"):
    """Single-indicator time series, optionally with earthquake/COVID markers."""
    plt.figure(figsize=(10, 5))
    data = df[["Year", column]].dropna()

    if kind == "scatter":
        plt.scatter(data["Year"], data[column], s=80)
    else:
        plt.plot(data["Year"], data[column], marker="o")

    if show_events and not data.empty:
        for year, label in EVENTS.items():
            if data["Year"].min() <= year <= data["Year"].max():
                plt.axvline(year, color="gray", linestyle="--", alpha=0.6)
                plt.text(year, data[column].max(), label, rotation=90,
                          va="top", fontsize=8, color="gray")

    plt.title(title)
    plt.xlabel("Year")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.4)
    plt.tight_layout()
    plt.show()


def plot_regional_comparison(df, column, country_map, title, ylabel):
    """Same indicator, multiple countries, one chart -- for the peer comparison."""
    plt.figure(figsize=(10, 5))
    for code, name in country_map.items():
        subset = df[df["Country Code"] == code].dropna(subset=[column])
        plt.plot(subset["Year"], subset[column], marker="o", label=name)
    plt.title(title)
    plt.xlabel("Year")
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid(True, alpha=0.4)
    plt.tight_layout()
    plt.show()


def plot_correlation_heatmap(corr_df, title):
    plt.figure(figsize=(9, 7))
    sns.heatmap(corr_df, annot=True, fmt=".2f", cmap="coolwarm", center=0,
                linewidths=0.5, square=True)
    plt.title(title)
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.show()


def plot_combined_dashboard(df, indicator_specs, suptitle):
    """
    indicator_specs: list of (column, subplot_title, ylabel) tuples, max 6,
    laid out in a 3x2 grid -- the original notebook's combined figure, generalized.
    """
    fig, axes = plt.subplots(3, 2, figsize=(15, 14))
    for ax, (col, subtitle, ylabel) in zip(axes.flat, indicator_specs):
        data = df[["Year", col]].dropna()
        ax.plot(data["Year"], data[col])
        ax.set_title(subtitle)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Year")
        ax.grid(True)
    plt.suptitle(suptitle, fontsize=18)
    plt.tight_layout()
    plt.show()
