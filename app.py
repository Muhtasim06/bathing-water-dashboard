import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="European Bathing Water Quality",
    page_icon="🌊",
    layout="wide",
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    [data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
DATA_URL = "https://sdi.eea.europa.eu/datashare/s/J86aarkSmCMXpkc/download?path=%2F&files=bw_assessment_eea_datahub_1990_2024.xlsx"

@st.cache_data(show_spinner="Loading dataset… this may take a moment ☕")
def load_data():
    import io, requests
    r = requests.get(DATA_URL)
    xl = pd.ExcelFile(io.BytesIO(r.content), engine="openpyxl")
    # Pick the sheet with the most columns (skip metadata sheets)
    best_sheet, best_cols = None, 0
    for sheet in xl.sheet_names:
        try:
            tmp = xl.parse(sheet, nrows=2)
            if len(tmp.columns) > best_cols:
                best_cols = len(tmp.columns)
                best_sheet = sheet
        except:
            pass
    df = xl.parse(best_sheet)
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

# ── Map exact column names ────────────────────────────────────────────────────
df = df_raw.rename(columns={
    "countryCode":      "country",
    "season":           "year",
    "quality":          "quality",
    "bathingWaterType": "water_type",
    "bathingWaterName": "site_name",
    "lat":              "lat",
    "lon":              "lon",
}).copy()

# Find the year column flexibly in case rename didn't catch it
if "year" not in df.columns:
    for c in df.columns:
        if "season" in c.lower() or "year" in c.lower():
            df = df.rename(columns={c: "year"})
            break

if "year" not in df.columns:
    st.error(f"Could not find a year/season column. Columns available: {df.columns.tolist()}")
    st.stop()

df["year"] = pd.to_numeric(df["year"], errors="coerce")
df = df.dropna(subset=["year"])
df["year"] = df["year"].astype(int)
df["quality"] = df["quality"].astype(str).str.strip().str.title()

# Colour map
COLOURS = {
    "Excellent":  "#1565C0",
    "Good":       "#43A047",
    "Sufficient": "#FB8C00",
    "Poor":       "#E53935",
}
def q_colour(q):
    for k, v in COLOURS.items():
        if k.lower() in str(q).lower():
            return v
    return "#9E9E9E"

# Country code → full name lookup
COUNTRY_NAMES = {
    "AT":"Austria","BE":"Belgium","BG":"Bulgaria","CY":"Cyprus","CZ":"Czech Republic",
    "DE":"Germany","DK":"Denmark","EE":"Estonia","EL":"Greece","ES":"Spain",
    "FI":"Finland","FR":"France","HR":"Croatia","HU":"Hungary","IE":"Ireland",
    "IT":"Italy","LT":"Lithuania","LU":"Luxembourg","LV":"Latvia","MT":"Malta",
    "NL":"Netherlands","PL":"Poland","PT":"Portugal","RO":"Romania","SE":"Sweden",
    "SI":"Slovenia","SK":"Slovakia","AL":"Albania","ME":"Montenegro","RS":"Serbia",
    "TR":"Turkey","CH":"Switzerland","NO":"Norway","IS":"Iceland","LI":"Liechtenstein",
}

# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.header("🔧 Filters")

min_y, max_y = int(df["year"].min()), int(df["year"].max())
year_range = st.sidebar.slider("Year range", min_y, max_y, (2010, max_y))

countries = sorted(df["country"].dropna().unique())
selected_countries = st.sidebar.multiselect("Countries", countries, default=countries)

water_types = sorted(df["water_type"].dropna().unique())
selected_types = st.sidebar.multiselect("Water type", water_types, default=water_types)

qualities = sorted(df["quality"].dropna().unique())
selected_qualities = st.sidebar.multiselect("Quality rating", qualities, default=qualities)

st.sidebar.markdown("---")
st.sidebar.caption("Data: EEA Bathing Water Directive (1990–2024)")

# ── Apply filters ─────────────────────────────────────────────────────────────
df_f = df[
    (df["year"] >= year_range[0]) &
    (df["year"] <= year_range[1]) &
    (df["country"].isin(selected_countries)) &
    (df["water_type"].isin(selected_types)) &
    (df["quality"].isin(selected_qualities))
]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🌊 European Bathing Water Quality Dashboard")
st.markdown("Explore bathing water quality across Europe from **1990 to 2024**, based on data from the **European Environment Agency (EEA)**.")
st.divider()

# ── KPI metrics ───────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
total    = len(df_f)
n_ctry   = df_f["country"].nunique()
exc_pct  = round(df_f["quality"].str.lower().str.contains("excell").sum() / total * 100, 1) if total else 0
poor_pct = round(df_f["quality"].str.lower().str.contains("poor").sum()   / total * 100, 1) if total else 0

k1.metric("Total records",       f"{total:,}")
k2.metric("Countries",           n_ctry)
k3.metric("% Excellent quality", f"{exc_pct}%")
k4.metric("% Poor quality",      f"{poor_pct}%")

st.divider()

# ── Chart 1 & 2: Donut + Coastal vs Inland ────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Quality Rating Breakdown")
    qc = df_f["quality"].value_counts().reset_index()
    qc.columns = ["Quality", "Count"]
    fig1 = go.Figure(go.Pie(
        labels=qc["Quality"],
        values=qc["Count"],
        hole=0.45,
        marker_colors=[q_colour(q) for q in qc["Quality"]],
    ))
    fig1.update_layout(height=350, margin=dict(t=10, b=10),
                       legend=dict(orientation="h", yanchor="top", y=-0.1))
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("Coastal vs Inland Sites")
    tv = df_f.groupby(["water_type", "quality"]).size().reset_index(name="count")
    fig2 = px.bar(
        tv, x="water_type", y="count", color="quality",
        barmode="stack",
        color_discrete_map={q: q_colour(q) for q in tv["quality"].unique()},
        labels={"water_type": "Water Type", "count": "Sites", "quality": "Quality"},
    )
    fig2.update_layout(height=350, margin=dict(t=10, b=10),
                       legend=dict(orientation="h", yanchor="top", y=-0.1))
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Chart 3: Trend over time ──────────────────────────────────────────────────
st.subheader("📈 Quality Trend Over Time")
trend = df_f.groupby(["year", "quality"]).size().reset_index(name="count")
fig3 = px.line(
    trend, x="year", y="count", color="quality",
    markers=True,
    color_discrete_map={q: q_colour(q) for q in trend["quality"].unique()},
    labels={"year": "Year", "count": "Number of Sites", "quality": "Quality"},
)
fig3.update_layout(height=400, legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ── Chart 4: Country comparison ───────────────────────────────────────────────
st.subheader("🏳️ Country Comparison")
available_years = sorted(df_f["year"].unique(), reverse=True)
if available_years:
    sel_year = st.selectbox("Select year for country comparison", available_years)
    df_yr = df_f[df_f["year"] == sel_year]
    cq = df_yr.groupby(["country", "quality"]).size().reset_index(name="count")
    fig4 = px.bar(
        cq, x="country", y="count", color="quality",
        barmode="stack",
        color_discrete_map={q: q_colour(q) for q in cq["quality"].unique()},
        labels={"country": "Country Code", "count": "Sites", "quality": "Quality"},
    )
    fig4.update_layout(height=450, xaxis_tickangle=-45,
                       legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("No data for selected filters.")

st.divider()

# ── Chart 5: Choropleth map ───────────────────────────────────────────────────
st.subheader("🗺️ Excellent Water Quality by Country (%)")
total_by_c = df_f.groupby("country").size().reset_index(name="total")
exc_by_c   = (df_f[df_f["quality"].str.lower().str.contains("excell")]
              .groupby("country").size().reset_index(name="excellent"))
map_df     = total_by_c.merge(exc_by_c, on="country", how="left").fillna(0)
map_df["pct_excellent"]  = (map_df["excellent"] / map_df["total"] * 100).round(1)
map_df["country_name"]   = map_df["country"].map(COUNTRY_NAMES).fillna(map_df["country"])

fig5 = px.choropleth(
    map_df,
    locations="country_name",
    locationmode="country names",
    color="pct_excellent",
    color_continuous_scale="Blues",
    range_color=(0, 100),
    scope="europe",
    hover_name="country_name",
    hover_data={"pct_excellent": ":.1f", "total": True, "excellent": True},
    labels={"pct_excellent": "% Excellent"},
)
fig5.update_layout(height=550, margin=dict(t=10, b=10))
st.plotly_chart(fig5, use_container_width=True)

st.divider()
st.caption("Dashboard built with Streamlit · Data: European Environment Agency — Bathing Water Directive (1990–2024) · eea.europa.eu")
