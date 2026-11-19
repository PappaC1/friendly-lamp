import streamlit as st
from scipy.stats import poisson

st.set_page_config(
    page_title="Hollywood Soccer Challenge Predictor",
    page_icon="⚽",
    layout="wide",
)

st.title("⚽ Hollywood Soccer Challenge Predictor")
st.caption(
    "Enter the daily fixtures and team goal statistics. The app estimates the "
    "probability of each winning-margin outcome and suggests the strongest pick."
)

OUTCOMES = [
    "Draw",
    "Home by 1",
    "Home by 2",
    "Home by 3+",
    "Away by 1",
    "Away by 2",
    "Away by 3+",
]


def team_rating_inputs(prefix: str, default_attack: float, default_defence: float):
    col1, col2 = st.columns(2)

    with col1:
        attack = st.number_input(
            f"{prefix} attack rating",
            min_value=0.20,
            max_value=3.00,
            value=default_attack,
            step=0.05,
            help="1.00 = league-average attack. Above 1.00 scores more than average.",
        )

    with col2:
        defence = st.number_input(
            f"{prefix} defence rating",
            min_value=0.20,
            max_value=3.00,
            value=default_defence,
            step=0.05,
            help="1.00 = league-average defence. Above 1.00 concedes more than average.",
        )

    return attack, defence


def calculate_prediction(
    home_attack,
    home_defence,
    away_attack,
    away_defence,
    league_average_goals=2.60,
    home_advantage=1.10,
):
    home_xg = league_average_goals * home_attack * away_defence * home_advantage
    away_xg = league_average_goals * away_attack * home_defence

    home_xg = max(home_xg, 0.15)
    away_xg = max(away_xg, 0.15)

    max_goals = 10
    home_probs = poisson.pmf(range(max_goals + 1), home_xg)
    away_probs = poisson.pmf(range(max_goals + 1), away_xg)

    probabilities = {outcome: 0.0 for outcome in OUTCOMES}
    score_probabilities = {}

    for home_goals, home_probability in enumerate(home_probs):
        for away_goals, away_probability in enumerate(away_probs):
            probability = home_probability * away_probability
            score_probabilities[(home_goals, away_goals)] = probability

            margin = home_goals - away_goals

            if margin == 0:
                probabilities["Draw"] += probability
            elif margin == 1:
                probabilities["Home by 1"] += probability
            elif margin == 2:
                probabilities["Home by 2"] += probability
            elif margin >= 3:
                probabilities["Home by 3+"] += probability
            elif margin == -1:
                probabilities["Away by 1"] += probability
            elif margin == -2:
                probabilities["Away by 2"] += probability
            else:
                probabilities["Away by 3+"] += probability

    most_likely_score = max(score_probabilities, key=score_probabilities.get)

    return {
        "home_xg": home_xg,
        "away_xg": away_xg,
        "probabilities": probabilities,
        "most_likely_score": most_likely_score,
        "most_likely_score_probability": score_probabilities[most_likely_score],
    }


def outcome_from_score(home_goals: int, away_goals: int) -> str:
    margin = home_goals - away_goals

    if margin == 0:
        return "Draw"
    if margin == 1:
        return "Home by 1"
    if margin == 2:
        return "Home by 2"
    if margin >= 3:
        return "Home by 3+"
    if margin == -1:
        return "Away by 1"
    if margin == -2:
        return "Away by 2"

    return "Away by 3+"


st.header("1. Match details")

col1, col2, col3 = st.columns([2, 1, 2])

with col1:
    home_team = st.text_input("Home team", value="Home Team")

with col2:
    st.write("")

with col3:
    away_team = st.text_input("Away team", value="Away Team")

st.subheader("Team ratings")

col1, col2 = st.columns(2)

with col1:
    st.write(f"**{home_team or 'Home team'}**")
    home_attack, home_defence = team_rating_inputs("Home", 1.00, 1.00)

with col2:
    st.write(f"**{away_team or 'Away team'}**")
    away_attack, away_defence = team_rating_inputs("Away", 1.00, 1.00)

st.subheader("Optional: Hollywood odds")

st.caption(
    "Enter the decimal odds shown for each margin in the Hollywood Soccer "
    "Challenge. Leave a field blank if that option is unavailable."
)

odds_columns = st.columns(7)

odds = {}

for column, outcome in zip(odds_columns, OUTCOMES):
    with column:
        value = st.text_input(outcome, value="")
        odds[outcome] = value

prediction = calculate_prediction(
    home_attack=home_attack,
    home_defence=home_defence,
    away_attack=away_attack,
    away_defence=away_defence,
)

st.header("2. Prediction")

