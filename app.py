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

