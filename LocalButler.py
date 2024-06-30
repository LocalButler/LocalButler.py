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

# Main app
def main():
    st.title("Delivery App")

    # Initialize session state
    if 'user' not in st.session_state:
        st.session_state.user = None

    # Authentication
    if st.session_state.user is None:
        auth_choice = st.sidebar.selectbox("Choose action", ["Login", "Register"])
        if auth_choice == "Login":
            login_page()
        else:
            register_user()
    else:
        # Sidebar menu
        menu = ["Home", "Order Now", "My Orders", "Map"]
        if st.session_state.user.type == 'driver':
            menu.append("Driver Dashboard")
        
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Home":
            home_page()
        elif choice == "Order Now":
            place_order()
        elif choice == "My Orders":
            display_user_orders()
        elif choice == "Map":
            display_map()
        elif choice == "Driver Dashboard":
            if st.session_state.user.type == 'driver':
                driver_dashboard()
            else:
                st.warning("Access denied. This page is for drivers only.")

        if st.sidebar.button("Log Out"):
            st.session_state.user = None
            st.success("Logged out successfully.")

def home_page():
    st.write(f"Welcome to our Delivery App, {st.session_state.user.name}!")
    session = Session()
    merchants = session.query(Merchant).all()
    st.write("Here are the available merchants:")
    for merchant in merchants:
        st.write(f"- {merchant.name} ({merchant.type})")
    map = create_map(merchants)
    folium_static(map)

def place_order():
    st.subheader("Place a New Order")

    session = Session()
    merchants = session.query(Merchant).all()
    merchant = st.selectbox("Select Merchant", [m.name for m in merchants])
    service = st.text_input("Service")
    
    date = st.date_input("Select Date", min_value=datetime.now().date())
    time = st.selectbox("Select Time", 
                        [f"{h:02d}:{m:02d} {'AM' if h<12 else 'PM'} EST" 
                         for h in range(7, 22) for m in [0, 15, 30, 45]])
    
    address = st.text_input("Delivery Address", value=st.session_state.user.address)
    
    if st.button("Confirm Order"):
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
        st.success(f"Order placed successfully! Your order ID is {order_id}")

def register_user():
    st.subheader("Register")
    user_type = st.selectbox("Register as", ["Customer", "Driver", "Merchant", "Service Provider"])
    name = st.text_input("Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    address = st.text_input("Address")
    
    if user_type == "Driver":
        vehicle_type = st.text_input("Vehicle Type")
    elif user_type == "Merchant":
        business_name = st.text_input("Business Name")
        business_type = st.text_input("Business Type")
    
    if st.button("Register"):
        hashed_password = ph.hash(password)
        new_user = User(
            name=name,
            email=email,
            password=hashed_password,
            type=user_type.lower(),
            address=address
        )
        session = Session()
        session.add(new_user)
        session.commit()
        st.success("Registered successfully!")

def login_page():
    st.subheader("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        user = login_user(email, password)
        if user:
            st.session_state.user = user
            st.success("Logged in successfully!")
        else:
            st.error("Invalid email or password")

def display_user_orders():
    st.subheader("My Orders")
    session = Session()
    user_orders = session.query(Order).filter_by(user_id=st.session_state.user.id).all()
    
    for order in user_orders:
        st.write(f"Order ID: {order.id}")
        st.write(f"Status: {order.status}")
        if st.button(f"View Details for Order {order.id}"):
            st.write(f"Service: {order.service}")
            st.write(f"Date: {order.date}")
            st.write(f"Time: {order.time}")
            st.write(f"Address: {order.address}")
            merchant = session.query(Merchant).filter_by(id=order.merchant_id).first()
            user_location = (st.session_state.user.latitude, st.session_state.user.longitude)
            route = [[merchant.latitude, merchant.longitude], user_location]
            map = create_map([merchant], user_location, route)
            folium_static(map)

def display_map():
    st.subheader("Merchant Map")
    session = Session()
    merchants = session.query(Merchant).all()
    user_location = (st.session_state.user.latitude, st.session_state.user.longitude)
    map = create_map(merchants, user_location)
    folium_static(map)

def driver_dashboard():
    st.subheader("Driver Dashboard")
    session = Session()
    available_orders = session.query(Order).filter_by(status='Pending').all()
    
    for order in available_orders:
        st.write(f"Order ID: {order.id}")
        merchant = session.query(Merchant).filter_by(id=order.merchant_id).first()
        st.write(f"Pickup: {merchant.name}")
        st.write(f"Delivery Address: {order.address}")
        if st.button(f"Accept Order {order.id}"):
            order.status = 'In Progress'
            session.commit()
            st.success(f"You have accepted order {order.id}")

if __name__ == "__main__":
    main()
