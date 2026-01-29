import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
import google.generativeai as genai
from PIL import Image
from datetime import datetime, date
import folium
from folium.plugins import LocateControl, Fullscreen
from streamlit_folium import st_folium
from streamlit_google_auth import Authenticate

# --- 1. CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(page_title="Agro-Intel Enterprise", page_icon="🛰️", layout="wide")

# --- LOGIN REAL COM GOOGLE (SINCRONIZADO COM SECRETS) ---
try:
    # IMPORTANTE: Esta URL deve ser IGUAL à cadastrada no Google Cloud Console
    URL_DO_APP = "https://monitoramento-agricola.streamlit.app" 

    authenticator = Authenticate(
        client_id=st.secrets["GOOGLE_CLIENT_ID"],
        client_secret=st.secrets["GOOGLE_CLIENT_SECRET"],
        redirect_uri=URL_DO_APP,
        cookie_name="agro_intel_session",
        key="agro_secret_key_2026", 
        cookie_expiry_days=30
    )
except Exception as e:
    st.error(f"Erro na configuração de Autenticação: {e}")
    st.stop()

authenticator.check_authenticity()

if not st.session_state.get('connected'):
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
            <div style="text-align: center; padding: 50px; background: white; border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.15);">
                <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_\"G\"_Logo.svg" width="60">
                <h1 style="color: #064e3b; margin-top: 20px; font-weight: 800;">Agro-Intel Pro</h1>
                <p style="color: #64748b;">Acesse com sua conta oficial Google</p>
            </div>
        """, unsafe_allow_html=True)
        authenticator.login()
        st.stop()

# --- VARIÁVEIS DE AMBIENTE ---
USER_EMAIL = st.session_state.get('email')
USER_NAME = st.session_state.get('name', 'Engenheiro Agrônomo')
USER_PIC = st.session_state.get('picture', "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")

WEATHER_KEY = st.secrets["OPENWEATHER_KEY"]
GEMINI_KEY = st.secrets["GEMINI_KEY"]

# ... (Todo o BANCO_MASTER e lógica de GDA permanecem os mesmos) ...

# --- COMPONENTE VISUAL TÉCNICO ---
# Adicionando o monitoramento de maturação térmica para a batata
# 

# --- ABA 1: CONSULTORIA TÉCNICA (EXEMPLO DE CÁLCULO GDA) ---
# Cálculo de Graus-Dia Acumulados: $GDA = \sum (T_{media} - T_{base})$
# Se a batata Orchestra foi plantada há 60 dias e a média térmica é 22°C:
# GDA Estimado = 60 * (22 - 7) = 900 GDA.
