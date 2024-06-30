import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from datetime import datetime, timedelta
import random
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import time

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine('sqlite:///delivery_app.db', echo=True)
Session = sessionmaker(bind=engine)

# Argon2 setup
ph = PasswordHasher()

# SQLAlchemy models
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    type = Column(String, nullable=False)
    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)

class Merchant(Base):
    __tablename__ = 'merchants'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    website = Column(String)

class Order(Base):
    __tablename__ = 'orders'
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    merchant_id = Column(Integer, ForeignKey('merchants.id'))
    service = Column(String)
    date = Column(DateTime, nullable=False)
    time = Column(String, nullable=False)
    address = Column(String, nullable=False)
    status = Column(String, nullable=False)
    user = relationship("User")
    merchant = relationship("Merchant")

# Create tables
Base.metadata.create_all(engine)

# Helper functions
def generate_order_id():
    return f"ORD-{random.randint(10000, 99999)}"

def create_map(merchants, user_location=None, route=None):
    m = folium.Map(location=[40.7128, -74.0060], zoom_start=12)
    for merchant in merchants:
        folium.Marker(
            location=[merchant.latitude, merchant.longitude],
            popup=f"<a href='{merchant.website}' target='_blank'>{merchant.name}</a>",
            tooltip=merchant.name,
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
    
    if user_location:
        folium.Marker(
            location=user_location,
            popup="Your Location",
            tooltip="Your Location",
            icon=folium.Icon(color='green', icon='home')
        ).add_to(m)
    
    if route:
        folium.PolyLine(route, color="blue", weight=2.5, opacity=1).add_to(m)
    
    return m

def login_user(email, password):
    session = Session()
    user = session.query(User).filter_by(email=email).first()
    if user:
        try:
            ph.verify(user.password, password)
            return user
        except VerifyMismatchError:
            return None
    return None

# Color palette
PRIMARY_COLOR = "#FF4B4B"
SECONDARY_COLOR = "#0068C9"
BACKGROUND_COLOR = "#F0F2F6"

# Apply the color theme
st.set_page_config(page_title="Delivery App", page_icon="🚚", layout="wide")

# Custom CSS
st.markdown(f"""
    <style>
    .stApp {{
        background-color: {BACKGROUND_COLOR};
    }}
    .stButton>button {{
        color: white;
        background-color: {PRIMARY_COLOR};
        border-radius: 20px;
    }}
    .stProgress > div > div > div > div {{
        background-color: {SECONDARY_COLOR};
    }}
    </style>
    """, unsafe_allow_html=True)

# Main app
def main():
    st.title("🚚 Delivery App")

    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None

    # Authentication
    if st.session_state.user is None:
        auth_choice = st.sidebar.radio("Choose action", ["🔑 Login", "📝 Register"])
        if auth_choice == "🔑 Login":
            login_page()
        else:
            register_user()
    else:
        # Creative menu
        menu_items = {
            "🏠 Home": home_page,
            "🛒 Order Now": place_order,
            "📦 My Orders": display_user_orders,
            "🗺️ Map": display_map
        }
        if st.session_state.user.type == 'driver':
            menu_items["🚗 Driver Dashboard"] = driver_dashboard

        cols = st.columns(len(menu_items))
        for i, (emoji_label, func) in enumerate(menu_items.items()):
            if cols[i].button(emoji_label):
                func()

        if st.sidebar.button("🚪 Log Out"):
            st.session_state.user = None
            st.success("Logged out successfully.")
            st.experimental_rerun()

def home_page():
    st.write(f"Welcome to our Delivery App, {st.session_state.user.name}! 🎉")
    session = Session()
    merchants = session.query(Merchant).all()
    st.write("Here are the available merchants:")
    for merchant in merchants:
        st.write(f"- 🏪 {merchant.name} ({merchant.type})")
    map = create_map(merchants)
    folium_static(map)

# The rest of the functions (place_order, register_user, login_page, display_user_orders, display_map, driver_dashboard) remain the same as in the previous code

if __name__ == "__main__":
    main()
