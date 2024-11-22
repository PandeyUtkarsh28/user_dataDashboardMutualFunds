import streamlit as st
from streamlit_gsheets import GSheetsConnection
import plotly.express as px
import plotly.graph_objects as go
import duckdb
import pandas as pd

# Page Configuration
st.set_page_config(page_title="Client-Specific Holdings Dashboard", page_icon=":chart_with_upwards_trend:", layout="wide")
st.title("Client-Specific Holdings Dashboard")
st.markdown("Track individual client Profit and Loss (P&L) in investments across sectors with filters, KPIs, and charts")

# Google Sheets Connection
url = "https://docs.google.com/spreadsheets/d/1v7x1ePdj_Gq2Y1JNArXLMt9sThjjHvQ5u8wQKj969Y8/edit?usp=sharing"
conn = st.connection("gsheets", type=GSheetsConnection)

# Loading Data
@st.cache_data
def load_data(spreadsheet_url, worksheet_name):
    data = conn.read(spreadsheet=spreadsheet_url, worksheet=worksheet_name)
    return data

data = load_data(url, "358148778")

# Ensure required columns exist before proceeding
required_columns = ["Client ID", "Client Name", "Product Name", "Investment Amount", "Market Value", "Gain/Loss", "Sector", "Risk Level"]
missing_columns = [col for col in required_columns if col not in data.columns]

if missing_columns:
    st.error(f"The following required columns are missing from the dataset: {missing_columns}")
else:
    # Sidebar Filters
    st.sidebar.header("Data & Filters")
    st.sidebar.write("Select a client to view their investment details")
    clients = data["Client Name"].unique()
    selected_client = st.sidebar.selectbox("Select Client", clients)

    # Filter data based on the selected client
    client_data = data[data["Client Name"] == selected_client]

    #######################################
    # DISPLAY KPIs
    #######################################
    st.subheader(f"Key Performance Indicators (KPIs) for {selected_client}")

    def plot_kpi(label, value, prefix="", suffix="", color=""):
        fig = go.Figure(go.Indicator(
            mode="number+delta",
            value=value,
            number={"prefix": prefix, "suffix": suffix, "font.size": 24},
            title={"text": label, "font": {"size": 20}},
        ))
        fig.update_layout(height=90, margin=dict(t=20, b=0), plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        total_investment = client_data["Investment Amount"].sum()
        plot_kpi("Total Investment", total_investment, prefix="$")

    with kpi2:
        total_market_value = client_data["Market Value"].sum()
        plot_kpi("Total Market Value", total_market_value, prefix="$")

    with kpi3:
        net_gain_loss = total_market_value - total_investment
        plot_kpi("Net Gain/Loss", net_gain_loss, prefix="$")

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
    # VISUALIZATION FUNCTIONS
    #######################################

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

    #######################################
    # DASHBOARD LAYOUT
    #######################################
    st.subheader(f"Investment Performance by Sector and Holdings for {selected_client}")
    sector_col, holdings_col = st.columns(2)

    with sector_col:
        plot_sector_performance(client_data)

    with holdings_col:
        plot_top_holdings(client_data)

    #######################################
    # STYLING ENHANCEMENTS
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
    st.write("Use the sidebar to select a client and view specific data on their investment performance.")
