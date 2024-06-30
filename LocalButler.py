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
import sqlalchemy
from dataclasses import dataclass
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

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

@dataclass
class Service:
    name: str
    url: str
    instructions: list
    video_url: str = None
    video_title: str = None
    image_url: str = None
    address: str = None
    phone: str = None
    hours: str = None

# Create tables
try:
    Base.metadata.create_all(engine, checkfirst=True)
    print("Database tables created successfully (or already exist).")
except sqlalchemy.exc.OperationalError as e:
    print(f"An error occurred while creating database tables: {e}")

# Add sample data if the database is empty
session = Session()
if session.query(Merchant).count() == 0:
    sample_merchants = [
        Merchant(name="Pizza Place", type="Restaurant", latitude=40.7128, longitude=-74.0060, website="http://example.com"),
        Merchant(name="Burger Joint", type="Restaurant", latitude=40.7282, longitude=-73.9942, website="http://example2.com"),
        Merchant(name="Sushi Bar", type="Restaurant", latitude=40.7589, longitude=-73.9851, website="http://example3.com"),
    ]
    session.add_all(sample_merchants)
    session.commit()

# Geocoding cache
geocoding_cache = {}

# Helper functions
def generate_order_id():
    return f"ORD-{random.randint(10000, 99999)}"

def create_map(businesses_to_show):
    m = folium.Map(location=[39.1054, -76.7285], zoom_start=12)
    
    for name, info in businesses_to_show.items():
        location = geocode_with_retry(info['address'])
        if location:
            folium.Marker(
                [location.latitude, location.longitude],
                popup=f"""
                <b>{name}</b><br>
                Address: {info['address']}<br>
                Phone: {info['phone']}<br>
                """
            ).add_to(m)
        else:
            st.warning(f"Could not locate {name}")
    
    return m

def geocode_with_retry(address, max_retries=3):
    if address in geocoding_cache:
        return geocoding_cache[address]
    
    geolocator = Nominatim(user_agent="local_butler_app")
    for attempt in range(max_retries):
        try:
            time.sleep(1)  # Add a delay to respect rate limits
            location = geolocator.geocode(address)
            if location:
                geocoding_cache[address] = location
                return location
        except (GeocoderTimedOut, GeocoderServiceError):
            if attempt == max_retries - 1:
                st.warning(f"Could not geocode address: {address}")
                return None
            time.sleep(2)  # Wait for 2 seconds before retrying
    return None

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

def display_service(service: Service):
    st.write(f"ORDER NOW: [{service.name}]({service.url})")
    if service.video_url:
        st.video(service.video_url)
    elif service.image_url:
        st.image(service.image_url, caption=f"{service.name} App", use_column_width=True)
    st.write("Instructions for placing your order:")
    for instruction in service.instructions:
        st.write(f"- {instruction}")
    if service.address:
        st.write(f"Address: {service.address}")
    if service.phone:
        st.write(f"Phone: {service.phone}")
    if service.hours:
        st.write(f"Hours: {service.hours}")

# Color palette
PRIMARY_COLOR = "#FF4B4B"
SECONDARY_COLOR = "#0068C9"
BACKGROUND_COLOR = "#F0F2F6"

# Apply the color theme
st.set_page_config(page_title="Local Butler", page_icon="👔", layout="wide")

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
            "🗺️ Map": display_map,
            "🛍️ Services": display_services
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
    
    businesses_to_show = {m.name: {'address': f"{m.latitude}, {m.longitude}", 'phone': '123-456-7890'} for m in merchants}
    map = create_map(businesses_to_show)
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
        if not all([merchant, service, date, time, address]):
            st.error("Please fill in all fields.")
        else:
            try:
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
            except Exception as e:
                st.error(f"An error occurred while placing the order: {str(e)}")
                session.rollback()

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
        if not all([name, email, password, address]):
            st.error("Please fill in all fields.")
        else:
            try:
                session = Session()
                existing_user = session.query(User).filter_by(email=email).first()
                if existing_user:
                    st.error("Email already in use. Please use a different email.")
                else:
                    hashed_password = ph.hash(password)
                    new_user = User(
                        name=name,
                        email=email,
                        password=hashed_password,
                        type=user_type.split()[1].lower(),
                        address=address
                    )
                    session.add(new_user)
                    session.commit()
                    st.success("Registered successfully! 🎉")
                    st.balloons()
            except Exception as e:
                st.error(f"An error occurred during registration: {str(e)}")
                session.rollback()

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
            businesses_to_show = {merchant.name: {'address': f"{merchant.latitude}, {merchant.longitude}", 'phone': '123-456-7890'}}
            map = create_map(businesses_to_show)
            folium_static(map)

