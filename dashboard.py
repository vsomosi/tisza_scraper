import streamlit as st
import pandas as pd
import os
import plotly.express as px

# 1. Az oldal beállításai
st.set_page_config(page_title="Tiszadorogma Dashboard", layout="wide")
st.title("🌊 Tiszadorogma Vízállás és Hozam Dashboard")

# 2. Adatok beolvasása
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, "tiszadorogma_adatok.csv")

try:
    # CSV beolvasása pontosvessző elválasztóval
    df = pd.read_csv(csv_path, delimiter=';')
    
    # 3. Adattisztítás: a '//' jelek lecserélése és oszlopok számmá alakítása
    df.replace('//', pd.NA, inplace=True)
    df['Vízállás ma reggel'] = pd.to_numeric(df['Vízállás ma reggel'], errors='coerce')
    df['Vízállás tegnap este'] = pd.to_numeric(df['Vízállás tegnap este'], errors='coerce')
    df['Vízállás tegnap reggel'] = pd.to_numeric(df['Vízállás tegnap reggel'], errors='coerce')
    df['Reggeli hozam'] = pd.to_numeric(df['Reggeli hozam'], errors='coerce')
    
    # Dátum beállítása indexként, a felesleges szóközök eltávolításával a biztonságosabb felismeréshez
    df['Észlelés dátuma'] = pd.to_datetime(df['Észlelés dátuma'].astype(str).str.replace(' ', ''), format='%Y.%m.%d.', errors='coerce')
    df.set_index('Észlelés dátuma', inplace=True)

    # Az adatok szigorú időrendbe állítása, hogy a grafikon balról jobbra haladjon
    df.sort_index(inplace=True)

    # --- Vízállás idősor felépítése (Reggel és Este) ---
    # 1. Ma reggeli adatok (az adott naphoz tartozik, pl. 06:00)
    df_ma_reggel = df[['Vízállás ma reggel']].dropna().rename(columns={'Vízállás ma reggel': 'Vízállás'})
    df_ma_reggel.index = df_ma_reggel.index + pd.Timedelta(hours=6)

    # 2. Tegnap esti adatok (az előző naphoz tartozik, pl. 18:00)
    df_tegnap_este = df[['Vízállás tegnap este']].dropna().rename(columns={'Vízállás tegnap este': 'Vízállás'})
    df_tegnap_este.index = df_tegnap_este.index - pd.Timedelta(days=1) + pd.Timedelta(hours=18)

    # 3. Tegnap reggeli adatok (az előző nap reggeléhez tartozik, pl. 06:00)
    df_tegnap_reggel = df[['Vízállás tegnap reggel']].dropna().rename(columns={'Vízállás tegnap reggel': 'Vízállás'})
    df_tegnap_reggel.index = df_tegnap_reggel.index - pd.Timedelta(days=1) + pd.Timedelta(hours=6)

    # Összefűzzük, időrendbe tesszük, és a duplikált időpontokat kiszűrjük (így naponta csak 1 reggeli és 1 esti marad)
    vizallas_kombinalt = pd.concat([df_tegnap_reggel, df_tegnap_este, df_ma_reggel]).sort_index()
    vizallas_kombinalt = vizallas_kombinalt[~vizallas_kombinalt.index.duplicated(keep='last')]

    # 4. Grafikonok kirajzolása
    st.subheader("📈 Vízállás alakulása (cm)")
    
    # Plotly area grafikon a vízálláshoz (Modern, lekerekített, pontos X tengellyel)
    fig_viz = px.area(vizallas_kombinalt.reset_index(), x='Észlelés dátuma', y='Vízállás', 
                      markers=True, line_shape='spline')
    
    # Kiszámítjuk a tengelyfeliratok helyét (minden nap 12:00-kor, így pontosan a reggeli és esti érték közé esik)
    unique_dates = pd.Series(vizallas_kombinalt.index.date).unique()
    tickvals = [pd.Timestamp(d) + pd.Timedelta(hours=12) for d in unique_dates]
    ticktext = [d.strftime("%m.%d.") for d in unique_dates]
    
    # Grafikon tengelyeinek és megjelenésének finomhangolása
    fig_viz.update_layout(
        xaxis_title="", 
        yaxis_title="Vízállás (cm)",
        hovermode="x unified",
        xaxis=dict(
            tickmode='array', tickvals=tickvals, ticktext=ticktext, tickangle=0
        )
    )
    st.plotly_chart(fig_viz, use_container_width=True)

    st.subheader("💧 Reggeli hozam alakulása")
    
    # Plotly terület-görbe a hozamhoz (oszlopdiagram helyett)
    fig_hozam = px.area(df[['Reggeli hozam']].dropna().reset_index(), x='Észlelés dátuma', y='Reggeli hozam',
                        markers=True, line_shape='spline', color_discrete_sequence=['#00b4d8'])
    fig_hozam.update_layout(xaxis_title="", yaxis_title="Hozam", hovermode="x unified", xaxis=dict(tickformat="%m.%d."))
    st.plotly_chart(fig_hozam, use_container_width=True)
except FileNotFoundError:
    st.error("A CSV fájl még nem található. Kérlek futtasd le a scraper.py-t először!")