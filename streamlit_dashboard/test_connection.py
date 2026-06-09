import streamlit as st
import os

st.title("Connection Test")

try:
    import streamlit as st
    host = st.secrets.get("DW_HOST", os.getenv("DW_HOST", "NOT SET"))
    st.write(f"Host: {host}")
    st.write(f"Port: {st.secrets.get('DW_PORT', 'NOT SET')}")
    st.write(f"DB: {st.secrets.get('DW_DATABASE', 'NOT SET')}")
    st.write(f"User: {st.secrets.get('DW_USER', 'NOT SET')}")
except Exception as e:
    st.error(f"Error: {e}")