def display_map():
    st.subheader("🗺️ Merchant Map")
    session = Session()
    merchants = session.query(Merchant).all()
    
    if not merchants:
        st.warning("No merchants found in the database.")
        return

    businesses_to_show = {m.name: {'address': f"{m.latitude}, {m.longitude}", 'phone': '123-456-7890'} for m in merchants}
    map = create_map(businesses_to_show)
    folium_static(map)

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

# Define GROCERY_STORES and RESTAURANTS dictionaries
GROCERY_STORES = {
    "Weis Markets": {
        "url": "https://www.weismarkets.com/",
        "video_url": "https://raw.githubusercontent.com/LocalButler/streamlit_app.py/1ff75ee91b2717fabadb44ee645612d6e48e8ee3/Weis%20Promo%20Online%20ordering%20%E2%80%90.mp4",
        "video_title": "Watch this video to learn how to order from Weis Markets:",
        "instructions": [
            "Place your order directly with Weis Markets using your own account to accumulate grocery store points and clip your favorite coupons.",
            "Select store pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "address": "2288, Blue Water Boulevard, Jackson Grove, Odenton, Anne Arundel County, Maryland, 21113, United States",
        "phone": "(410) 672-1877"
    },
    "SafeWay": {
        "url": "https://www.safeway.com/",
        "instructions": [
            "Place your order directly with Safeway using your own account to accumulate grocery store points and clip your favorite coupons.",
            "Select store pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "image_url": "https://raw.githubusercontent.com/LocalButler/streamlit_app.py/main/safeway%20app%20ads.png",
        "address": "7643 Arundel Mills Blvd, Hanover, MD 21076",
        "phone": "(410) 904-7222"
    },
    # Add other grocery stores here...
}

RESTAURANTS = {
    "The Hideaway": {
        "url": "https://order.toasttab.com/online/hideawayodenton",
        "instructions": [
            "Place your order directly with The Hideaway using their website or app.",
            "Select pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "image_url": "https://raw.githubusercontent.com/LocalButler/streamlit_app.py/main/TheHideAway.jpg",
        "address": "1439 Odenton Rd, Odenton, MD 21113",
        "phone": "(410) 874-7213"
    },
    "Ruth's Chris Steak House": {
        "url": "https://order.ruthschris.com/",
        "instructions": [
            "Place your order directly with Ruth's Chris Steak House using their website or app.",
            "Select pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "address": "1110 Town Center Blvd, Odenton, MD 21113",
        "phone": "(410) 451-9600"
    },
    # Add other restaurants here...
}

def display_services():
    st.subheader("🛍️ Available Services")
    
    st.write("### 🛒 Grocery Stores")
    for store_name, store_info in GROCERY_STORES.items():
        with st.expander(store_name):
            display_service(Service(
                name=store_name,
                url=store_info['url'],
                instructions=store_info['instructions'],
                video_url=store_info.get('video_url'),
                video_title=store_info.get('video_title'),
                image_url=store_info.get('image_url'),
                address=store_info['address'],
                phone=store_info['phone']
            ))
    
    st.write("### 🍽️ Restaurants")
    for restaurant_name, restaurant_info in RESTAURANTS.items():
        with st.expander(restaurant_name):
            display_service(Service(
                name=restaurant_name,
                url=restaurant_info['url'],
                instructions=restaurant_info['instructions'],
                image_url=restaurant_info.get('image_url'),
                address=restaurant_info['address'],
                phone=restaurant_info['phone']
            ))

# Add a search functionality
def search_services():
    st.subheader("🔍 Search Services")
    search_term = st.text_input("Enter a service name or keyword:")
    if search_term:
        results = []
        for store_name, store_info in GROCERY_STORES.items():
            if search_term.lower() in store_name.lower():
                results.append((store_name, store_info, "Grocery Store"))
        for restaurant_name, restaurant_info in RESTAURANTS.items():
            if search_term.lower() in restaurant_name.lower():
                results.append((restaurant_name, restaurant_info, "Restaurant"))
        
        if results:
            for name, info, service_type in results:
                with st.expander(f"{name} ({service_type})"):
                    display_service(Service(
                        name=name,
                        url=info['url'],
                        instructions=info['instructions'],
                        video_url=info.get('video_url'),
                        video_title=info.get('video_title'),
                        image_url=info.get('image_url'),
                        address=info['address'],
                        phone=info['phone']
                    ))
        else:
            st.warning("No services found matching your search term.")

# Update the main function to include the search functionality
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
            "🗺️ Map": display_map,
            "🛍️ Services": display_services,
            "🔍 Search": search_services
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

if __name__ == "__main__":
    main()
