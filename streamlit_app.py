import os
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# ==================================================
# 1. PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="BFT System Performance Dashboard",
    page_icon="🚌",
    layout="wide",
)


# ==================================================
# 2. COLOR PALETTE
# ==================================================

BFT_NAVY = "#12355B"
BFT_BLUE = "#2563EB"
BFT_LIGHT_BLUE = "#60A5FA"
BFT_GOLD = "#E3A008"

ON_TIME_GREEN = "#2E8B57"
LATE_RED = "#D64545"

WEEKDAY_BLUE = "#2563EB"
SATURDAY_GOLD = "#E3A008"
SUNDAY_GREEN = "#2E8B57"

REVENUE_MILES_TEAL = "#0F766E"
REVENUE_HOURS_PURPLE = "#7C3AED"
TRIPS_ORANGE = "#EA580C"

TEXT_GRAY = "#6B7280"
GRID_COLOR = "#E5E7EB"
CARD_BORDER = "#E2E8F0"


# ==================================================
# 3. PAGE STYLING
# ==================================================

st.markdown(
    f"""
    <style>
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 3rem;
    }}

    .main-title {{
        color: {BFT_NAVY};
        font-size: 40px;
        font-weight: 800;
        margin-bottom: 3px;
    }}

    .sub-title {{
        color: {TEXT_GRAY};
        font-size: 16px;
        margin-bottom: 24px;
    }}

    .section-title {{
        color: {BFT_NAVY};
        font-size: 25px;
        font-weight: 750;
        margin-top: 26px;
        margin-bottom: 10px;
    }}

    .section-description {{
        color: {TEXT_GRAY};
        font-size: 14px;
        margin-bottom: 12px;
    }}

    div[data-testid="stMetric"] {{
        background-color: white;
        border: 1px solid {CARD_BORDER};
        border-radius: 14px;
        padding: 15px 18px;
        box-shadow: 0 2px 7px rgba(15, 23, 42, 0.05);
    }}

    div[data-testid="stMetricLabel"] {{
        color: {TEXT_GRAY};
        font-size: 14px;
    }}

    div[data-testid="stMetricValue"] {{
        color: {BFT_NAVY};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="main-title">🚌 BFT System Performance Dashboard</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="sub-title">
    Spring 2026 system performance and monthly ridership trends since 2023
    </div>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# 4. LOAD DATA FROM THE GITHUB REPOSITORY
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

SYSTEM_FILE_CANDIDATES = [
    "Summary System(1).csv",
    "Summary System.csv",
    "SYSTEM_SUMMARY_SPRING_2026.csv",
]

TREND_FILE_CANDIDATES = [
    "Ridership Trend from 2023 - Jul 20 2026(1).csv",
    "Ridership Trend from 2023 - Jul 20 2026.csv",
    "RIDERSHIP_TREND_FROM_2023.csv",
]


def find_data_file(candidates):
    """Return the first matching file from the repository's data folder."""
    for filename in candidates:
        path = DATA_DIR / filename
        if path.exists():
            return path

    expected = "\n".join(f"- data/{name}" for name in candidates)
    st.error(
        "A required data file could not be found. Expected one of:\n"
        f"{expected}"
    )
    st.stop()


def standardize_column_names(df):
    """Convert source column names to compact lowercase names."""
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "", regex=False)
        .str.replace("_", "", regex=False)
    )
    return df


@st.cache_data(show_spinner="Loading dashboard data...")
def load_data(system_file_mtime, trend_file_mtime):
    """
    Load CSV files from the repository.

    The modification-time arguments make Streamlit invalidate the cache
    whenever a committed CSV file changes.
    """
    system_path = find_data_file(SYSTEM_FILE_CANDIDATES)
    trend_path = find_data_file(TREND_FILE_CANDIDATES)

    system_df = pd.read_csv(system_path)
    trend_df = pd.read_csv(trend_path)

    return (
        standardize_column_names(system_df),
        standardize_column_names(trend_df),
    )


system_path = find_data_file(SYSTEM_FILE_CANDIDATES)
trend_path = find_data_file(TREND_FILE_CANDIDATES)

system_df, trend_df = load_data(
    system_path.stat().st_mtime_ns,
    trend_path.stat().st_mtime_ns,
)


# ==================================================
# 5. DATA-CLEANING FUNCTIONS
# ==================================================

