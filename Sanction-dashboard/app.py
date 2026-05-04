import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import os
import pycountry

st.set_page_config(
    page_title="Sanctions Network Dashboard",
    layout="wide"
)

st.markdown("""
<style>
    .stApp {
        background-color: #05080d;
        color: white;
    }
    [data-testid="stSidebar"] {
        background-color: #10131a;
    }
</style>
""", unsafe_allow_html=True)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(
    BASE_DIR,
    "Sanction-db-generators",
    "Sanction-db-files",
    "sanctions_network.db"
)

def iso2_to_iso3(code):
    try:
        return pycountry.countries.get(alpha_2=code).alpha_3
    except:
        return None


@st.cache_data
def load_entities():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM entities", conn)
    conn.close()
    return df

df = load_entities()

st.title("Sanctions Entity Intelligence Dashboard")

# --- Metrics ---
total_entities = len(df)
high_risk = len(df[df["Risk_score"] == 3])
medium_risk = len(df[df["Risk_score"] == 2])
low_risk = len(df[df["Risk_score"] == 1])
corporates = len(df[df["Entity_type"] == "C"])
private = len(df[df["Entity_type"] == "P"])

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric("Total Entities", total_entities)
col2.metric("Low Risk", low_risk)
col3.metric("Medium Risk", medium_risk)
col4.metric("High Risk", high_risk)
col5.metric("Corporates", corporates)
col6.metric("Private", private)

# --- Filters ---
st.sidebar.header("Filters")

risk_filter = st.sidebar.multiselect(
    "Risk Score",
    sorted(df["Risk_score"].dropna().unique()),
    default=sorted(df["Risk_score"].dropna().unique())
)

type_filter = st.sidebar.multiselect(
    "Entity Type",
    sorted(df["Entity_type"].dropna().unique()),
    default=sorted(df["Entity_type"].dropna().unique())
)

filtered = df[
    (df["Risk_score"].isin(risk_filter)) &
    (df["Entity_type"].isin(type_filter))
]

# --- Country aggregation ---
country_summary = (
    filtered
    .groupby("Registered_country")
    .agg(
        entity_count=("Entity_ID", "count"),
        avg_risk=("Risk_score", "mean"),
        high_risk_count=("Risk_score", lambda x: (x == 3).sum())
    )
    .reset_index()
)

country_summary["iso3"] = country_summary["Registered_country"].apply(iso2_to_iso3)
country_summary = country_summary.dropna(subset=["iso3"])

# --- Map ---
st.subheader("Registered Entity Breakdown by Country")

metric = st.sidebar.selectbox(
    "Map Metric",
    ["entity_count", "avg_risk", "high_risk_count"]
)

fig_map = px.choropleth(
    country_summary,
    locations="iso3",
    color=metric,
    hover_name="Registered_country",
    hover_data={
        "entity_count": True,
        "avg_risk": ":.2f",
        "high_risk_count": True,
        "iso3": False
    },
    color_continuous_scale=[
        [0.0, "#1b1b1b"],
        [0.3, "#5c1f1f"],
        [0.6, "#b22222"],
        [1.0, "#ff2e2e"]
    ],
    projection="natural earth"
)

fig_map.update_geos(
    showframe=False,
    showcoastlines=True,
    coastlinecolor="#555555",
    showland=True,
    landcolor="#111111",
    showocean=True,
    oceancolor="#05080d",
    showcountries=True,
    countrycolor="#333333",
    bgcolor="#05080d"
)

fig_map.update_layout(
    height=720,
    paper_bgcolor="#05080d",
    plot_bgcolor="#05080d",
    font=dict(color="white"),
    margin=dict(l=0, r=0, t=10, b=0),
    coloraxis_colorbar=dict(
        title=dict(
            text=metric,
            font=dict(color="white")
        ),
        tickfont=dict(color="white")
    )
)

st.plotly_chart(fig_map, width="stretch")

# --- Charts ---
left, right = st.columns(2)

with left:
    st.subheader("Risk Score Distribution")
    risk_chart = filtered["Risk_score"].value_counts().reset_index()
    risk_chart.columns = ["Risk_score", "count"]

    fig_risk = px.bar(
        risk_chart,
        x="Risk_score",
        y="count"
    )

    st.plotly_chart(fig_risk, width="stretch")

with right:
    st.subheader("Entity Type Breakdown")
    type_chart = filtered["Entity_type"].value_counts().reset_index()
    type_chart.columns = ["Entity_type", "count"]

    fig_type = px.pie(
        type_chart,
        names="Entity_type",
        values="count"
    )

    st.plotly_chart(fig_type, width="stretch")

# --- Data table ---
st.subheader("Entity Records")
st.dataframe(filtered, width="stretch")