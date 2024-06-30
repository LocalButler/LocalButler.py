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

def place_order():
    st.subheader("🛍️ Place a New Order")

    session = Session()
    merchants = session.query(Merchant).all()
    merchant = st.selectbox("Select Merchant", [m.name for m in merchants])
    service = st.text_input("Service")
    
    date = st.date_input("Select Date", min_value=datetime.now().date())
    time = st.selectbox("Select Time", 
                        [f"{h:02d}:{m:02d} {'AM' if h<12 else 'PM'} EST" 
                         for h in range(7, 22) for m in [0, 15, 30, 45]])
    
    address = st.text_input("Delivery Address", value=st.session_state.user.address)
    
    if st.button("🚀 Confirm Order"):
        order_id = generate_order_id()
        new_order = Order(
            id=order_id,
            user_id=st.session_state.user.id,
            merchant_id=next(m.id for m in merchants if m.name == merchant),
            service=service,
            date=date,
            time=time,
            address=address,
            status='Pending'
        )
        session.add(new_order)
        session.commit()
        
        # Animated order confirmation
        progress_bar = st.progress(0)
        status_text = st.empty()
        for i in range(100):
            progress_bar.progress(i + 1)
            status_text.text(f"Processing order... {i+1}%")
            time.sleep(0.01)
        status_text.text("Order placed successfully! 🎉")
        st.success(f"Your order ID is {order_id}")
        st.balloons()

def register_user():
    st.subheader("📝 Register")
    user_type = st.selectbox("Register as", ["👤 Customer", "🚗 Driver", "🏪 Merchant", "🛠️ Service Provider"])
    name = st.text_input("Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    address = st.text_input("Address")
    
    if user_type == "🚗 Driver":
        vehicle_type = st.text_input("Vehicle Type")
    elif user_type == "🏪 Merchant":
        business_name = st.text_input("Business Name")
        business_type = st.text_input("Business Type")
    
    if st.button("🚀 Register"):
        hashed_password = ph.hash(password)
        new_user = User(
            name=name,
            email=email,
            password=hashed_password,
            type=user_type.split()[1].lower(),
            address=address
        )
        session = Session()
        session.add(new_user)
        session.commit()
        st.success("Registered successfully! 🎉")
        st.balloons()

def login_page():
    st.subheader("🔑 Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("🚀 Login"):
        user = login_user(email, password)
        if user:
            st.session_state.user = user
            st.success("Logged in successfully! 🎉")
            st.balloons()
            st.experimental_rerun()
        else:
            st.error("Invalid email or password ❌")

def display_user_orders():
    st.subheader("📦 My Orders")
    session = Session()
    user_orders = session.query(Order).filter_by(user_id=st.session_state.user.id).all()
    
    for order in user_orders:
        with st.expander(f"🛍️ Order ID: {order.id} - Status: {order.status}"):
            st.write(f"🛒 Service: {order.service}")
            st.write(f"📅 Date: {order.date}")
            st.write(f"🕒 Time: {order.time}")
            st.write(f"📍 Address: {order.address}")
            
            # Live order status update
            status_placeholder = st.empty()
            progress_bar = st.progress(0)
            
            statuses = ['Pending', 'Preparing', 'On the way', 'Delivered']
            status_emojis = ['⏳', '👨‍🍳', '🚚', '✅']
            current_status_index = statuses.index(order.status)
            
            for i in range(current_status_index, len(statuses)):
                status_placeholder.text(f"Current Status: {status_emojis[i]} {statuses[i]}")
                progress_bar.progress((i + 1) * 25)
                if i < len(statuses) - 1:
                    time.sleep(2)  # Simulate status change every 2 seconds
            
            merchant = session.query(Merchant).filter_by(id=order.merchant_id).first()
            user_location = (st.session_state.user.latitude, st.session_state.user.longitude)
            route = [[merchant.latitude, merchant.longitude], user_location]
            map = create_map([merchant], user_location, route)
            folium_static(map)

def display_map():
    st.subheader("🗺️ Merchant Map")
    session = Session()
    merchants = session.query(Merchant).all()
    user_location = (st.session_state.user.latitude, st.session_state.user.longitude)
    
    map_container = st.empty()
    
    while True:
        map = create_map(merchants, user_location)
        with map_container:
            folium_static(map)
        
        # Simulate movement (in a real app, this would be actual location updates)
        user_location = (user_location[0] + random.uniform(-0.001, 0.001),
                         user_location[1] + random.uniform(-0.001, 0.001))
        
        time.sleep(5)  # Update every 5 seconds

def driver_dashboard():
    st.subheader("🚗 Driver Dashboard")
    session = Session()
    
    # Create an empty container for orders
    orders_container = st.empty()
    
    while True:
        available_orders = session.query(Order).filter_by(status='Pending').all()
        
        with orders_container.container():
            if not available_orders:
                st.info("No pending orders at the moment. Waiting for new orders... ⏳")
            else:
                for order in available_orders:
                    with st.expander(f"📦 Order ID: {order.id}"):
                        merchant = session.query(Merchant).filter_by(id=order.merchant_id).first()
                        st.write(f"🏪 Pickup: {merchant.name}")
                        st.write(f"📍 Delivery Address: {order.address}")
                        if st.button(f"✅ Accept Order {order.id}"):
                            order.status = 'In Progress'
                            session.commit()
                            st.success(f"You have accepted order {order.id} 🎉")
                            time.sleep(2)  # Give time for the success message to be seen
                            st.experimental_rerun()  # Rerun the app to update the order list
        
        time.sleep(10)  # Check for new orders every 10 seconds
        session.commit()  # Refresh the session to get the latest data

if __name__ == "__main__":
    main()
