from __future__ import annotations

import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}


@st.cache_data(ttl=300)
def load_data(csv_path: str) -> tuple[pd.DataFrame, pd.Series]:
    """Beolvassa és előkészíti a napi adatokat és a reggel/este bontású vízállás idősort."""
    df = pd.read_csv(csv_path, delimiter=";", encoding="utf-8-sig", on_bad_lines="skip")
    df.replace("//", pd.NA, inplace=True)

    numeric_cols = [
        "Vízállás ma reggel",
        "Vízállás tegnap este",
        "Vízállás tegnap reggel",
        "Változás 24 óra alatt",
        "Reggeli hozam",
        "Reggeli víz hőmérséklet",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "."), errors="coerce")

    df["Észlelés dátuma"] = pd.to_datetime(
        df["Észlelés dátuma"].astype(str).str.replace(" ", ""),
        format="%Y.%m.%d.",
        errors="coerce",
    )
    df = df.dropna(subset=["Észlelés dátuma"]).set_index("Észlelés dátuma").sort_index()

    # Reggeli (06:00) és esti (18:00) vízállás idősor összeállítása
    parts = []
    for col, day_offset, hour in [
        ("Vízállás tegnap reggel", -1, 6),
        ("Vízállás tegnap este", -1, 18),
        ("Vízállás ma reggel", 0, 6),
    ]:
        s = df[col].dropna()
        s.index = s.index + pd.Timedelta(days=day_offset, hours=hour)
        parts.append(s)

    water_series = pd.concat(parts).sort_index()
    water_series = water_series[~water_series.index.duplicated(keep="last")]
    water_series.name = "Vízállás"
    return df, water_series


@st.cache_data(ttl=300)
def load_pressure_data(csv_path: str) -> pd.Series:
    """Beolvassa a legnyomas_adatok.csv órás légnyomás idősorát."""
    if not os.path.isfile(csv_path):
        return pd.Series(dtype=float, name="Légnyomás (hPa)")
    p_df = pd.read_csv(csv_path, delimiter=";", encoding="utf-8-sig", on_bad_lines="skip")
    if p_df.empty or "Időpont" not in p_df.columns or "Légnyomás (hPa)" not in p_df.columns:
        return pd.Series(dtype=float, name="Légnyomás (hPa)")
    p_df["Időpont"] = pd.to_datetime(p_df["Időpont"], errors="coerce")
    p_df["Légnyomás (hPa)"] = pd.to_numeric(
        p_df["Légnyomás (hPa)"].astype(str).str.replace(",", "."), errors="coerce"
    )
    p_df = p_df.dropna(subset=["Időpont", "Légnyomás (hPa)"]).set_index("Időpont").sort_index()
    p_series = p_df["Légnyomás (hPa)"]
    p_series = p_series[~p_series.index.duplicated(keep="last")]
    return p_series


def format_delta_badge(delta: float | None, unit: str) -> tuple[str, str]:
    """Visszaadja a változás szövegét és CSS osztályát."""
    if delta is None or pd.isna(delta):
        return "Nincs előző adat", "badge-flat"
    if delta > 0:
        return f"▲ +{delta:g} {unit} (24ó)", "badge-up"
    if delta < 0:
        return f"▼ {delta:g} {unit} (24ó)", "badge-down"
    return f"● 0 {unit} (24ó)", "badge-flat"