def clean_numeric(series):
    """Convert text-formatted numbers, commas, percentages, and blanks."""
    cleaned = (
        series.astype("string")
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("$", "", regex=False)
    )

    cleaned = cleaned.replace(
        {
            "": pd.NA,
            "None": pd.NA,
            "none": pd.NA,
            "NULL": pd.NA,
            "null": pd.NA,
            "NaN": pd.NA,
            "nan": pd.NA,
            "<NA>": pd.NA,
        }
    )

    return pd.to_numeric(cleaned, errors="coerce")


def clean_route_labels(series):
    """Convert values such as 1.0 to 1 while preserving 27X and 123S."""
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def create_route_sort(series):
    """Extract the numeric portion of a route label for route ordering."""
    return pd.to_numeric(
        series.astype("string").str.extract(r"(\d+)")[0],
        errors="coerce",
    )


def prepare_system_summary(df):
    """Clean and prepare the system-summary dataset."""
    df = df.copy()

    if "routes" not in df.columns:
        st.error(
            "The system-summary CSV does not contain a 'Routes' column. "
            f"Available columns: {list(df.columns)}"
        )
        st.stop()

    numeric_columns = [
        "totalavgdailyboardings",
        "totalboarding",
        "totalboradingweekday",
        "totalboardingweekday",
        "totalboardingsaturday",
        "totalboradingsunday",
        "totalboardingsunday",
        "totalaveragedailyweekdayborading",
        "totalaveragedailyweekdayboarding",
        "totalaveragedailysaturdayborading",
        "totalaveragedailysaturdayboarding",
        "totalaveragedailysundayborading",
        "totalaveragedailysundayboarding",
        "avgmedianload",
        "avgontime",
        "avglate",
        "totalseasonalrevenuemiles",
        "averagedailyrevenuemilesweekday",
        "averagedailyrevenuemilessaturday",
        "averagedailyrevenuemilessunday",
        "totaltripcount",
        "totalseasonalrevenuehours",
        "averagedailyrevenuehoursweekday",
        "averagedailyrevenuehourssaturday",
        "averagedailyrevenuehourssunday",
        "ridershipperrevhour",
        "weekdayridershipperrevhour",
        "saturdayridershipperrevhour",
        "sundayridershipperrevhour",
    ]

    df["routes"] = clean_route_labels(df["routes"])

    for column in numeric_columns:
        if column in df.columns:
            df[column] = clean_numeric(df[column])

    # Create correctly spelled aliases when the CSV retains earlier typos.
    alias_map = {
        "totalboradingweekday": "totalboardingweekday",
        "totalboradingsunday": "totalboardingsunday",
        "totalaveragedailyweekdayborading": "totalaveragedailyweekdayboarding",
        "totalaveragedailysaturdayborading": "totalaveragedailysaturdayboarding",
        "totalaveragedailysundayborading": "totalaveragedailysundayboarding",
    }

    for old_name, new_name in alias_map.items():
        if new_name not in df.columns and old_name in df.columns:
            df[new_name] = df[old_name]

    df["route_sort"] = create_route_sort(df["routes"])

    return (
        df.sort_values(
            by=["route_sort", "routes"],
            na_position="last",
        )
        .reset_index(drop=True)
    )


def prepare_ridership_trend(df):
    """Clean and prepare the monthly ridership-trend dataset."""
    df = df.copy()

    required_columns = ["route", "yearmonth", "totalfarecounts"]
    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        st.error(
            "The ridership-trend CSV is missing these columns: "
            f"{missing_columns}. Available columns: {list(df.columns)}"
        )
        st.stop()

    df["route"] = clean_route_labels(df["route"])
    df["yearmonth"] = pd.to_datetime(df["yearmonth"], errors="coerce")
    df["totalfarecounts"] = clean_numeric(df["totalfarecounts"])
    df["route_sort"] = create_route_sort(df["route"])

    return (
        df.dropna(subset=["yearmonth"])
        .sort_values(
            by=["route_sort", "route", "yearmonth"],
            na_position="last",
        )
        .reset_index(drop=True)
    )


system_df = prepare_system_summary(system_df)
trend_df = prepare_ridership_trend(trend_df)

route_sort_order = (
    system_df[["routes", "route_sort"]]
    .dropna(subset=["routes"])
    .drop_duplicates(subset=["routes"])
    .sort_values(by=["route_sort", "routes"], na_position="last")["routes"]
    .astype(str)
    .tolist()
)


# ==================================================
# 6. REUSABLE CHART FORMATTING
# ==================================================

def format_chart(chart):
    return (
        chart.configure_axis(
            labelColor=TEXT_GRAY,
            titleColor=BFT_NAVY,
            gridColor=GRID_COLOR,
            gridOpacity=0.8,
            domain=False,
            tickColor=GRID_COLOR,
        )
        .configure_view(stroke=None)
        .configure_legend(
            labelColor=TEXT_GRAY,
            titleColor=BFT_NAVY,
            orient="top",
        )
        .configure_title(
            color=BFT_NAVY,
            fontSize=17,
            fontWeight=600,
            anchor="start",
        )
    )


