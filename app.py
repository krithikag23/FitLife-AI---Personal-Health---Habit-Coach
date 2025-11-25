import streamlit as st
import sqlite3
import pandas as pd
import datetime as dt
import plotly.express as px
from pathlib import Path

DB_PATH = "fitlife.db"

# ----------------- DB HELPERS -----------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            steps INTEGER DEFAULT 0,
            water_glasses INTEGER DEFAULT 0,
            sleep_hours REAL DEFAULT 0,
            mood TEXT DEFAULT '',
            energy INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            habit_1_done INTEGER DEFAULT 0,
            habit_2_done INTEGER DEFAULT 0,
            habit_3_done INTEGER DEFAULT 0
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position INTEGER NOT NULL
        );
        """
    )
    # Insert default habits if empty
    cur.execute("SELECT COUNT(*) FROM habits;")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO habits (name, position) VALUES (?, ?);",
            [
                ("Exercise 20 minutes", 1),
                ("No sugary drinks", 2),
                ("Meditate 5 minutes", 3),
            ],
        )
    conn.commit()
    conn.close()

def get_habits():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, name, position FROM habits ORDER BY position;")
    rows = cur.fetchall()
    conn.close()
    return rows

def upsert_daily_log(date_str, data):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id FROM daily_log WHERE date = ?;", (date_str,))
    row = cur.fetchone()

    if row is None:
        cur.execute(
            """
            INSERT INTO daily_log 
            (date, steps, water_glasses, sleep_hours, mood, energy, notes,
             habit_1_done, habit_2_done, habit_3_done)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                date_str,
                data["steps"],
                data["water_glasses"],
                data["sleep_hours"],
                data["mood"],
                data["energy"],
                data["notes"],
                data["habit_1_done"],
                data["habit_2_done"],
                data["habit_3_done"],
            ),
        )
    else:
        cur.execute(
            """
            UPDATE daily_log SET
            steps = ?, water_glasses = ?, sleep_hours = ?, mood = ?, energy = ?, 
            notes = ?, habit_1_done = ?, habit_2_done = ?, habit_3_done = ?
            WHERE date = ?;
            """,
            (
                data["steps"],
                data["water_glasses"],
                data["sleep_hours"],
                data["mood"],
                data["energy"],
                data["notes"],
                data["habit_1_done"],
                data["habit_2_done"],
                data["habit_3_done"],
                date_str,
            ),
        )

    conn.commit()
    conn.close()

    def load_logs(days=30):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT date, steps, water_glasses, sleep_hours, mood, energy,
               habit_1_done, habit_2_done, habit_3_done
        FROM daily_log
        ORDER BY date DESC
        LIMIT ?;
        """,
        (days,),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(
        rows,
        columns=[
            "date",
            "steps",
            "water_glasses",
            "sleep_hours",
            "mood",
            "energy",
            "habit_1_done",
            "habit_2_done",
            "habit_3_done",
        ],
    )
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")

# ----------------- SCORE LOGIC -----------------
def compute_health_score(row):
    score = 0
    # Steps (0–40 pts)
    steps = row.get("steps", 0)
    if steps >= 8000:
        score += 40
    elif steps >= 5000:
        score += 30
    elif steps >= 3000:
        score += 20
    elif steps > 0:
        score += 10

    # Sleep (0–25 pts)
    sleep = row.get("sleep_hours", 0)
    if 7 <= sleep <= 9:
        score += 25
    elif 6 <= sleep < 7 or 9 < sleep <= 10:
        score += 18
    elif 5 <= sleep < 6:
        score += 10

    # Water (0–20 pts)
    water = row.get("water_glasses", 0)
    if water >= 8:
        score += 20
    elif water >= 6:
        score += 15
    elif water >= 4:
        score += 10
    elif water > 0:
        score += 5

    # Habits (0–15 pts)
    habits_count = row.get("habit_1_done", 0) + row.get("habit_2_done", 0) + row.get(
        "habit_3_done", 0
    )
    score += habits_count * 5  # 3 habits max → 15 pts

    return min(score, 100)

# ----------------- UI -----------------
def main():
    Path(DB_PATH).touch(exist_ok=True)
    init_db()

    st.set_page_config(
        page_title="FitLife AI – Habit Coach",
        page_icon="💪",
        layout="wide",
    )

    st.title("💪 FitLife AI – Personal Health & Habit Coach")
    st.caption("Track your daily habits, health metrics, and see your wellness score over time.")

    tabs = st.tabs(["📆 Today", "📊 Insights", "📜 History"])

    # --------- TODAY TAB ---------
    with tabs[0]:
        st.subheader("📆 Log Today")

        today = dt.date.today()
        date = st.date_input("Date", today)
        date_str = date.isoformat()

        habits = get_habits()
        habit_labels = [h[1] for h in habits]

        col1, col2, col3 = st.columns(3)
        with col1:
            steps = st.number_input("Steps walked", min_value=0, max_value=100000, value=4000)
            water = st.number_input("Water (glasses)", min_value=0, max_value=30, value=6)
        with col2:
            sleep = st.number_input("Sleep (hours)", min_value=0.0, max_value=24.0, value=7.0, step=0.5)
            energy = st.slider("Energy level", 0, 10, 6)
        with col3:
            mood = st.selectbox("Mood", ["😊 Good", "😐 Okay", "😴 Tired", "😟 Stressed", "😢 Low"])
            notes = st.text_area("Notes (optional)", height=80)

        st.markdown("### ✅ Habits")
        colh1, colh2, colh3 = st.columns(3)
        habit_1_done = colh1.checkbox(habit_labels[0], value=False)
        habit_2_done = colh2.checkbox(habit_labels[1], value=False)
        habit_3_done = colh3.checkbox(habit_labels[2], value=False)

        if st.button("💾 Save Today"):
            data = {
                "steps": int(steps),
                "water_glasses": int(water),
                "sleep_hours": float(sleep),
                "mood": mood,
                "energy": int(energy),
                "notes": notes,
                "habit_1_done": int(habit_1_done),
                "habit_2_done": int(habit_2_done),
                "habit_3_done": int(habit_3_done),
            }
            upsert_daily_log(date_str, data)
            st.success(f"Saved log for {date_str} ✅")

    # --------- INSIGHTS TAB ---------
    with tabs[1]:
        st.subheader("📊 Wellness Insights")

        df = load_logs(days=30)
        if df.empty:
            st.info("No data yet. Log at least one day in the 'Today' tab.")
        else:
            df["health_score"] = df.apply(compute_health_score, axis=1)

            colA, colB = st.columns(2)
            with colA:
                latest = df.iloc[-1]
                st.metric("Today’s Health Score", f"{int(latest['health_score'])}/100")
                st.metric("Steps (last day)", int(latest["steps"]))
                st.metric("Water (glasses, last day)", int(latest["water_glasses"]))

            with colB:
                fig = px.line(
                    df,
                    x="date",
                    y="health_score",
                    title="Health Score Over Time",
                    markers=True,
                )
                fig.update_layout(yaxis_range=[0, 100])
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("### 🧩 Metrics Overview (Last 30 Days)")
            fig2 = px.bar(
                df,
                x="date",
                y=["steps", "water_glasses", "sleep_hours"],
                barmode="group",
                title="Steps, Water & Sleep Trends",
            )
            st.plotly_chart(fig2, use_container_width=True)

    # --------- HISTORY TAB ---------
    with tabs[2]:
        st.subheader("📜 History (Last 30 days)")
        df = load_logs(days=30)
        if df.empty:
            st.info("No logs saved yet.")
        else:
            df["health_score"] = df.apply(compute_health_score, axis=1)
            show_df = df[
                [
                    "date",
                    "health_score",
                    "steps",
                    "water_glasses",
                    "sleep_hours",
                    "mood",
                    "energy",
                ]
            ].sort_values("date", ascending=False)
            st.dataframe(show_df, hide_index=True, use_container_width=True)

            csv = show_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇ Download CSV",
                data=csv,
                file_name="fitlife_history.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()