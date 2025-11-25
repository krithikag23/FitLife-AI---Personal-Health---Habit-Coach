import streamlit as st
import sqlite3
import pandas as pd
import datetime as dt
import plotly.express as px
from pathlib import Path

DB_PATH = "fitlife.db"