def route_axis():
    return alt.X(
        "routes:N",
        title="Route",
        sort=route_sort_order,
        axis=alt.Axis(labelAngle=0, labelOverlap=False),
    )


def section_header(title, description=None):
    st.markdown(
        f'<div class="section-title">{title}</div>',
        unsafe_allow_html=True,
    )
    if description:
        st.markdown(
            f'<div class="section-description">{description}</div>',
            unsafe_allow_html=True,
        )


# ==================================================
# 7. DASHBOARD TABS
# ==================================================

tab1, tab2 = st.tabs(
    [
        "📊 Spring 2026 System Summary",
        "📈 Ridership Trend Since 2023",
    ]
)


# ==================================================
# 8. TAB 1 — SPRING 2026 SYSTEM SUMMARY
# ==================================================

with tab1:
    st.markdown("### Spring 2026 System Overview")

    total_boardings = system_df["totalboarding"].sum()
    total_avg_daily_boardings = system_df["totalavgdailyboardings"].sum()
    total_revenue_miles = system_df["totalseasonalrevenuemiles"].sum()
    total_revenue_hours = system_df["totalseasonalrevenuehours"].sum()
    total_trips = system_df["totaltripcount"].sum()

    overall_productivity = (
        total_boardings / total_revenue_hours
        if total_revenue_hours > 0
        else 0
    )

    boardings_weight = system_df["totalboarding"].fillna(0)
    total_weight = boardings_weight.sum()

    weighted_otp = (
        (system_df["avgontime"].fillna(0) * boardings_weight).sum()
        / total_weight
        if total_weight > 0
        else 0
    )

    weighted_late = (
        (system_df["avglate"].fillna(0) * boardings_weight).sum()
        / total_weight
        if total_weight > 0
        else 0
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Spring Boardings", f"{total_boardings:,.0f}")
    k2.metric(
        "Total Avg Daily Boardings",
        f"{total_avg_daily_boardings:,.1f}",
    )
    k3.metric("System On-Time", f"{weighted_otp:.1f}%")
    k4.metric("System Late", f"{weighted_late:.1f}%")

    k5, k6, k7, k8 = st.columns(4)
    k5.metric("Seasonal Revenue Miles", f"{total_revenue_miles:,.0f}")
    k6.metric("Seasonal Revenue Hours", f"{total_revenue_hours:,.1f}")
    k7.metric("Total Trips", f"{total_trips:,.0f}")
    k8.metric(
        "Boardings per Revenue Hour",
        f"{overall_productivity:.2f}",
    )

    st.divider()

    section_header(
        "Overall Ridership by Route",
        "Total seasonal boardings and average daily boardings.",
    )

    ridership_col1, ridership_col2 = st.columns(2)

    with ridership_col1:
        total_boarding_chart = (
            alt.Chart(system_df)
            .mark_bar(
                color=BFT_BLUE,
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
            )
            .encode(
                x=route_axis(),
                y=alt.Y("totalboarding:Q", title="Total Boardings"),
                tooltip=[
                    alt.Tooltip("routes:N", title="Route"),
                    alt.Tooltip(
                        "totalboarding:Q",
                        title="Total Boardings",
                        format=",.0f",
                    ),
                ],
            )
            .properties(height=380, title="Total Spring Boardings")
        )

        st.altair_chart(
            format_chart(total_boarding_chart),
            use_container_width=True,
        )

    with ridership_col2:
        average_daily_chart = (
            alt.Chart(system_df)
            .mark_bar(
                color=BFT_GOLD,
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
            )
            .encode(
                x=route_axis(),
                y=alt.Y(
                    "totalavgdailyboardings:Q",
                    title="Average Daily Boardings",
                ),
                tooltip=[
                    alt.Tooltip("routes:N", title="Route"),
                    alt.Tooltip(
                        "totalavgdailyboardings:Q",
                        title="Average Daily Boardings",
                        format=",.1f",
                    ),
                ],
            )
            .properties(
                height=380,
                title="Total Average Daily Boardings",
            )
        )

        st.altair_chart(
            format_chart(average_daily_chart),
            use_container_width=True,
        )

    section_header(
        "Total Boardings by Service Day",
        "Seasonal boardings divided between weekday, Saturday, and Sunday service.",
    )

    total_service_boardings = system_df[
        [
            "routes",
            "totalboardingweekday",
            "totalboardingsaturday",
            "totalboardingsunday",
        ]
    ].melt(
        id_vars="routes",
        var_name="service_day",
        value_name="total_boardings",
    )

    total_service_boardings["service_day"] = (
        total_service_boardings["service_day"].replace(
            {
                "totalboardingweekday": "Weekday",
                "totalboardingsaturday": "Saturday",
                "totalboardingsunday": "Sunday",
            }
        )
    )

    total_service_chart = (
        alt.Chart(total_service_boardings)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=route_axis(),
            xOffset=alt.XOffset(
                "service_day:N",
                sort=["Weekday", "Saturday", "Sunday"],
            ),
            y=alt.Y("total_boardings:Q", title="Total Boardings"),
            color=alt.Color(
                "service_day:N",
                title="Service Day",
                sort=["Weekday", "Saturday", "Sunday"],
                scale=alt.Scale(
                    domain=["Weekday", "Saturday", "Sunday"],
                    range=[
                        WEEKDAY_BLUE,
                        SATURDAY_GOLD,
                        SUNDAY_GREEN,
                    ],
                ),
            ),
            tooltip=[
                alt.Tooltip("routes:N", title="Route"),
                alt.Tooltip("service_day:N", title="Service Day"),
                alt.Tooltip(
                    "total_boardings:Q",
                    title="Total Boardings",
                    format=",.0f",
                ),
            ],
        )
        .properties(
            height=420,
            title="Total Seasonal Boardings by Service Day",
        )
    )

    st.altair_chart(
        format_chart(total_service_chart),
        use_container_width=True,
    )

    section_header(
        "Average Daily Boardings by Service Day",
        "Average daily route ridership for weekday, Saturday, and Sunday service.",
    )

    average_daily_boardings = system_df[
        [
            "routes",
            "totalaveragedailyweekdayboarding",
            "totalaveragedailysaturdayboarding",
            "totalaveragedailysundayboarding",
        ]
    ].melt(
        id_vars="routes",
        var_name="service_day",
        value_name="average_daily_boardings",
    )

    average_daily_boardings["service_day"] = (
        average_daily_boardings["service_day"].replace(
            {
                "totalaveragedailyweekdayboarding": "Weekday",
                "totalaveragedailysaturdayboarding": "Saturday",
                "totalaveragedailysundayboarding": "Sunday",
            }
        )
    )

    average_daily_boardings_chart = (
        alt.Chart(average_daily_boardings)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=route_axis(),
            xOffset=alt.XOffset(
                "service_day:N",
                sort=["Weekday", "Saturday", "Sunday"],
            ),
            y=alt.Y(
                "average_daily_boardings:Q",
                title="Average Daily Boardings",
            ),
            color=alt.Color(
                "service_day:N",
                title="Service Day",
                sort=["Weekday", "Saturday", "Sunday"],
                scale=alt.Scale(
                    domain=["Weekday", "Saturday", "Sunday"],
                    range=[
                        WEEKDAY_BLUE,
                        SATURDAY_GOLD,
                        SUNDAY_GREEN,
                    ],
                ),
            ),
            tooltip=[
                alt.Tooltip("routes:N", title="Route"),
                alt.Tooltip("service_day:N", title="Service Day"),
                alt.Tooltip(
                    "average_daily_boardings:Q",
                    title="Average Daily Boardings",
                    format=",.1f",
                ),
            ],
        )
        .properties(
            height=420,
            title="Average Daily Boardings by Service Day",
        )
    )

    st.altair_chart(
        format_chart(average_daily_boardings_chart),
        use_container_width=True,
    )

    section_header(
        "Passenger Load",
        "Average median passenger load by route.",
    )

    median_load_chart = (
        alt.Chart(system_df)
        .mark_bar(
            color=BFT_LIGHT_BLUE,
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
        )
        .encode(
            x=route_axis(),
            y=alt.Y(
                "avgmedianload:Q",
                title="Average Median Passenger Load",
            ),
            tooltip=[
                alt.Tooltip("routes:N", title="Route"),
                alt.Tooltip(
                    "avgmedianload:Q",
                    title="Average Median Load",
                    format=".1f",
                ),
            ],
        )
        .properties(
            height=390,
            title="Average Median Passenger Load by Route",
        )
    )

    st.altair_chart(
        format_chart(median_load_chart),
        use_container_width=True,
    )

    section_header(
        "On-Time Performance",
        "On-Time and Late percentages are displayed in the same stacked column for each route.",
    )

    performance_data = system_df[
        ["routes", "avgontime", "avglate"]
    ].melt(
        id_vars="routes",
        var_name="performance_type",
        value_name="percentage",
    )

    performance_data["performance_type"] = (
        performance_data["performance_type"].replace(
            {
                "avgontime": "On-Time",
                "avglate": "Late",
            }
        )
    )

    performance_chart = (
        alt.Chart(performance_data)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=route_axis(),
            y=alt.Y(
                "percentage:Q",
                title="Percentage",
                stack="zero",
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(labelExpr="datum.value + '%'"),
            ),
            color=alt.Color(
                "performance_type:N",
                title="Performance",
                sort=["On-Time", "Late"],
                scale=alt.Scale(
                    domain=["On-Time", "Late"],
                    range=[ON_TIME_GREEN, LATE_RED],
                ),
            ),
            order=alt.Order("performance_type:N", sort="descending"),
            tooltip=[
                alt.Tooltip("routes:N", title="Route"),
                alt.Tooltip(
                    "performance_type:N",
                    title="Performance",
                ),
                alt.Tooltip(
                    "percentage:Q",
                    title="Percentage",
                    format=".1f",
                ),
            ],
        )
        .properties(
            height=430,
            title="Average On-Time and Late Performance by Route",
        )
    )

    st.altair_chart(
        format_chart(performance_chart),
        use_container_width=True,
    )

    section_header(
        "Seasonal Service Supply",
        "Seasonal revenue miles, revenue hours, and trip counts are displayed separately because they use different units.",
    )

    supply_col1, supply_col2, supply_col3 = st.columns(3)

    with supply_col1:
        seasonal_miles_chart = (
            alt.Chart(system_df)
            .mark_bar(
                color=REVENUE_MILES_TEAL,
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
            )
            .encode(
                x=route_axis(),
                y=alt.Y(
                    "totalseasonalrevenuemiles:Q",
                    title="Revenue Miles",
                ),
                tooltip=[
                    alt.Tooltip("routes:N", title="Route"),
                    alt.Tooltip(
                        "totalseasonalrevenuemiles:Q",
                        title="Seasonal Revenue Miles",
                        format=",.0f",
                    ),
                ],
            )
            .properties(height=390, title="Seasonal Revenue Miles")
        )
        st.altair_chart(
            format_chart(seasonal_miles_chart),
            use_container_width=True,
        )

    with supply_col2:
        seasonal_hours_chart = (
            alt.Chart(system_df)
            .mark_bar(
                color=REVENUE_HOURS_PURPLE,
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
            )
            .encode(
                x=route_axis(),
                y=alt.Y(
                    "totalseasonalrevenuehours:Q",
                    title="Revenue Hours",
                ),
                tooltip=[
                    alt.Tooltip("routes:N", title="Route"),
                    alt.Tooltip(
                        "totalseasonalrevenuehours:Q",
                        title="Seasonal Revenue Hours",
                        format=",.1f",
                    ),
                ],
            )
            .properties(height=390, title="Seasonal Revenue Hours")
        )
        st.altair_chart(
            format_chart(seasonal_hours_chart),
            use_container_width=True,
        )

    with supply_col3:
        total_trips_chart = (
            alt.Chart(system_df)
            .mark_bar(
                color=TRIPS_ORANGE,
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
            )
            .encode(
                x=route_axis(),
                y=alt.Y("totaltripcount:Q", title="Trip Count"),
                tooltip=[
                    alt.Tooltip("routes:N", title="Route"),
                    alt.Tooltip(
                        "totaltripcount:Q",
                        title="Total Trips",
                        format=",.0f",
                    ),
                ],
            )
            .properties(height=390, title="Total Trip Count")
        )
        st.altair_chart(
            format_chart(total_trips_chart),
            use_container_width=True,
        )

    section_header(
        "Average Daily Revenue Miles",
        "Average daily revenue miles by route and service day.",
    )

    daily_miles_data = system_df[
        [
            "routes",
            "averagedailyrevenuemilesweekday",
            "averagedailyrevenuemilessaturday",
            "averagedailyrevenuemilessunday",
        ]
    ].melt(
        id_vars="routes",
        var_name="service_day",
        value_name="average_daily_revenue_miles",
    )

    daily_miles_data["service_day"] = (
        daily_miles_data["service_day"].replace(
            {
                "averagedailyrevenuemilesweekday": "Weekday",
                "averagedailyrevenuemilessaturday": "Saturday",
                "averagedailyrevenuemilessunday": "Sunday",
            }
        )
    )

    daily_miles_chart = (
        alt.Chart(daily_miles_data)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=route_axis(),
            xOffset=alt.XOffset(
                "service_day:N",
                sort=["Weekday", "Saturday", "Sunday"],
            ),
            y=alt.Y(
                "average_daily_revenue_miles:Q",
                title="Average Daily Revenue Miles",
            ),
            color=alt.Color(
                "service_day:N",
                title="Service Day",
                sort=["Weekday", "Saturday", "Sunday"],
                scale=alt.Scale(
                    domain=["Weekday", "Saturday", "Sunday"],
                    range=[
                        WEEKDAY_BLUE,
                        SATURDAY_GOLD,
                        SUNDAY_GREEN,
                    ],
                ),
            ),
            tooltip=[
                alt.Tooltip("routes:N", title="Route"),
                alt.Tooltip("service_day:N", title="Service Day"),
                alt.Tooltip(
                    "average_daily_revenue_miles:Q",
                    title="Average Daily Revenue Miles",
                    format=",.1f",
                ),
            ],
        )
        .properties(
            height=420,
            title="Average Daily Revenue Miles by Service Day",
        )
    )

    st.altair_chart(
        format_chart(daily_miles_chart),
        use_container_width=True,
    )

    section_header(
        "Average Daily Revenue Hours",
        "Average daily revenue hours by route and service day.",
    )

    daily_hours_data = system_df[
        [
            "routes",
            "averagedailyrevenuehoursweekday",
            "averagedailyrevenuehourssaturday",
            "averagedailyrevenuehourssunday",
        ]
    ].melt(
        id_vars="routes",
        var_name="service_day",
        value_name="average_daily_revenue_hours",
    )

    daily_hours_data["service_day"] = (
        daily_hours_data["service_day"].replace(
            {
                "averagedailyrevenuehoursweekday": "Weekday",
                "averagedailyrevenuehourssaturday": "Saturday",
                "averagedailyrevenuehourssunday": "Sunday",
            }
        )
    )

    daily_hours_chart = (
        alt.Chart(daily_hours_data)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=route_axis(),
            xOffset=alt.XOffset(
                "service_day:N",
                sort=["Weekday", "Saturday", "Sunday"],
            ),
            y=alt.Y(
                "average_daily_revenue_hours:Q",
                title="Average Daily Revenue Hours",
            ),
            color=alt.Color(
                "service_day:N",
                title="Service Day",
                sort=["Weekday", "Saturday", "Sunday"],
                scale=alt.Scale(
                    domain=["Weekday", "Saturday", "Sunday"],
                    range=[
                        WEEKDAY_BLUE,
                        SATURDAY_GOLD,
                        SUNDAY_GREEN,
                    ],
                ),
            ),
            tooltip=[
                alt.Tooltip("routes:N", title="Route"),
                alt.Tooltip("service_day:N", title="Service Day"),
                alt.Tooltip(
                    "average_daily_revenue_hours:Q",
                    title="Average Daily Revenue Hours",
                    format=",.1f",
                ),
            ],
        )
        .properties(
            height=420,
            title="Average Daily Revenue Hours by Service Day",
        )
    )

    st.altair_chart(
        format_chart(daily_hours_chart),
        use_container_width=True,
    )

    section_header(
        "Ridership per Revenue Hour",
        "Overall and service-day productivity measures by route.",
    )

    overall_productivity_chart = (
        alt.Chart(system_df)
        .mark_bar(
            color=ON_TIME_GREEN,
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
        )
        .encode(
            x=route_axis(),
            y=alt.Y(
                "ridershipperrevhour:Q",
                title="Ridership per Revenue Hour",
            ),
            tooltip=[
                alt.Tooltip("routes:N", title="Route"),
                alt.Tooltip(
                    "ridershipperrevhour:Q",
                    title="Overall Ridership per Revenue Hour",
                    format=".2f",
                ),
            ],
        )
        .properties(
            height=390,
            title="Overall Ridership per Revenue Hour",
        )
    )

    st.altair_chart(
        format_chart(overall_productivity_chart),
        use_container_width=True,
    )

    productivity_by_day = system_df[
        [
            "routes",
            "weekdayridershipperrevhour",
            "saturdayridershipperrevhour",
            "sundayridershipperrevhour",
        ]
    ].melt(
        id_vars="routes",
        var_name="service_day",
        value_name="ridership_per_revenue_hour",
    )

    productivity_by_day["service_day"] = (
        productivity_by_day["service_day"].replace(
            {
                "weekdayridershipperrevhour": "Weekday",
                "saturdayridershipperrevhour": "Saturday",
                "sundayridershipperrevhour": "Sunday",
            }
        )
    )

    productivity_day_chart = (
        alt.Chart(productivity_by_day)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=route_axis(),
            xOffset=alt.XOffset(
                "service_day:N",
                sort=["Weekday", "Saturday", "Sunday"],
            ),
            y=alt.Y(
                "ridership_per_revenue_hour:Q",
                title="Ridership per Revenue Hour",
            ),
            color=alt.Color(
                "service_day:N",
                title="Service Day",
                sort=["Weekday", "Saturday", "Sunday"],
                scale=alt.Scale(
                    domain=["Weekday", "Saturday", "Sunday"],
                    range=[
                        WEEKDAY_BLUE,
                        SATURDAY_GOLD,
                        SUNDAY_GREEN,
                    ],
                ),
            ),
            tooltip=[
                alt.Tooltip("routes:N", title="Route"),
                alt.Tooltip("service_day:N", title="Service Day"),
                alt.Tooltip(
                    "ridership_per_revenue_hour:Q",
                    title="Ridership per Revenue Hour",
                    format=".2f",
                ),
            ],
        )
        .properties(
            height=420,
            title="Ridership per Revenue Hour by Service Day",
        )
    )

    st.altair_chart(
        format_chart(productivity_day_chart),
        use_container_width=True,
    )

    section_header(
        "Complete Spring 2026 System Summary",
        "The table below contains every field from the system-summary CSV.",
    )

    display_columns = {
        "routes": "Route",
        "totalavgdailyboardings": "Total Avg Daily Boardings",
        "totalboarding": "Total Boardings",
        "totalboardingweekday": "Total Boardings – Weekday",
        "totalboardingsaturday": "Total Boardings – Saturday",
        "totalboardingsunday": "Total Boardings – Sunday",
        "totalaveragedailyweekdayboarding": "Avg Daily Boardings – Weekday",
        "totalaveragedailysaturdayboarding": "Avg Daily Boardings – Saturday",
        "totalaveragedailysundayboarding": "Avg Daily Boardings – Sunday",
        "avgmedianload": "Avg Median Load",
        "avgontime": "Avg On-Time (%)",
        "avglate": "Avg Late (%)",
        "totalseasonalrevenuemiles": "Total Seasonal Revenue Miles",
        "averagedailyrevenuemilesweekday": "Avg Daily Revenue Miles – Weekday",
        "averagedailyrevenuemilessaturday": "Avg Daily Revenue Miles – Saturday",
        "averagedailyrevenuemilessunday": "Avg Daily Revenue Miles – Sunday",
        "totaltripcount": "Total Trip Count",
        "totalseasonalrevenuehours": "Total Seasonal Revenue Hours",
        "averagedailyrevenuehoursweekday": "Avg Daily Revenue Hours – Weekday",
        "averagedailyrevenuehourssaturday": "Avg Daily Revenue Hours – Saturday",
        "averagedailyrevenuehourssunday": "Avg Daily Revenue Hours – Sunday",
        "ridershipperrevhour": "Ridership per Revenue Hour",
        "weekdayridershipperrevhour": "Weekday Ridership per Revenue Hour",
        "saturdayridershipperrevhour": "Saturday Ridership per Revenue Hour",
        "sundayridershipperrevhour": "Sunday Ridership per Revenue Hour",
    }

    available_display_columns = {
        key: value
        for key, value in display_columns.items()
        if key in system_df.columns
    }

    complete_summary = system_df[
        list(available_display_columns.keys())
    ].rename(columns=available_display_columns)

    st.dataframe(
        complete_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Route": st.column_config.TextColumn("Route", pinned=True),
            "Avg On-Time (%)": st.column_config.NumberColumn(
                "Avg On-Time (%)",
                format="%.1f%%",
            ),
            "Avg Late (%)": st.column_config.NumberColumn(
                "Avg Late (%)",
                format="%.1f%%",
            ),
        },
    )


