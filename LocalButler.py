import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import folium_static
from datetime import datetime, timedelta
import random
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import time
import sqlalchemy
from dataclasses import dataclass
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import os
from dotenv import load_dotenv
from auth0_component import login_button

# Load environment variables
load_dotenv()

AUTH0_CLIENT_ID = st.secrets["auth0"]["AUTH0_CLIENT_ID"]
AUTH0_DOMAIN = st.secrets["auth0"]["AUTH0_DOMAIN"]
AUTH0_CALLBACK_URL = os.getenv("https://localbutler.streamlit.app/")


# SQLAlchemy setup
Base = sqlalchemy.orm.declarative_base()
engine = create_engine(st.secrets["database"]["url"], echo=True)
Session = sessionmaker(bind=engine)

# SQLAlchemy models
class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)
    address = Column(String)

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
    user_id = Column(String, ForeignKey('users.id'))
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
Base.metadata.create_all(engine, checkfirst=True)

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
            popup_html = f"""
            <b>{name}</b><br>
            Address: {info['address']}<br>
            Phone: {info['phone']}<br>
            """
            if 'url' in info and info['url']:
                popup_html += f"<a href='{info['url']}' target='_blank'>Visit Website</a>"
            
            folium.Marker(
                [location.latitude, location.longitude],
                popup=folium.Popup(popup_html, max_width=300)
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
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            if attempt == max_retries - 1:
                st.warning(f"Could not geocode address: {address}. Error: {str(e)}")
                return None
            time.sleep(2)  # Wait for 2 seconds before retrying
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
    # ... (other grocery stores)
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
    # ... (other restaurants)
}

def auth0_authentication():
    if 'user' not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        auth_choice = st.sidebar.radio("Choose action", ["🔑 Login", "📝 Register"])
        
        if auth_choice == "🔑 Login":
            user_info = login_button(AUTH0_CLIENT_ID, domain=AUTH0_DOMAIN)
            
            if user_info:
                session = Session()
                user = session.query(User).filter_by(email=user_info['email']).first()
                if not user:
                    # Create a new user if they don't exist in your database
                    user = User(
                        id=user_info['sub'],
                        name=user_info['name'],
                        email=user_info['email'],
                        type='customer',  # Default type, can be updated later
                        address=''  # Can be updated later
                    )
                    session.add(user)
                    session.commit()
                
                st.session_state.user = user
                st.success(f"Welcome, {user.name}!")
                st.experimental_rerun()
        else:
            st.markdown(f"""
            <a href="https://{AUTH0_DOMAIN}/authorize?response_type=code&client_id={AUTH0_CLIENT_ID}&redirect_uri={https://localbutler.streamlit.app/}&scope=openid%20profile%20email&screen_hint=signup" target="_self">
            Register with Auth0
            </a>
            """, unsafe_allow_html=True)

    return st.session_state.user

def main():
    st.title("🚚 Local Butler")

    user = auth0_authentication()

    if user:
        # Creative menu
        menu_items = {
            "🏠 Home": home_page,
            "🛒 Order Now": place_order,
            "📦 My Orders": display_user_orders,
            "🗺️ Map": display_map,
            "🛍️ Services": display_services,
            "🔍 Search": search_services
        }
        if user.type == 'driver':
            menu_items["🚗 Driver Dashboard"] = driver_dashboard

        cols = st.columns(len(menu_items))
        for i, (emoji_label, func) in enumerate(menu_items.items()):
            if cols[i].button(emoji_label):
                func()

        if st.sidebar.button("🚪 Log Out"):
            st.session_state.user = None
            st.success("Logged out successfully.")
            st.experimental_rerun()
    else:
        st.write("Please log in to access the full features of the app")

def home_page():
    st.write(f"Welcome to Local Butler, {st.session_state.user.name}! 🎉")
    session = Session()
    merchants = session.query(Merchant).all()
    st.write("Here are the available merchants:")
    for merchant in merchants:
        st.write(f"- {merchant.name}")

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
    
    businesses_to_show = {}
    businesses_to_show.update(GROCERY_STORES)
    businesses_to_show.update(RESTAURANTS)

    if not businesses_to_show:
        st.warning("No businesses found to display on the map.")
        return

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

if __name__ == "__main__":
    main()