def mobile_plotly_layout(fig: go.Figure, yaxis_title: str, height: int = 330) -> go.Figure:
    """Egységes, mobilbarát Plotly elrendezés (görgetésbarát fix tengelyekkel)."""
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=28, b=8),
        hovermode="x unified",
        dragmode=False,
        xaxis=dict(
            title="",
            fixedrange=True,
            showgrid=False,
            tickformat="%m.%d.",
        ),
        yaxis=dict(
            title=yaxis_title,
            fixedrange=True,
            gridcolor="rgba(128,128,128,0.15)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def render() -> None:
    """Megjeleníti a mobilbarát (v2) Tiszadorogma dashboardot."""
    st.markdown(
        """
        <style>
            .block-container {
                padding-top: 3.5rem;
                padding-bottom: 2rem;
                padding-left: 1rem;
                padding-right: 1rem;
                max-width: 1100px;
            }
            .hero-header {
                display: flex;
                flex-wrap: wrap;
                justify-content: space-between;
                align-items: baseline;
                gap: 0.4rem;
                margin-bottom: 0.75rem;
            }
            .hero-title {
                font-size: clamp(1.35rem, 4vw, 2rem);
                font-weight: 700;
                margin: 0;
                line-height: 1.2;
            }
            .hero-subtitle {
                font-size: 0.85rem;
                opacity: 0.75;
            }
            .kpi-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.65rem;
                margin-bottom: 1rem;
            }
            @media (min-width: 768px) {
                .kpi-grid {
                    grid-template-columns: repeat(5, minmax(0, 1fr));
                    gap: 0.9rem;
                }
                .kpi-card-wide {
                    grid-column: span 1 !important;
                }
            }
            .kpi-card-wide {
                grid-column: span 2;
            }
            .kpi-card {
                background: rgba(128, 128, 128, 0.08);
                border: 1px solid rgba(128, 128, 128, 0.18);
                border-radius: 14px;
                padding: 0.8rem 0.9rem;
            }
            .kpi-label {
                font-size: 0.78rem;
                opacity: 0.75;
                margin-bottom: 0.25rem;
            }
            .kpi-value {
                font-size: clamp(1.25rem, 3.5vw, 1.65rem);
                font-weight: 700;
                line-height: 1.15;
            }
            .kpi-badge {
                display: inline-block;
                margin-top: 0.35rem;
                padding: 0.15rem 0.5rem;
                border-radius: 999px;
                font-size: 0.75rem;
                font-weight: 600;
            }
            .badge-up {
                background: rgba(14, 165, 233, 0.16);
                color: #0284c7;
            }
            .badge-down {
                background: rgba(249, 115, 22, 0.16);
                color: #ea580c;
            }
            .badge-flat {
                background: rgba(100, 116, 139, 0.16);
                color: #64748b;
            }
            @media (prefers-color-scheme: dark) {
                .badge-up { color: #38bdf8; }
                .badge-down { color: #fb923c; }
                .badge-flat { color: #94a3b8; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "tiszadorogma_adatok.csv")
    pressure_csv_path = os.path.join(script_dir, "legnyomas_adatok.csv")

    try:
        df, water_series = load_data(csv_path)
    except FileNotFoundError:
        st.error("A tiszadorogma_adatok.csv fájl nem található. Futtasd előbb a `git pull`-t vagy a `scraper.py`-t!")
        st.stop()

    pressure_series = load_pressure_data(pressure_csv_path)

    if df.empty:
        st.warning("A CSV fájl üres vagy nem tartalmaz érvényes dátumokat.")
        st.stop()

    latest_date = df.index.max()
    latest_row = df.loc[latest_date]
    if isinstance(latest_row, pd.DataFrame):
        latest_row = latest_row.iloc[-1]

    latest_water = water_series.iloc[-1] if not water_series.empty else latest_row.get("Vízállás ma reggel")
    latest_delta = latest_row.get("Változás 24 óra alatt")
    latest_flow = latest_row.get("Reggeli hozam")
    latest_temp = latest_row.get("Reggeli víz hőmérséklet")
    latest_ice = latest_row.get("Reggeli jégállapot")

    valid_flows = df["Reggeli hozam"].dropna()
    flow_delta = (valid_flows.iloc[-1] - valid_flows.iloc[-2]) if len(valid_flows) >= 2 else None

    st.markdown(
        f"""
        <div class="hero-header">
            <div class="hero-title">🌊 Tisza – Tiszadorogma</div>
            <div class="hero-subtitle">Utolsó adat: <b>{latest_date.strftime('%Y.%m.%d.')}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    preset = st.segmented_control(
        "Időszak",
        options=["7 nap", "14 nap", "30 nap", "90 nap", "Összes", "Egyéni"],
        default="14 nap",
        label_visibility="collapsed",
    )

    min_date = df.index.min().date()
    max_date = df.index.max().date()

    preset_days = {"7 nap": 7, "14 nap": 14, "30 nap": 30, "90 nap": 90}
    if preset in preset_days:
        start_date = max(min_date, (latest_date - pd.Timedelta(days=preset_days[preset])).date())
        end_date = max_date
    elif preset == "Összes":
        start_date, end_date = min_date, max_date
    else:
        default_start = max(min_date, (latest_date - pd.Timedelta(days=14)).date())
        date_range = st.date_input(
            "Válassz dátumtartományt",
            value=(default_start, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_date, max_date

    water_filtered = water_series[(water_series.index.date >= start_date) & (water_series.index.date <= end_date)]
    df_filtered = df[(df.index.date >= start_date) & (df.index.date <= end_date)]
    pressure_filtered = (
        pressure_series[(pressure_series.index.date >= start_date) & (pressure_series.index.date <= end_date)]
        if not pressure_series.empty
        else pressure_series
    )

    water_delta_text, water_delta_cls = format_delta_badge(latest_delta, "cm")
    if flow_delta is not None and not pd.isna(flow_delta):
        flow_sign = "+" if flow_delta > 0 else ""
        flow_badge_cls = "badge-up" if flow_delta > 0 else ("badge-down" if flow_delta < 0 else "badge-flat")
        flow_badge_text = f"{flow_sign}{flow_delta:g} m³/s"
    else:
        flow_badge_cls, flow_badge_text = "badge-flat", "Napi mérés"

    # Aznapi aktuális légnyomás és 3 órás trend számítása
    if not pressure_series.empty:
        p_latest_ts = pressure_series.index.max()
        p_latest_val = pressure_series.iloc[-1]
        pressure_val_str = f"{p_latest_val:.1f} hPa"
        pressure_label = f"Légnyomás ({p_latest_ts.strftime('%m.%d. %H:%M')})"

        ref_target = p_latest_ts - pd.Timedelta(hours=3)
        earlier_vals = pressure_series[pressure_series.index <= ref_target]
        if not earlier_vals.empty:
            p_delta = p_latest_val - earlier_vals.iloc[-1]
            if p_delta >= 0.5:
                p_badge_cls = "badge-up"
                p_badge_text = f"▲ Növekvő (+{p_delta:.1f} hPa / 3ó)"
            elif p_delta <= -0.5:
                p_badge_cls = "badge-down"
                p_badge_text = f"▼ Csökkenő ({p_delta:.1f} hPa / 3ó)"
            else:
                p_badge_cls = "badge-flat"
                p_badge_text = f"● Stabil ({p_delta:+.1f} hPa / 3ó)"
        else:
            p_badge_cls, p_badge_text = "badge-flat", "Nincs előző adat"
    else:
        pressure_val_str = "–"
        pressure_label = "Aktuális légnyomás"
        p_badge_cls, p_badge_text = "badge-flat", "Nincs légnyomás adat"

    w_min = f"{water_filtered.min():.0f}" if not water_filtered.empty else "–"
    w_max = f"{water_filtered.max():.0f}" if not water_filtered.empty else "–"
    w_avg = f"{water_filtered.mean():.0f} cm átlag" if not water_filtered.empty else "Nincs adat"

    water_val_str = f"{latest_water:.0f} cm" if pd.notna(latest_water) else "–"
    flow_val_str = f"{latest_flow:g} m³/s" if pd.notna(latest_flow) else "–"
    ice_str = str(latest_ice).capitalize() if pd.notna(latest_ice) else "Nincs adat"
    temp_str = f"{latest_temp:g} °C" if pd.notna(latest_temp) else "Vízhő: –"

    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Aktuális vízállás</div>
                <div class="kpi-value">{water_val_str}</div>
                <span class="kpi-badge {water_delta_cls}">{water_delta_text}</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Reggeli hozam</div>
                <div class="kpi-value">{flow_val_str}</div>
                <span class="kpi-badge {flow_badge_cls}">{flow_badge_text}</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Időszak Min / Max</div>
                <div class="kpi-value">{w_min} / {w_max} cm</div>
                <span class="kpi-badge badge-flat">{w_avg}</span>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Jégállapot & Hőfok</div>
                <div class="kpi-value">{ice_str}</div>
                <span class="kpi-badge badge-flat">{temp_str}</span>
            </div>
            <div class="kpi-card kpi-card-wide">
                <div class="kpi-label">{pressure_label}</div>
                <div class="kpi-value">{pressure_val_str}</div>
                <span class="kpi-badge {p_badge_cls}">{p_badge_text}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_water, tab_flow, tab_temp, tab_pressure, tab_combined, tab_table = st.tabs(
        ["📈 Vízállás", "💧 Hozam", "🌡️ Vízhő", "🌬️ Légnyomás", "🔀 Összevetés", "📋 Táblázat"]
    )

    with tab_water:
        if water_filtered.empty:
            st.info("A választott időszakra nincs vízállás adat.")
        else:
            fig_water = go.Figure()
            fig_water.add_trace(
                go.Scatter(
                    x=water_filtered.index,
                    y=water_filtered.values,
                    mode="lines+markers",
                    name="Vízállás",
                    line=dict(color="#0ea5e9", width=3, shape="spline"),
                    marker=dict(size=5, color="#0284c7"),
                    fill="tozeroy",
                    fillcolor="rgba(14, 165, 233, 0.18)",
                    hovertemplate="%{x|%Y.%m.%d. %H:%M}<br><b>%{y:.0f} cm</b><extra></extra>",
                )
            )
            idx_max = water_filtered.idxmax()
            idx_min = water_filtered.idxmin()
            fig_water.add_trace(
                go.Scatter(
                    x=[idx_max, idx_min],
                    y=[water_filtered.loc[idx_max], water_filtered.loc[idx_min]],
                    mode="markers+text",
                    text=[f"Max: {water_filtered.loc[idx_max]:.0f}", f"Min: {water_filtered.loc[idx_min]:.0f}"],
                    textposition=["top center", "bottom center"],
                    marker=dict(size=9, color=["#ef4444", "#10b981"], line=dict(width=1.5, color="white")),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            mobile_plotly_layout(fig_water, "Vízállás (cm)", height=340)
            st.plotly_chart(fig_water, use_container_width=True, config=PLOTLY_CONFIG)

        delta_series = df_filtered["Változás 24 óra alatt"].dropna()
        if not delta_series.empty:
            colors = ["#0ea5e9" if v > 0 else ("#f97316" if v < 0 else "#94a3b8") for v in delta_series.values]
            fig_delta = go.Figure(
                go.Bar(
                    x=delta_series.index,
                    y=delta_series.values,
                    marker_color=colors,
                    name="24ó változás",
                    hovertemplate="%{x|%Y.%m.%d.}<br><b>%{y:+.0f} cm</b><extra></extra>",
                )
            )
            mobile_plotly_layout(fig_delta, "24ó változás (cm)", height=220)
            fig_delta.update_layout(title=dict(text="Napi vízszintváltozás (cm)", font=dict(size=14), x=0))
            st.plotly_chart(fig_delta, use_container_width=True, config=PLOTLY_CONFIG)

    with tab_flow:
        flow_series = df_filtered["Reggeli hozam"].dropna()
        if flow_series.empty:
            st.info("A választott időszakra nincs hozam adat.")
        else:
            fig_flow = go.Figure()
            fig_flow.add_trace(
                go.Scatter(
                    x=flow_series.index,
                    y=flow_series.values,
                    mode="lines+markers",
                    name="Reggeli hozam",
                    line=dict(color="#06b6d4", width=3, shape="spline"),
                    marker=dict(size=6, color="#0891b2"),
                    fill="tozeroy",
                    fillcolor="rgba(6, 182, 212, 0.18)",
                    hovertemplate="%{x|%Y.%m.%d.}<br><b>%{y:g} m³/s</b><extra></extra>",
                )
            )
            mobile_plotly_layout(fig_flow, "Hozam (m³/s)", height=340)
            st.plotly_chart(fig_flow, use_container_width=True, config=PLOTLY_CONFIG)

    with tab_temp:
        temp_series = df_filtered["Reggeli víz hőmérséklet"].dropna()
        if temp_series.empty:
            st.info("A választott időszakra még nincs vízhőmérséklet adat.")
        else:
            fig_temp = go.Figure()
            fig_temp.add_trace(
                go.Scatter(
                    x=temp_series.index,
                    y=temp_series.values,
                    mode="lines+markers",
                    name="Vízhőmérséklet",
                    line=dict(color="#f59e0b", width=3, shape="spline"),
                    marker=dict(size=7, color="#d97706"),
                    fill="tozeroy",
                    fillcolor="rgba(245, 158, 11, 0.18)",
                    hovertemplate="%{x|%Y.%m.%d.}<br><b>%{y:.1f} °C</b><extra></extra>",
                )
            )
            mobile_plotly_layout(fig_temp, "Vízhőmérséklet (°C)", height=340)
            st.plotly_chart(fig_temp, use_container_width=True, config=PLOTLY_CONFIG)

    with tab_pressure:
        if pressure_filtered.empty:
            st.info("A választott időszakra még nincs légnyomás adat. Futtasd a `pressure_scraper.py` szkriptet!")
        else:
            fig_pressure = go.Figure()
            fig_pressure.add_trace(
                go.Scatter(
                    x=pressure_filtered.index,
                    y=pressure_filtered.values,
                    mode="lines",
                    name="Légnyomás",
                    line=dict(color="#8b5cf6", width=2.5, shape="spline"),
                    fill="tozeroy",
                    fillcolor="rgba(139, 92, 246, 0.14)",
                    hovertemplate="%{x|%Y.%m.%d. %H:%M}<br><b>%{y:.1f} hPa</b><extra></extra>",
                )
            )
            p_max_idx = pressure_filtered.idxmax()
            p_min_idx = pressure_filtered.idxmin()
            fig_pressure.add_trace(
                go.Scatter(
                    x=[p_max_idx, p_min_idx],
                    y=[pressure_filtered.loc[p_max_idx], pressure_filtered.loc[p_min_idx]],
                    mode="markers+text",
                    text=[
                        f"Max: {pressure_filtered.loc[p_max_idx]:.1f}",
                        f"Min: {pressure_filtered.loc[p_min_idx]:.1f}",
                    ],
                    textposition=["top center", "bottom center"],
                    marker=dict(size=8, color=["#ef4444", "#10b981"], line=dict(width=1.5, color="white")),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            fig_pressure.add_hline(
                y=1013.25,
                line_dash="dash",
                line_color="rgba(148, 163, 184, 0.7)",
                annotation_text="1013.25 hPa (normál)",
                annotation_position="bottom right",
            )
            p_pad = 3
            mobile_plotly_layout(fig_pressure, "Légnyomás (hPa)", height=350)
            fig_pressure.update_yaxes(
                range=[pressure_filtered.min() - p_pad, pressure_filtered.max() + p_pad]
            )
            st.plotly_chart(fig_pressure, use_container_width=True, config=PLOTLY_CONFIG)

    with tab_combined:
        combo_choice = st.segmented_control(
            "Összevetés típusa",
            options=["Vízállás + Légnyomás", "Vízállás + Hozam"],
            default="Vízállás + Légnyomás",
            label_visibility="collapsed",
        )
        if combo_choice == "Vízállás + Légnyomás":
            if water_filtered.empty or pressure_filtered.empty:
                st.info("Az összevetéshez vízállás és légnyomás adat is szükséges.")
            else:
                fig_combo = make_subplots(specs=[[{"secondary_y": True}]])
                fig_combo.add_trace(
                    go.Scatter(
                        x=water_filtered.index,
                        y=water_filtered.values,
                        name="Vízállás (cm)",
                        line=dict(color="#0ea5e9", width=2.5, shape="spline"),
                    ),
                    secondary_y=False,
                )
                fig_combo.add_trace(
                    go.Scatter(
                        x=pressure_filtered.index,
                        y=pressure_filtered.values,
                        name="Légnyomás (hPa)",
                        line=dict(color="#8b5cf6", width=2, dash="dot", shape="spline"),
                    ),
                    secondary_y=True,
                )
                mobile_plotly_layout(fig_combo, "Vízállás (cm)", height=350)
                fig_combo.update_yaxes(title_text="Légnyomás (hPa)", secondary_y=True, fixedrange=True, showgrid=False)
                st.plotly_chart(fig_combo, use_container_width=True, config=PLOTLY_CONFIG)
        else:
            flow_series = df_filtered["Reggeli hozam"].dropna()
            if water_filtered.empty or flow_series.empty:
                st.info("Az összevetéshez mindkét adatsor szükséges.")
            else:
                fig_combo = make_subplots(specs=[[{"secondary_y": True}]])
                fig_combo.add_trace(
                    go.Scatter(
                        x=water_filtered.index,
                        y=water_filtered.values,
                        name="Vízállás (cm)",
                        line=dict(color="#0ea5e9", width=2.5, shape="spline"),
                    ),
                    secondary_y=False,
                )
                fig_combo.add_trace(
                    go.Scatter(
                        x=flow_series.index,
                        y=flow_series.values,
                        name="Hozam (m³/s)",
                        line=dict(color="#14b8a6", width=2.5, dash="dot", shape="spline"),
                    ),
                    secondary_y=True,
                )
                mobile_plotly_layout(fig_combo, "Vízállás (cm)", height=350)
                fig_combo.update_yaxes(title_text="Hozam (m³/s)", secondary_y=True, fixedrange=True, showgrid=False)
                st.plotly_chart(fig_combo, use_container_width=True, config=PLOTLY_CONFIG)

    with tab_table:
        cols = [
            "Vízállás ma reggel",
            "Változás 24 óra alatt",
            "Vízállás tegnap este",
            "Reggeli hozam",
            "Reggeli víz hőmérséklet",
            "Reggeli jégállapot",
        ]
        available_cols = [c for c in cols if c in df_filtered.columns]
        table_df = df_filtered[available_cols].sort_index(ascending=False).copy()
        table_df.index = table_df.index.strftime("%Y.%m.%d.")
        st.dataframe(table_df, use_container_width=True, height=380)


if __name__ == "__main__":
    st.set_page_config(
        page_title="Tiszadorogma Vízállás v2",
        page_icon="🌊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    render()