# ==================================================
# 9. TAB 2 — RIDERSHIP TREND SINCE 2023
# ==================================================

with tab2:
    st.markdown("### Ridership Trend")

    route_options = (
        trend_df[["route", "route_sort"]]
        .dropna(subset=["route"])
        .drop_duplicates(subset=["route"])
        .sort_values(
            by=["route_sort", "route"],
            na_position="last",
        )["route"]
        .astype(str)
        .tolist()
    )

    route_filter_options = ["System Total"] + route_options

    selected_route = st.selectbox(
        "Route",
        options=route_filter_options,
        index=0,
        key="ridership_trend_route",
    )

    if selected_route == "System Total":
        chart_data = (
            trend_df.groupby("yearmonth", as_index=False)[
                "totalfarecounts"
            ].sum()
        )
        chart_data["route"] = "System Total"
    else:
        chart_data = trend_df.loc[
            trend_df["route"] == selected_route,
            ["route", "yearmonth", "totalfarecounts"],
        ].copy()

    if chart_data.empty:
        st.warning("No ridership data are available for this selection.")
        st.stop()

    chart_data = chart_data.sort_values("yearmonth").reset_index(drop=True)

    latest_month = chart_data["yearmonth"].max()
    previous_month = latest_month - pd.DateOffset(months=1)

    latest_total = chart_data.loc[
        chart_data["yearmonth"] == latest_month,
        "totalfarecounts",
    ].sum()

    previous_total = chart_data.loc[
        chart_data["yearmonth"] == previous_month,
        "totalfarecounts",
    ].sum()

    monthly_change = (
        ((latest_total - previous_total) / previous_total) * 100
        if previous_total > 0
        else 0
    )

    latest_year = latest_month.year
    latest_year_total = chart_data.loc[
        chart_data["yearmonth"].dt.year == latest_year,
        "totalfarecounts",
    ].sum()

    trend_k1, trend_k2, trend_k3, trend_k4 = st.columns(4)
    trend_k1.metric("Latest Month", latest_month.strftime("%B %Y"))
    trend_k2.metric("Latest Monthly Ridership", f"{latest_total:,.0f}")
    trend_k3.metric(
        "Change from Previous Month",
        f"{monthly_change:+.1f}%",
    )
    trend_k4.metric(
        f"{latest_year} Ridership to Date",
        f"{latest_year_total:,.0f}",
    )

    section_header(
        "Monthly Ridership Trend",
        f"Monthly fare counts for {selected_route}.",
    )

    trend_chart = (
        alt.Chart(chart_data)
        .mark_line(
            color=BFT_BLUE,
            point=alt.OverlayMarkDef(filled=True, size=55),
            strokeWidth=3,
        )
        .encode(
            x=alt.X(
                "yearmonth:T",
                title="Month",
                axis=alt.Axis(format="%b %Y", labelAngle=-45),
            ),
            y=alt.Y(
                "totalfarecounts:Q",
                title="Total Fare Counts",
                scale=alt.Scale(zero=False),
            ),
            tooltip=[
                alt.Tooltip(
                    "yearmonth:T",
                    title="Month",
                    format="%B %Y",
                ),
                alt.Tooltip("route:N", title="Route"),
                alt.Tooltip(
                    "totalfarecounts:Q",
                    title="Fare Counts",
                    format=",.0f",
                ),
            ],
        )
        .properties(
            height=500,
            title=f"Monthly Fare Counts – {selected_route}",
        )
        .interactive()
    )

    st.altair_chart(
        format_chart(trend_chart),
        use_container_width=True,
    )

    annual_ridership = (
        chart_data.assign(year=chart_data["yearmonth"].dt.year)
        .groupby("year", as_index=False)["totalfarecounts"]
        .sum()
    )

    section_header(
        "Annual Ridership",
        "Annual fare-count totals for the selected route.",
    )

    annual_chart = (
        alt.Chart(annual_ridership)
        .mark_bar(
            color=BFT_GOLD,
            cornerRadiusTopLeft=5,
            cornerRadiusTopRight=5,
        )
        .encode(
            x=alt.X("year:O", title="Year"),
            y=alt.Y(
                "totalfarecounts:Q",
                title="Annual Fare Counts",
            ),
            tooltip=[
                alt.Tooltip("year:O", title="Year"),
                alt.Tooltip(
                    "totalfarecounts:Q",
                    title="Annual Fare Counts",
                    format=",.0f",
                ),
            ],
        )
        .properties(
            height=390,
            title=f"Annual Ridership – {selected_route}",
        )
    )

    st.altair_chart(
        format_chart(annual_chart),
        use_container_width=True,
    )

    with st.expander("View ridership trend data"):
        st.dataframe(
            chart_data[
                ["route", "yearmonth", "totalfarecounts"]
            ].rename(
                columns={
                    "route": "Route",
                    "yearmonth": "Month",
                    "totalfarecounts": "Total Fare Counts",
                }
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Month": st.column_config.DateColumn(
                    "Month",
                    format="MMM YYYY",
                ),
                "Total Fare Counts": st.column_config.NumberColumn(
                    "Total Fare Counts",
                    format="%,.0f",
                ),
            },
        )


# ==================================================
# 10. FOOTER
# ==================================================

st.divider()

st.caption(
    "Data sources: data/Summary System(1).csv and "
    "data/Ridership Trend from 2023 - Jul 20 2026(1).csv "
    "• Ben Franklin Transit"
)
