import warnings

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st
from mplsoccer import Pitch
from statsbombpy import sb

warnings.filterwarnings("ignore")

st.set_page_config(page_title="Análisis de pases - StatsBomb", layout="wide")

# ---------------------------------------------------------------------------
# Funciones con cache: en Colab cada celda se ejecuta una sola vez, pero un
# script de Streamlit se re-ejecuta completo en cada interacción del usuario.
# st.cache_data evita volver a llamar a la API de StatsBomb cada vez que
# movemos el slider.
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Cargando competiciones...")
def load_competitions():
    return sb.competitions()


@st.cache_data(show_spinner="Cargando partidos...")
def load_matches(competition_id, season_id):
    return sb.matches(competition_id=competition_id, season_id=season_id)


@st.cache_data(show_spinner="Cargando eventos del partido...")
def load_events(match_id):
    return sb.events(match_id=match_id)


@st.cache_data(show_spinner="Procesando pases...")
def build_passes_df(events: pd.DataFrame) -> pd.DataFrame:
    variables = [
        "minute",
        "second",
        "period",
        "location",
        "pass_end_location",
        "player",
        "pass_recipient",
        "team",
        "type",
    ]
    passes = events[variables]

    final = passes[passes["type"] == "Pass"].copy()
    final.reset_index(inplace=True, drop=True)

    final["x0"] = final.location.apply(lambda x: x[0])
    final["y0"] = final.location.apply(lambda x: x[1])
    final["x1"] = final.pass_end_location.apply(lambda x: x[0])
    final["y1"] = final.pass_end_location.apply(lambda x: x[1])
    final.drop(columns=["location", "pass_end_location"], inplace=True)

    return final


def plot_minute(final: pd.DataFrame, minuto: int):
    pitch = Pitch(pitch_color="grass", line_color="white", stripe=True)
    fig, axs = pitch.draw(figsize=(10, 7))

    data_minuto = final[final.minute == minuto]

    if data_minuto.empty:
        st.info(f"No hubo pases registrados en el minuto {minuto}.")
        return fig

    sns.scatterplot(x="x0", y="y0", data=data_minuto, hue="team", ax=axs)
    axs.legend(loc="upper center", ncol=2)
    return fig


# ---------------------------------------------------------------------------
# Sidebar: selección de competición, temporada y partido
# ---------------------------------------------------------------------------

st.sidebar.header("Selección de partido")

competitions = load_competitions()

competition_name = st.sidebar.selectbox(
    "Competición",
    sorted(competitions.competition_name.unique()),
    index=sorted(competitions.competition_name.unique()).index("FIFA World Cup")
    if "FIFA World Cup" in competitions.competition_name.unique()
    else 0,
)

comp_rows = competitions[competitions.competition_name == competition_name]

season_name = st.sidebar.selectbox("Temporada", sorted(comp_rows.season_name.unique()))

comp_row = comp_rows[comp_rows.season_name == season_name].iloc[0]
competition_id = comp_row.competition_id
season_id = comp_row.season_id

matches = load_matches(competition_id, season_id)
matches = matches.copy()
matches["etiqueta"] = matches.home_team + " vs " + matches.away_team

match_label = st.sidebar.selectbox("Partido", matches["etiqueta"].tolist())
match_id = int(matches.loc[matches["etiqueta"] == match_label, "match_id"].iloc[0])

# ---------------------------------------------------------------------------
# Cuerpo principal
# ---------------------------------------------------------------------------

st.title("⚽ Análisis de pases con StatsBomb + mplsoccer")
st.caption(f"Partido: {match_label} (match_id={match_id})")

events = load_events(match_id)

with st.expander("Ver mapa de datos faltantes (equivalente al heatmap de isna)"):
    fig_na, axs_na = plt.subplots(figsize=(10, 4))
    sns.heatmap(events.isna(), ax=axs_na, cbar=False, cmap="Blues")
    st.pyplot(fig_na)

final = build_passes_df(events)

st.subheader("Todos los pases del partido (x0, y0)")
fig_scatter, ax_scatter = plt.subplots()
sns.scatterplot(x="x0", y="y0", data=final, ax=ax_scatter)
st.pyplot(fig_scatter)

st.subheader("Pases por minuto sobre la cancha")

# Equivalente a widgets.interact(plot_minute, minuto=(0, 90, 1))
minuto = st.slider("Minuto", min_value=0, max_value=90, value=0, step=1)

fig_pitch = plot_minute(final, minuto)
st.pyplot(fig_pitch)

with st.expander("Ver tabla de pases filtrados"):
    st.dataframe(final[final.minute == minuto])
