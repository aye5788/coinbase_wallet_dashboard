import streamlit as st

def cache(ttl=300):
    return st.cache_data(ttl=ttl, show_spinner=False)