st.metric(
    label="Expected goals",
    value=(
        f"{home_team or 'Home'} {prediction['home_xg']:.2f} — "
        f"{prediction['away_xg']:.2f} {away_team or 'Away'}"
    ),
)

most_likely_home, most_likely_away = prediction["most_likely_score"]

st.info(
    f"Most likely exact score: **{most_likely_home}–{most_likely_away}** "
    f"({prediction['most_likely_score_probability'] * 100:.1f}% model probability). "
    "For the Soccer Challenge, use the margin probabilities below rather than "
    "the exact score."
)

st.subheader("Margin probabilities")

ranked = sorted(
    prediction["probabilities"].items(),
    key=lambda item: item[1],
    reverse=True,
)

for outcome, probability in ranked:
    st.progress(
        min(probability, 1.0),
        text=f"{outcome}: {probability * 100:.1f}%",
    )

best_probability_outcome = ranked[0][0]

st.success(
    f"Highest model probability: **{best_probability_outcome}** "
    f"({prediction['probabilities'][best_probability_outcome] * 100:.1f}%)"
)

st.header("3. Best value selection")

valid_odds = {}

for outcome, value in odds.items():
    if value.strip():
        try:
            decimal_odds = float(value)
            if decimal_odds > 1.0:
                valid_odds[outcome] = decimal_odds
        except ValueError:
            pass

if valid_odds:
    expected_points = {
        outcome: prediction["probabilities"][outcome] * odd
        for outcome, odd in valid_odds.items()
    }

    best_value_outcome = max(expected_points, key=expected_points.get)

    st.success(
        f"Best expected-points selection: **{best_value_outcome}** "
        f"at odds {valid_odds[best_value_outcome]:.2f}. "
        f"Expected points: {expected_points[best_value_outcome]:.2f}."
    )

    st.dataframe(
        {
            "Selection": list(expected_points.keys()),
            "Model probability": [
                f"{prediction['probabilities'][outcome] * 100:.1f}%"
                for outcome in expected_points
            ],
            "Odds": [f"{valid_odds[outcome]:.2f}" for outcome in expected_points],
            "Expected points": [
                f"{expected_points[outcome]:.2f}" for outcome in expected_points
            ],
        },
        use_container_width=True,
        hide_index=True,
    )
else:
    st.caption(
        "Enter at least one decimal odd to see which selection offers the best "
        "expected Soccer Challenge points."
    )

st.header("4. Quick rating helper")

st.caption(
    "If you do not have ratings, enter each team’s last 10 matches. "
    "The app converts goals per match into simple attack and defence ratings."
)

with st.expander("Calculate ratings from recent matches"):
    recent_col1, recent_col2 = st.columns(2)

    with recent_col1:
        home_matches = st.number_input(
            f"{home_team or 'Home'} matches played",
            min_value=1,
            max_value=50,
            value=10,
        )
        home_scored = st.number_input(
            f"{home_team or 'Home'} goals scored",
            min_value=0,
            max_value=200,
            value=15,
        )
        home_conceded = st.number_input(
            f"{home_team or 'Home'} goals conceded",
            min_value=0,
            max_value=200,
            value=12,
        )

    with recent_col2:
        away_matches = st.number_input(
            f"{away_team or 'Away'} matches played",
            min_value=1,
            max_value=50,
            value=10,
        )
        away_scored = st.number_input(
            f"{away_team or 'Away'} goals scored",
            min_value=0,
            max_value=200,
            value=12,
        )
        away_conceded = st.number_input(
            f"{away_team or 'Away'} goals conceded",
            min_value=0,
            max_value=200,
            value=15,
        )

    league_goals_per_match = st.number_input(
        "Average goals per match in the league",
        min_value=0.50,
        max_value=6.00,
        value=2.60,
        step=0.05,
    )

    calculated_home_attack = (home_scored / home_matches) / league_goals_per_match
    calculated_home_defence = (home_conceded / home_matches) / league_goals_per_match

    calculated_away_attack = (away_scored / away_matches) / league_goals_per_match
    calculated_away_defence = (away_conceded / away_matches) / league_goals_per_match

    st.write(
        f"**{home_team or 'Home'} ratings:** "
        f"Attack {calculated_home_attack:.2f}, Defence {calculated_home_defence:.2f}"
    )
    st.write(
        f"**{away_team or 'Away'} ratings:** "
        f"Attack {calculated_away_attack:.2f}, Defence {calculated_away_defence:.2f}"
    )
    st.caption("Copy these values into the team-rating fields above.")

st.divider()
st.caption(
    "For entertainment and statistical guidance only. Football is highly "
    "uncertain; do not treat any prediction as a guaranteed result."
)
