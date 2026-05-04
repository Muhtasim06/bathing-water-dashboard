import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EU Bathing Water Quality",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Force light theme + dark text everywhere */
    .stApp { background-color: #f4f8fb; color: #1a1a1a !important; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; background-color: #f4f8fb; }
    
    /* Sidebar text - dark */
    [data-testid="stSidebar"] { color: #1a1a1a; }
    [data-baseweb="tag"] span { color: white !important; }
    
    /* Tab text */
    div[data-testid="stTabs"] button p { color: #546e7a !important; }
    div[data-testid="stTabs"] button[aria-selected="true"] p { color: #006064 !important; }
    
    /* Caption */
    [data-testid="stCaptionContainer"] p { color: #607d8b !important; font-size: 0.8rem !important; }

    /* Hero banner — teal/ocean theme */
    .hero {
        background: linear-gradient(135deg, #006064 0%, #00838f 60%, #00acc1 100%);
        border-radius: 16px;
        padding: 2.2rem 2.5rem;
        margin-bottom: 1.5rem;
        color: white;
    }
    .hero h1 {
        font-size: 2.1rem; font-weight: 800; margin: 0 0 0.4rem 0;
        letter-spacing: -0.5px; color: white;
    }
    .hero p { font-size: 1rem; margin: 0; opacity: 0.92; color: white; }
    .hero .badge {
        display: inline-block; background: rgba(255,255,255,0.2);
        border-radius: 20px; padding: 3px 14px; font-size: 0.78rem;
        margin-top: 0.9rem; margin-right: 6px; color: white;
        border: 1px solid rgba(255,255,255,0.3);
    }

    /* KPI cards */
    .kpi-card {
        background: white;
        border-radius: 14px;
        padding: 1.3rem 1.5rem;
        box-shadow: 0 2px 16px rgba(0,0,0,0.07);
        border-top: 4px solid #00838f;
        height: 100%;
    }
    .kpi-card.green  { border-top-color: #2e7d32; }
    .kpi-card.red    { border-top-color: #c62828; }
    .kpi-card.orange { border-top-color: #e65100; }
    .kpi-label { font-size: 0.72rem; font-weight: 700; color: #607d8b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
    .kpi-value { font-size: 2.1rem; font-weight: 800; color: #1a1a1a; line-height: 1; }
    .kpi-sub   { font-size: 0.75rem; color: #90a4ae; margin-top: 5px; }

    /* Section headers */
    .section-header {
        font-size: 1.1rem; font-weight: 700; color: #00695c;
        border-bottom: 2px solid #b2ebf2; padding-bottom: 0.5rem;
        margin-bottom: 1.2rem; margin-top: 0.5rem;
    }

    /* Insight box */
    .insight-box {
        background: #e0f7fa; border-radius: 12px;
        padding: 1rem 1.4rem; margin-top: 1rem;
        border-left: 4px solid #00838f;
        font-size: 0.88rem; color: #004d40;
    }
    .insight-box b { color: #006064; }

    /* Chart wrapper — white card */
    .chart-wrap {
        background: white; border-radius: 14px;
        padding: 1rem 0.5rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }

    /* Tabs */
    div[data-testid="stTabs"] button {
        font-weight: 600; font-size: 0.88rem; color: #546e7a;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #006064;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e0f7fa 0%, #f4f8fb 100%);
        border-right: 1px solid #b2ebf2;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Global Plotly theme ──────────────────────────────────────────────────────
import plotly.io as pio
pio.templates["clean_light"] = go.layout.Template(
    layout=go.Layout(
        font=dict(family="Arial, sans-serif", color="#1a1a1a", size=12),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        colorway=["#006064","#2E7D32","#F57F17","#B71C1C","#90A4AE","#558B2F"],
        title=dict(font=dict(color="#006064", size=15)),
        legend=dict(font=dict(color="#1a1a1a"), bgcolor="rgba(255,255,255,0.8)"),
        xaxis=dict(gridcolor="#f0f0f0", linecolor="#cfd8dc", tickfont=dict(color="#1a1a1a")),
        yaxis=dict(gridcolor="#f0f0f0", linecolor="#cfd8dc", tickfont=dict(color="#1a1a1a")),
    )
)
pio.templates.default = "clean_light"

# ── Colour palette ─────────────────────────────────────────────────────────────
COLOURS = {
    "Excellent":          "#006064",
    "Good":               "#2E7D32",
    "Sufficient":         "#F57F17",
    "Poor":               "#B71C1C",
    "Not Classified":     "#90A4AE",
    "Good Or Sufficient": "#558B2F",
}

def q_colour(q):
    q = str(q)
    for k, v in COLOURS.items():
        if k.lower() in q.lower():
            return v
    return "#9E9E9E"

COUNTRY_NAMES = {
    "AT":"Austria","BE":"Belgium","BG":"Bulgaria","CY":"Cyprus","CZ":"Czech Republic",
    "DE":"Germany","DK":"Denmark","EE":"Estonia","EL":"Greece","ES":"Spain",
    "FI":"Finland","FR":"France","HR":"Croatia","HU":"Hungary","IE":"Ireland",
    "IT":"Italy","LT":"Lithuania","LU":"Luxembourg","LV":"Latvia","MT":"Malta",
    "NL":"Netherlands","PL":"Poland","PT":"Portugal","RO":"Romania","SE":"Sweden",
    "SI":"Slovenia","SK":"Slovakia","AL":"Albania","ME":"Montenegro","RS":"Serbia",
    "TR":"Turkey","CH":"Switzerland","NO":"Norway","IS":"Iceland","LI":"Liechtenstein",
}

# ── Load data ─────────────────────────────────────────────────────────────────
DATA_URL = "https://sdi.eea.europa.eu/datashare/s/J86aarkSmCMXpkc/download?path=%2F&files=bw_assessment_eea_datahub_1990_2024.xlsx"

@st.cache_data(show_spinner="🌊 Loading EEA Bathing Water dataset…")
def load_data():
    import io, requests
    r = requests.get(DATA_URL)
    xl = pd.ExcelFile(io.BytesIO(r.content), engine="openpyxl")
    best_sheet, best_cols = None, 0
    for sheet in xl.sheet_names:
        try:
            tmp = xl.parse(sheet, nrows=2)
            if len(tmp.columns) > best_cols:
                best_cols = len(tmp.columns)
                best_sheet = sheet
        except:
            pass
    return xl.parse(best_sheet)

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

# ── Clean data ────────────────────────────────────────────────────────────────
df = df_raw.rename(columns={
    "countryCode":      "country",
    "quality":          "quality",
    "bathingWaterType": "water_type",
    "bathingWaterName": "site_name",
    "lat": "lat", "lon": "lon",
}).copy()

# Find year column
if "year" not in df.columns:
    for c in df.columns:
        if "season" in c.lower() or "year" in c.lower():
            df = df.rename(columns={c: "year"})
            break

df["year"] = pd.to_numeric(df["year"], errors="coerce")
df = df.dropna(subset=["year"])
df["year"] = df["year"].astype(int)

# Clean quality labels
df["quality"] = (df["quality"].astype(str)
    .str.strip()
    .str.replace(r"^\d+\s*[-–]\s*", "", regex=True)
    .str.strip()
    .str.title()
)

# Clean water type labels
def clean_wt(wt):
    wt = str(wt).replace("BathingWater", "").replace("bathing_water", "")
    wt = re.sub(r"([A-Z])", r" \1", wt).strip().title()
    return wt or "Unknown"

df["water_type"] = df["water_type"].apply(clean_wt)
df["country_name"] = df["country"].map(COUNTRY_NAMES).fillna(df["country"])

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔧 Dashboard Filters")
    st.markdown("Use the filters below to explore the data interactively.")
    st.divider()

    min_y, max_y = int(df["year"].min()), int(df["year"].max())
    year_range = st.slider("📅 Year Range", min_y, max_y, (2010, max_y))

    st.markdown("")
    countries = sorted(df["country"].dropna().unique())
    selected_countries = st.multiselect("🌍 Countries", countries, default=countries)

    st.markdown("")
    water_types = sorted(df["water_type"].dropna().unique())
    selected_types = st.multiselect("💧 Water Type", water_types, default=water_types)

    st.markdown("")
    qualities = sorted(df["quality"].dropna().unique())
    selected_qualities = st.multiselect("⭐ Quality Rating", qualities, default=qualities)

    st.divider()
    st.caption("📊 Data: European Environment Agency\nBathing Water Directive (1990–2024)\n[eea.europa.eu](https://www.eea.europa.eu)")

# ── Filter data ───────────────────────────────────────────────────────────────
df_f = df[
    (df["year"] >= year_range[0]) &
    (df["year"] <= year_range[1]) &
    (df["country"].isin(selected_countries)) &
    (df["water_type"].isin(selected_types)) &
    (df["quality"].isin(selected_qualities))
]

total     = len(df_f)
n_ctry    = df_f["country"].nunique()
n_sites   = df_f["site_name"].nunique() if "site_name" in df_f.columns else "N/A"
exc_pct   = round(df_f["quality"].str.lower().str.contains("excell").sum() / total * 100, 1) if total else 0
poor_pct  = round(df_f["quality"].str.lower().str.contains("poor").sum()  / total * 100, 1) if total else 0

# ── Hero Banner ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="hero">
    <h1>🌊 European Bathing Water Quality Dashboard</h1>
    <p>Monitoring water safety across Europe from <b>1990 to 2024</b> — 
    helping policymakers, sustainability professionals and the public understand 
    the health of our bathing waters.</p>
    <span class="badge">📅 {year_range[0]}–{year_range[1]}</span>
    <span class="badge">🌍 {n_ctry} Countries</span>
    <span class="badge">📋 {total:,} Records</span>
    <span class="badge">Source: EEA Bathing Water Directive</span>
</div>
""", unsafe_allow_html=True)

# ── KPI Cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="kpi-card">
        <div class="kpi-label">Total Records</div>
        <div class="kpi-value">{total:,}</div>
        <div class="kpi-sub">assessments in selected range</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="kpi-card green">
        <div class="kpi-label">Excellent Quality</div>
        <div class="kpi-value">{exc_pct}%</div>
        <div class="kpi-sub">of sites meet highest standard</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="kpi-card red">
        <div class="kpi-label">Poor Quality</div>
        <div class="kpi-value">{poor_pct}%</div>
        <div class="kpi-sub">of sites below minimum standard</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class="kpi-card orange">
        <div class="kpi-label">Unique Sites</div>
        <div class="kpi-value">{n_sites:,}</div>
        <div class="kpi-sub">bathing locations monitored</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊  Overview",
    "📈  Trends Over Time",
    "🏳️  Country Analysis",
    "🗺️  Map View",
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — Overview
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("<div class='section-header'>Quality Rating Breakdown & Water Type Comparison</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        qc = df_f["quality"].value_counts().reset_index()
        qc.columns = ["Quality", "Count"]
        qc["pct"] = (qc["Count"] / qc["Count"].sum() * 100).round(1)

        fig1 = go.Figure(go.Pie(
            labels=qc["Quality"],
            values=qc["Count"],
            hole=0.52,
            marker_colors=[q_colour(q) for q in qc["Quality"]],
            textinfo="label+percent",
            textfont_size=12,
            hovertemplate="<b>%{label}</b><br>Sites: %{value:,}<br>Share: %{percent}<extra></extra>",
        ))
        fig1.update_layout(
            title=dict(text="Quality Rating Distribution", font_size=15, font_color="#006064"),
            height=370,
            margin=dict(t=50, b=20, l=10, r=10),
            legend=dict(orientation="h", yanchor="top", y=-0.05, font=dict(color="#1a1a1a")),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        tv = df_f.groupby(["water_type", "quality"]).size().reset_index(name="count")
        fig2 = px.bar(
            tv, x="water_type", y="count", color="quality",
            barmode="stack",
            color_discrete_map={q: q_colour(q) for q in tv["quality"].unique()},
            labels={"water_type": "Water Type", "count": "Number of Sites", "quality": "Quality"},
        )
        fig2.update_layout(
            title=dict(text="Sites by Water Type & Quality", font_size=15, font_color="#006064"),
            height=370,
            margin=dict(t=50, b=20, l=10, r=10),
            legend=dict(orientation="h", yanchor="top", y=-0.05, font=dict(color="#1a1a1a")),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            font=dict(color="#1a1a1a"),
            xaxis=dict(showgrid=False, color="#1a1a1a"),
            yaxis=dict(gridcolor="#f0f0f0", color="#1a1a1a"),
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown(f"""<div class="insight-box">
        💡 <b>Key Insight:</b> Across the selected period, <b>{exc_pct}%</b> of all bathing water 
        assessments achieved <b>Excellent</b> status — the highest classification under the EU 
        Bathing Water Directive. Coastal sites consistently account for the largest share of 
        monitored locations, reflecting Europe's extensive coastline.
    </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — Trends Over Time
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("<div class='section-header'>How has bathing water quality changed over time?</div>", unsafe_allow_html=True)

    trend = df_f.groupby(["year", "quality"]).size().reset_index(name="count")
    fig3 = px.line(
        trend, x="year", y="count", color="quality",
        markers=True,
        color_discrete_map={q: q_colour(q) for q in trend["quality"].unique()},
        labels={"year": "Year", "count": "Number of Sites", "quality": "Quality Rating"},
    )
    fig3.update_traces(line=dict(width=2.5), marker=dict(size=5))
    fig3.update_layout(
        title=dict(text="Bathing Water Quality Trend (1990–2024)", font_size=15, font_color="#006064"),
        height=420,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, title=None, font=dict(color="#1a1a1a")),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        xaxis=dict(showgrid=False, title="Year"),
        yaxis=dict(gridcolor="#f0f0f0", title="Number of Sites"),
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("""<div class="insight-box">
        💡 <b>Key Insight:</b> The number of sites rated <b>Excellent</b> has grown steadily 
        since the Bathing Water Directive was strengthened in 2006, rising from around 14,000 
        to nearly 20,000 sites by 2024. This reflects both improved water quality and an 
        expansion in the number of monitored bathing sites across Europe.
    </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>Monitoring Coverage Over Time</div>", unsafe_allow_html=True)

    coverage = df_f.groupby("year").size().reset_index(name="total_sites")
    fig4 = px.area(
        coverage, x="year", y="total_sites",
        labels={"year": "Year", "total_sites": "Total Assessments"},
        color_discrete_sequence=["#1565C0"],
    )
    fig4.update_traces(fill="tozeroy", fillcolor="rgba(21,101,192,0.12)", line_color="#1565C0")
    fig4.update_layout(
        title=dict(text="Total Annual Assessments Across Europe", font_size=15, font_color="#006064"),
        height=300,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#f0f0f0"),
        margin=dict(t=50, b=20),
    )
    st.plotly_chart(fig4, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — Country Analysis
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("<div class='section-header'>Compare bathing water quality across European countries</div>", unsafe_allow_html=True)

    available_years = sorted(df_f["year"].unique(), reverse=True)
    if available_years:
        sel_year = st.select_slider(
            "Select year for country comparison",
            options=available_years,
            value=available_years[0],
        )
        df_yr = df_f[df_f["year"] == sel_year]
        cq = df_yr.groupby(["country", "quality"]).size().reset_index(name="count")

        fig5 = px.bar(
            cq, x="country", y="count", color="quality",
            barmode="stack",
            color_discrete_map={q: q_colour(q) for q in cq["quality"].unique()},
            labels={"country": "Country Code", "count": "Number of Sites", "quality": "Quality"},
        )
        fig5.update_layout(
            title=dict(text=f"Bathing Water Quality by Country — {sel_year}", font_size=15, font_color="#006064"),
            height=430,
            xaxis_tickangle=-45,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, title=None, font=dict(color="#1a1a1a")),
            paper_bgcolor="#ffffff",
            plot_bgcolor="#ffffff",
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor="#f0f0f0"),
            bargap=0.25,
        )
        st.plotly_chart(fig5, use_container_width=True)

        # Top/bottom performers
        perf = df_yr.copy()
        perf["is_exc"] = perf["quality"].str.lower().str.contains("excell")
        perf_grp = perf.groupby("country").agg(total=("quality","count"), excellent=("is_exc","sum")).reset_index()
        perf_grp["pct"] = (perf_grp["excellent"] / perf_grp["total"] * 100).round(1)
        perf_grp["country_name"] = perf_grp["country"].map(COUNTRY_NAMES).fillna(perf_grp["country"])
        perf_grp = perf_grp[perf_grp["total"] >= 10].sort_values("pct", ascending=False)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("#### 🏆 Top 5 Countries by % Excellent")
            top5 = perf_grp.head(5)[["country_name","pct","total"]].rename(
                columns={"country_name":"Country","pct":"% Excellent","total":"Sites"})
            st.dataframe(top5, hide_index=True, use_container_width=True)
        with col_b:
            st.markdown("#### ⚠️ Bottom 5 Countries by % Excellent")
            bot5 = perf_grp.tail(5)[["country_name","pct","total"]].rename(
                columns={"country_name":"Country","pct":"% Excellent","total":"Sites"})
            st.dataframe(bot5, hide_index=True, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — Map View
# ════════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-header'>Geographic distribution of bathing water quality across Europe</div>", unsafe_allow_html=True)

    map_metric = st.radio(
        "Colour map by:",
        ["% Excellent Quality", "% Poor Quality", "Total Sites Monitored"],
        horizontal=True,
    )

    total_by_c = df_f.groupby("country").size().reset_index(name="total")
    exc_by_c   = (df_f[df_f["quality"].str.lower().str.contains("excell")]
                  .groupby("country").size().reset_index(name="excellent"))
    poor_by_c  = (df_f[df_f["quality"].str.lower().str.contains("poor")]
                  .groupby("country").size().reset_index(name="poor"))

    map_df = (total_by_c
              .merge(exc_by_c,  on="country", how="left")
              .merge(poor_by_c, on="country", how="left")
              .fillna(0))
    map_df["pct_excellent"] = (map_df["excellent"] / map_df["total"] * 100).round(1)
    map_df["pct_poor"]      = (map_df["poor"]      / map_df["total"] * 100).round(1)
    map_df["country_name"]  = map_df["country"].map(COUNTRY_NAMES).fillna(map_df["country"])

    if map_metric == "% Excellent Quality":
        col, scale, title = "pct_excellent", "Blues", "% Excellent Quality"
        rng = (0, 100)
    elif map_metric == "% Poor Quality":
        col, scale, title = "pct_poor", "Reds", "% Poor Quality"
        rng = (0, 10)
    else:
        col, scale, title = "total", "Greens", "Total Sites"
        rng = (0, map_df["total"].max())

    fig6 = px.choropleth(
        map_df,
        locations="country_name",
        locationmode="country names",
        color=col,
        color_continuous_scale=scale,
        range_color=rng,
        scope="europe",
        hover_name="country_name",
        hover_data={
            "pct_excellent": ":.1f",
            "pct_poor": ":.1f",
            "total": ":,",
            col: False,
        },
        labels={"pct_excellent": "% Excellent", "pct_poor": "% Poor", "total": "Total Sites"},
    )
    fig6.update_layout(
        title=dict(text=f"Europe — {title} ({year_range[0]}–{year_range[1]})", font_size=15, font_color="#006064"),
        height=560,
        margin=dict(t=50, b=10, l=0, r=0),
        paper_bgcolor="#ffffff",
        coloraxis_colorbar=dict(title=title, thickness=14),
        geo=dict(
            bgcolor="#f4f8fb",
            lakecolor="#b2ebf2",
            landcolor="#eceff1",
            showocean=True,
            oceancolor="#b2ebf2",
            showlakes=True,
            showrivers=True,
            rivercolor="#b2ebf2",
            showcountries=True,
            countrycolor="#cfd8dc",
            showcoastlines=True,
            coastlinecolor="#90a4ae",
        ),
    )
    st.plotly_chart(fig6, use_container_width=True)

    st.markdown("""<div class="insight-box">
        💡 <b>Key Insight:</b> Mediterranean countries such as <b>Greece, Cyprus and Malta</b> 
        consistently achieve the highest proportions of Excellent-rated coastal bathing waters, 
        benefiting from warm, low-rainfall climates that reduce agricultural and urban runoff 
        into bathing areas.
    </div>""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("""
<div style='text-align:center; color:#888; font-size:0.8rem; padding: 0.5rem 0 1rem 0;'>
    🌊 European Bathing Water Quality Dashboard &nbsp;|&nbsp; 
    Data: <a href='https://www.eea.europa.eu' target='_blank' style='color:#1565c0;'>European Environment Agency</a> 
    — Bathing Water Directive (1990–2024) &nbsp;|&nbsp; Built with Streamlit & Plotly
</div>
""", unsafe_allow_html=True)
