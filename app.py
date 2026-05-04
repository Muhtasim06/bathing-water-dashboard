import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="European Bathing Water Quality",
    page_icon="🌊",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #f0f6fb; }
    .block-container { padding-top: 2rem; }
    h1 { color: #0a4c73; }
    h2, h3 { color: #1a6fa3; }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
DATA_URL = "https://sdi.eea.europa.eu/datashare/s/J86aarkSmCMXpkc/download?path=%2F&files=bw_assessment_eea_datahub_1990_2024.xlsx"

@st.cache_data(show_spinner="Loading dataset…")
def load_data():
    df = pd.read_excel(DATA_URL, engine="openpyxl")
    df.columns = df.columns.str.strip()
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

# ── Inspect and normalise columns ─────────────────────────────────────────────
# Show columns in sidebar for debugging (remove later)
with st.expander("🔍 Raw column names (debug)"):
    st.write(df_raw.columns.tolist())
    st.write(df_raw.head(3))

# Lowercase all column names for easier handling
df_raw.columns = [c.lower().strip() for c in df_raw.columns]

# Try to find the key columns automatically
def find_col(df, candidates):
    for c in candidates:
        for col in df.columns:
            if c in col:
                return col
    return None

col_country   = find_col(df_raw, ["country", "nation", "member"])
col_year      = find_col(df_raw, ["year", "season"])
col_quality   = find_col(df_raw, ["quality", "class", "status", "rating"])
col_type      = find_col(df_raw, ["type", "coastal", "inland", "category"])
col_count     = find_col(df_raw, ["count", "number", "total", "sites", "num"])

# Map found columns to standard names
rename = {}
if col_country: rename[col_country] = "country"
if col_year:    rename[col_year]    = "year"
if col_quality: rename[col_quality] = "quality"
if col_type:    rename[col_type]    = "water_type"
if col_count:   rename[col_count]   = "count"

df = df_raw.rename(columns=rename).copy()

# Ensure year is numeric
if "year" in df.columns:
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("🌊 European Bathing Water Quality Dashboard")
st.markdown("Explore bathing water quality across Europe from **1990 to 2024**, based on data from the **European Environment Agency (EEA)**.")
st.divider()

# ── Sidebar filters ────────────────────────────────────────────────────────────
st.sidebar.header("🔧 Filters")

# Year range slider
if "year" in df.columns:
    min_y, max_y = int(df["year"].min()), int(df["year"].max())
    year_range = st.sidebar.slider("Year range", min_y, max_y, (2015, max_y))
    df_f = df[(df["year"] >= year_range[0]) & (df["year"] <= year_range[1])]
else:
    df_f = df.copy()
    year_range = (None, None)

# Country filter
if "country" in df_f.columns:
    countries = sorted(df_f["country"].dropna().unique())
    selected_countries = st.sidebar.multiselect("Countries", countries, default=countries[:10] if len(countries) > 10 else countries)
    if selected_countries:
        df_f = df_f[df_f["country"].isin(selected_countries)]

# Water type filter
if "water_type" in df_f.columns:
    types = sorted(df_f["water_type"].dropna().unique())
    selected_type = st.sidebar.multiselect("Water type", types, default=types)
    if selected_type:
        df_f = df_f[df_f["water_type"].isin(selected_type)]

# Quality filter
if "quality" in df_f.columns:
    qualities = sorted(df_f["quality"].dropna().unique())
    selected_quality = st.sidebar.multiselect("Quality rating", qualities, default=qualities)
    if selected_quality:
        df_f = df_f[df_f["quality"].isin(selected_quality)]

st.sidebar.markdown("---")
st.sidebar.caption("Data: European Environment Agency (EEA) — Bathing Water Directive, Status of Bathing Water (1990–2024)")

# ── KPI cards ──────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
total_sites = len(df_f)
n_countries = df_f["country"].nunique() if "country" in df_f.columns else "N/A"

if "quality" in df_f.columns:
    # Try to count excellent sites — handle different naming conventions
    excellent_mask = df_f["quality"].astype(str).str.lower().str.contains("excell")
    poor_mask      = df_f["quality"].astype(str).str.lower().str.contains("poor")
    pct_excellent  = round(excellent_mask.sum() / len(df_f) * 100, 1) if len(df_f) > 0 else 0
    pct_poor       = round(poor_mask.sum()      / len(df_f) * 100, 1) if len(df_f) > 0 else 0
else:
    pct_excellent = pct_poor = "N/A"

with k1:
    st.metric("Total records", f"{total_sites:,}")
with k2:
    st.metric("Countries", n_countries)
with k3:
    st.metric("% Excellent quality", f"{pct_excellent}%")
with k4:
    st.metric("% Poor quality", f"{pct_poor}%")

st.divider()

# ── Charts ─────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

# Chart 1: Quality rating breakdown (donut)
with col_left:
    st.subheader("Quality Rating Breakdown")
    if "quality" in df_f.columns:
        quality_counts = df_f["quality"].value_counts().reset_index()
        quality_counts.columns = ["Quality", "Count"]
        colour_map = {
            "Excellent": "#2196F3",
            "Good":      "#4CAF50",
            "Sufficient":"#FF9800",
            "Poor":      "#F44336",
        }
        # Partial match colouring
        def match_colour(q):
            q_lower = str(q).lower()
            if "excell" in q_lower: return "#2196F3"
            if "good"   in q_lower: return "#4CAF50"
            if "suffic" in q_lower: return "#FF9800"
            if "poor"   in q_lower: return "#F44336"
            return "#9E9E9E"
        colours = [match_colour(q) for q in quality_counts["Quality"]]
        fig1 = go.Figure(go.Pie(
            labels=quality_counts["Quality"],
            values=quality_counts["Count"],
            hole=0.45,
            marker_colors=colours,
        ))
        fig1.update_layout(margin=dict(t=10, b=10), height=320, legend=dict(orientation="h"))
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("Quality column not found in dataset.")

# Chart 2: Coastal vs Inland
with col_right:
    st.subheader("Coastal vs Inland Sites")
    if "water_type" in df_f.columns and "quality" in df_f.columns:
        type_quality = df_f.groupby(["water_type", "quality"]).size().reset_index(name="count")
        fig2 = px.bar(
            type_quality, x="water_type", y="count", color="quality",
            barmode="group",
            color_discrete_map={q: match_colour(q) for q in type_quality["quality"].unique()},
            labels={"water_type": "Water Type", "count": "Number of Sites", "quality": "Quality"},
        )
        fig2.update_layout(margin=dict(t=10, b=10), height=320, legend=dict(orientation="h"))
        st.plotly_chart(fig2, use_container_width=True)
    elif "water_type" in df_f.columns:
        type_counts = df_f["water_type"].value_counts().reset_index()
        type_counts.columns = ["Type", "Count"]
        fig2 = px.bar(type_counts, x="Type", y="Count", color="Type")
        fig2.update_layout(margin=dict(t=10, b=10), height=320)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Water type column not found in dataset.")

st.divider()

# Chart 3: Trend over time
st.subheader("📈 Quality Trend Over Time")
if "year" in df_f.columns and "quality" in df_f.columns:
    trend = df_f.groupby(["year", "quality"]).size().reset_index(name="count")
    fig3 = px.line(
        trend, x="year", y="count", color="quality",
        color_discrete_map={q: match_colour(q) for q in trend["quality"].unique()},
        markers=True,
        labels={"year": "Year", "count": "Number of Sites", "quality": "Quality"},
    )
    fig3.update_layout(height=380, legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("Year or quality column not found.")

st.divider()

# Chart 4: Country comparison bar chart
st.subheader("🏳️ Country Comparison")
if "country" in df_f.columns and "quality" in df_f.columns:
    # Pick a single year for comparison — default to latest
    if "year" in df_f.columns:
        available_years = sorted(df_f["year"].unique(), reverse=True)
        selected_year = st.selectbox("Select year for country comparison", available_years)
        df_year = df_f[df_f["year"] == selected_year]
    else:
        df_year = df_f

    country_q = df_year.groupby(["country", "quality"]).size().reset_index(name="count")
    fig4 = px.bar(
        country_q, x="country", y="count", color="quality",
        barmode="stack",
        color_discrete_map={q: match_colour(q) for q in country_q["quality"].unique()},
        labels={"country": "Country", "count": "Sites", "quality": "Quality"},
    )
    fig4.update_layout(height=420, xaxis_tickangle=-45, legend=dict(orientation="h"))
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("Country or quality column not found.")

st.divider()

# Chart 5: Excellent % by country map
st.subheader("🗺️ Excellent Water Quality by Country")
if "country" in df_f.columns and "quality" in df_f.columns:
    total_by_country    = df_f.groupby("country").size().reset_index(name="total")
    excellent_by_country = df_f[excellent_mask].groupby("country").size().reset_index(name="excellent") if "quality" in df_f.columns else pd.DataFrame()
    if not excellent_by_country.empty:
        map_df = total_by_country.merge(excellent_by_country, on="country", how="left").fillna(0)
        map_df["pct_excellent"] = (map_df["excellent"] / map_df["total"] * 100).round(1)
        fig5 = px.choropleth(
            map_df,
            locations="country",
            locationmode="country names",
            color="pct_excellent",
            color_continuous_scale="Blues",
            range_color=(0, 100),
            labels={"pct_excellent": "% Excellent"},
            scope="europe",
        )
        fig5.update_layout(height=500, margin=dict(t=10, b=10))
        st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("Could not compute excellent % by country.")
else:
    st.info("Country or quality column not found.")

st.divider()
st.caption("Dashboard built with Streamlit · Data source: European Environment Agency (EEA) Bathing Water Directive Dataset (1990–2024) · https://www.eea.europa.eu")
