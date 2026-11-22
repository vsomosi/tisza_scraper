from __future__ import annotations

import os
import pandas as pd
import plotly.express as px
import streamlit as st


def render(show_title: bool = True) -> None:
    """Megjeleníti a klasszikus (v1) Tiszadorogma dashboardot."""
    if show_title:
        st.title("🌊 Tiszadorogma Vízállás és Hozam Dashboard")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "tiszadorogma_adatok.csv")

    try:
        # CSV beolvasása pontosvessző elválasztóval
        df = pd.read_csv(csv_path, delimiter=";", encoding="utf-8-sig", on_bad_lines="skip")

        # Adattisztítás: a '//' jelek lecserélése és oszlopok számmá alakítása
        df.replace("//", pd.NA, inplace=True)
        df["Vízállás ma reggel"] = pd.to_numeric(df["Vízállás ma reggel"].astype(str).str.replace(",", "."), errors="coerce")
        df["Vízállás tegnap este"] = pd.to_numeric(df["Vízállás tegnap este"].astype(str).str.replace(",", "."), errors="coerce")
        df["Vízállás tegnap reggel"] = pd.to_numeric(df["Vízállás tegnap reggel"].astype(str).str.replace(",", "."), errors="coerce")
        df["Reggeli hozam"] = pd.to_numeric(df["Reggeli hozam"].astype(str).str.replace(",", "."), errors="coerce")

        # Dátum beállítása indexként, a felesleges szóközök eltávolításával a biztonságosabb felismeréshez
        df["Észlelés dátuma"] = pd.to_datetime(df["Észlelés dátuma"].astype(str).str.replace(" ", ""), format="%Y.%m.%d.", errors="coerce")
        df.set_index("Észlelés dátuma", inplace=True)

        # Az adatok szigorú időrendbe állítása, hogy a grafikon balról jobbra haladjon
        df.sort_index(inplace=True)

        # --- Vízállás idősor felépítése (Reggel és Este) ---
        df_ma_reggel = df[["Vízállás ma reggel"]].dropna().rename(columns={"Vízállás ma reggel": "Vízállás"})
        df_ma_reggel.index = df_ma_reggel.index + pd.Timedelta(hours=6)

        df_tegnap_este = df[["Vízállás tegnap este"]].dropna().rename(columns={"Vízállás tegnap este": "Vízállás"})
        df_tegnap_este.index = df_tegnap_este.index - pd.Timedelta(days=1) + pd.Timedelta(hours=18)

        df_tegnap_reggel = df[["Vízállás tegnap reggel"]].dropna().rename(columns={"Vízállás tegnap reggel": "Vízállás"})
        df_tegnap_reggel.index = df_tegnap_reggel.index - pd.Timedelta(days=1) + pd.Timedelta(hours=6)

        vizallas_kombinalt = pd.concat([df_tegnap_reggel, df_tegnap_este, df_ma_reggel]).sort_index()
        vizallas_kombinalt = vizallas_kombinalt[~vizallas_kombinalt.index.duplicated(keep="last")]

        # --- Időszak szűrése csúszkával ---
        min_date = df.index.min().date()
        max_date = df.index.max().date()

        if min_date < max_date:
            default_start = (df.index.max() - pd.Timedelta(days=14)).date()
            default_start = max(min_date, default_start)
            start_date, end_date = st.slider(
                "📅 Időszak kiválasztása (alapértelmezés: utolsó 2 hét):",
                min_value=min_date,
                max_value=max_date,
                value=(default_start, max_date),
                format="YYYY.MM.DD",
            )
        else:
            start_date, end_date = min_date, max_date

        vizallas_filtered = vizallas_kombinalt[
            (vizallas_kombinalt.index.date >= start_date) & (vizallas_kombinalt.index.date <= end_date)
        ]
        df_filtered = df[(df.index.date >= start_date) & (df.index.date <= end_date)]

        # Grafikonok kirajzolása
        st.subheader("📈 Vízállás alakulása (cm)")
        fig_viz = px.area(
            vizallas_filtered.reset_index(),
            x="Észlelés dátuma",
            y="Vízállás",
            markers=True,
            line_shape="spline",
        )

        unique_dates = pd.Series(vizallas_filtered.index.date).unique()
        tickvals = [pd.Timestamp(d) + pd.Timedelta(hours=12) for d in unique_dates]
        ticktext = [d.strftime("%m.%d.") for d in unique_dates]

        fig_viz.update_layout(
            xaxis_title="",
            yaxis_title="Vízállás (cm)",
            hovermode="x unified",
            xaxis=dict(tickmode="array", tickvals=tickvals, ticktext=ticktext, tickangle=0),
        )
        st.plotly_chart(fig_viz, use_container_width=True)

        st.subheader("💧 Reggeli hozam alakulása")
        fig_hozam = px.area(
            df_filtered[["Reggeli hozam"]].dropna().reset_index(),
            x="Észlelés dátuma",
            y="Reggeli hozam",
            markers=True,
            line_shape="spline",
            color_discrete_sequence=["#00b4d8"],
            text="Reggeli hozam",
        )
        fig_hozam.update_traces(textposition="top center")
        fig_hozam.update_layout(
            xaxis_title="",
            yaxis_title="Hozam",
            hovermode="x unified",
            xaxis=dict(tickformat="%m.%d."),
        )
        st.plotly_chart(fig_hozam, use_container_width=True)
    except FileNotFoundError:
        st.error("A CSV fájl még nem található. Kérlek futtasd le a scraper.py-t először!")


if __name__ == "__main__":
    st.set_page_config(page_title="Tiszadorogma Dashboard", layout="wide")
    render()
