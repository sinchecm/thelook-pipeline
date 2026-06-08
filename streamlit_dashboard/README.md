# TheLook Analytics Dashboard

A live analytics dashboard built with Streamlit, connecting directly to the
PostgreSQL data warehouse populated by the Dagster + dbt pipeline.

## Features

- **KPI cards** — Revenue, Orders, Customers, AOV, Margin, Return Rate
- **Monthly trend** — Revenue + Profit line chart with MoM % bars
- **Top categories** — Revenue and margin comparison
- **Customer segments** — RFM donut chart + LTV bars + segment details
- **Top products** — Interactive table with 15 top performers
- **Geographic map** — Revenue by country choropleth
- **Live filters** — Year, Category, Country
- **Auto-refresh** — Queries warehouse live, cache TTL 1 hour

## Run locally

```bash
cd dashboard
pip install -r requirements.txt

# Copy your .env from the pipeline project
cp ../thelook-pipeline/.env .env

streamlit run app.py
# Open: http://localhost:8501
```

## Deploy to Streamlit Cloud (free)

1. Push this folder to a GitHub repo
2. Go to share.streamlit.io → New app
3. Select your repo and `app.py`
4. Add secrets in the Streamlit Cloud dashboard:
   - Copy values from your `.env` file

```toml
# Streamlit Cloud secrets
DW_HOST = "your-host"
DW_PORT = "5433"
DW_DATABASE = "thelook_dw"
DW_USER = "pipeline_user"
DW_PASSWORD = "your-password"
```

5. Click Deploy — done!

## Auto-refresh

The dashboard uses `@st.cache_data(ttl=3600)` — all queries refresh
automatically every hour. After each Dagster pipeline run (02:00 UTC),
the dashboard will show fresh data within 1 hour.

To force an immediate refresh: press **R** or click the refresh button
in the top right of the Streamlit UI.
