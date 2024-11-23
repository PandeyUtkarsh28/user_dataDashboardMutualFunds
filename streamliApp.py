import streamlit as st
from streamlit_gsheets import GSheetsConnection
import plotly.express as px
import plotly.graph_objects as go
import duckdb
import pandas as pd
import numpy as np

# Page Configuration
st.set_page_config(page_title="Enhanced Holdings Dashboard", page_icon=":chart_with_upwards_trend:", layout="wide")
st.title("Client-Specific Holdings Dashboard")
st.markdown("Analyze investments with insights into expected returns, target increase, and performance tracking.")

# Google Sheets Connection
url = "https://docs.google.com/spreadsheets/d/1bTT7R7hImTFME7ZLqpWrFp_ZqVFOCryh8iwemVos4EQ/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# Loading Data
@st.cache_data
def load_data(spreadsheet_url, worksheet_name):
    data = conn.read(spreadsheet=spreadsheet_url, worksheet=worksheet_name)
    return data

data = load_data(url, "290160618")

# Ensure required columns exist
required_columns = ["Client ID", "Client Name", "Product Name", "Investment Amount", "Market Value", 
                    "Gain/Loss", "Sector", "Risk Level", "Annualized Expected Growth", "Actual Annual Growth"]
missing_columns = [col for col in required_columns if col not in data.columns]

if missing_columns:
    st.error(f"The following required columns are missing from the dataset: {missing_columns}")
else:
    # Sidebar Filters: Select Client
    st.sidebar.header("Data & Filters")
    st.sidebar.write("Select a client to view specific details")
    clients = data["Client Name"].unique()
    selected_client = st.sidebar.selectbox("Select a Client", clients)

    # Filter data for the selected client
    client_data = data[data["Client Name"] == selected_client]

    # Display Client-Specific Data
    st.subheader(f"Investment Details for {selected_client}")
    st.dataframe(client_data)

    #######################################
    # KPI Section
    #######################################
    st.subheader(f"Key Performance Indicators (KPIs) for {selected_client}")

    def plot_kpi(label, value, prefix="", suffix="", color=""):
        fig = go.Figure(go.Indicator(
            mode="number",
            value=value,
            number={"prefix": prefix, "suffix": suffix, "font.size": 20},
            title={"text": label, "font": {"size": 18}},
        ))
        fig.update_layout(height=100, margin=dict(t=10, b=0), plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    # Calculate KPIs
    total_investment = client_data["Investment Amount"].sum()
    total_market_value = client_data["Market Value"].sum()
    net_gain_loss = total_market_value - total_investment
    annual_growth_required = client_data["Annualized Expected Growth"].mean()
    actual_annual_growth = client_data["Actual Annual Growth"].mean()

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    with kpi_col1:
        plot_kpi("Total Investment", total_investment, prefix="$")
    with kpi_col2:
        plot_kpi("Market Value", total_market_value, prefix="$")
    with kpi_col3:
        plot_kpi("Net Gain/Loss", net_gain_loss, prefix="$")
    with kpi_col4:
        plot_kpi("Target Annual Growth", annual_growth_required, suffix="%")

    #######################################
    # User Input for Expected Returns
    #######################################
    st.sidebar.subheader("Set Target Returns")
    target_increase = st.sidebar.number_input("Target Increase ($)", value=100000, step=10000)
    time_period = st.sidebar.number_input("Time Period (Years)", value=3, step=1)

    if target_increase > 0 and time_period > 0:
        expected_annual_growth = ((target_increase / total_investment) ** (1 / time_period) - 1) * 100
        st.sidebar.write(f"Expected Annual Growth to meet target: {expected_annual_growth:.2f}%")

    #######################################
    # DATA QUERYING & AT-RISK INVESTMENTS
    #######################################
    sql = """
    SELECT
        "Client ID",
        "Client Name",
        "Product Name",
        "Investment Amount",
        "Market Value",
        ("Market Value" - "Investment Amount") AS "Gain/Loss",
        "Sector",
        "Risk Level"
    FROM client_data
    WHERE "Market Value" < "Investment Amount"
    ORDER BY "Gain/Loss" ASC;
    """
    df_protip_data = duckdb.query(sql).df()
    st.subheader("At-Risk Investments")
    st.dataframe(df_protip_data)

    #######################################
    # Visualization Functions
    #######################################
    st.subheader("Investment Performance")

    def plot_sector_performance(client_data):
        sector_data = duckdb.query(
            """
            SELECT 
                "Sector",
                SUM("Investment Amount") AS "Total Invested",
                SUM("Market Value") AS "Total Market Value",
                SUM("Market Value" - "Investment Amount") AS "Net Gain/Loss"
            FROM client_data
            GROUP BY "Sector"
            ORDER BY "Net Gain/Loss" DESC
            """
        ).df()

        fig = px.bar(
            sector_data,
            x="Sector",
            y="Net Gain/Loss",
            text_auto=".2s",
            title=f"Net Gain/Loss by Sector for {selected_client}",
            color="Sector"
        )
        fig.update_traces(textfont_size=12, textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    def plot_top_holdings(client_data):
        top_holdings_data = duckdb.query(
            """
            SELECT 
                "Product Name",
                SUM("Investment Amount") AS "Total Invested"
            FROM client_data
            GROUP BY "Product Name"
            ORDER BY "Total Invested" DESC
            LIMIT 5
            """
        ).df()

        fig = px.pie(
            top_holdings_data,
            names="Product Name",
            values="Total Invested",
            title=f"Top Holdings by Investment Amount for {selected_client}"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Display Visualizations
    sector_col, holdings_col = st.columns(2)
    with sector_col:
        plot_sector_performance(client_data)
    with holdings_col:
        plot_top_holdings(client_data)

    #######################################
    # Styling Enhancements
    #######################################
    st.markdown(
        """
        <style>
        .stApp {background-color: #F8F9FA;}
        h1, h2, h3, h4, h5, h6 {color: #007BFF;}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.write("Refine insights with sidebar filters and explore sector-wise performance and top holdings.")
