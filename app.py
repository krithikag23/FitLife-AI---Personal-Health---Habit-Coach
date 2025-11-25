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
