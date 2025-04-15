import streamlit as st
from streamlit_webrtc import webrtc_streamer
import av
import cv2
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
from functools import lru_cache
import requests
import json

# Page config
st.set_page_config(
    page_title="Local Butler",
    page_icon="https://raw.githubusercontent.com/LocalButler/streamlit_app.py/main/LOGO.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()

AUTH0_CLIENT_ID = st.secrets["auth0"]["AUTH0_CLIENT_ID"]
AUTH0_DOMAIN = st.secrets["auth0"]["AUTH0_DOMAIN"]
PAYPAL_CLIENT_ID = st.secrets["paypal"]["PAYPAL_CLIENT_ID"]

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
    merchant_id = Column(Integer, ForeignKey('merchants.id'), nullable=True)
    service = Column(String)
    date = Column(DateTime, nullable=False)
    time = Column(String, nullable=False)
    address = Column(String, nullable=False)
    status = Column(String, nullable=False)
    payment_status = Column(String, default="Pending")
    total_amount = Column(Float, default=0.0)
    user = relationship("User")
    merchant = relationship("Merchant")

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))
    partner_name = Column(String, nullable=False)
    subscription_id = Column(String, nullable=False)
    status = Column(String, default="Active")
    user = relationship("User")

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

@lru_cache(maxsize=100)
def geocode_with_retry(address, max_retries=3, initial_delay=1):
    geolocator = Nominatim(user_agent="local_butler_app")
    for attempt in range(max_retries):
        try:
            time.sleep(initial_delay * (2 ** attempt))
            location = geolocator.geocode(address)
            if location:
                return location
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            if attempt == max_retries - 1:
                st.warning(f"Could not geocode address: {address}. Error: {str(e)}")
                return None
    return None

@dataclass
class Service:
    name: str
    url: str
    instructions: list
    video_url: str = None
    image_url: str = None
    address: str = None
    phone: str = None
    hours: str = None

def display_service(service: Service):
    st.markdown(f"[**ORDER NOW**: {service.name}]({service.url})")
    if service.video_url:
        st.video(service.video_url)
    elif service.image_url:
        st.image(service.image_url, caption=f"{service.name}", use_column_width=True)
    st.write("**Instructions**:")
    for instruction in service.instructions:
        st.markdown(f"- {instruction}")
    if service.address:
        st.write(f"**Address**: {service.address}")
    if service.phone:
        st.write(f"**Phone**: {service.phone}")
    if service.hours:
        st.write(f"**Hours**: {service.hours}")

def update_map(address):
    location = geocode_with_retry(address)
    if location:
        m = folium.Map(location=[location.latitude, location.longitude], zoom_start=15)
        folium.Marker(
            [location.latitude, location.longitude],
            popup=f"Service Address: {address}"
        ).add_to(m)
        return m, location
    return None, None

# PayPal payment
def process_paypal_payment(order_id, amount):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_paypal_access_token()}"
    }
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": "USD",
                "value": f"{amount:.2f}"
            },
            "description": f"Local Butler Order {order_id}"
        }],
        "application_context": {
            "return_url": "https://localbutler.streamlit.app/success",
            "cancel_url": "https://localbutler.streamlit.app/cancel"
        }
    }
    response = requests.post(
        "https://api-m.sandbox.paypal.com/v2/checkout/orders",
        headers=headers,
        json=payload
    )
    if response.status_code == 201:
        return response.json()
    return None

def get_paypal_access_token():
    client_id = PAYPAL_CLIENT_ID
    client_secret = st.secrets["paypal"]["PAYPAL_CLIENT_SECRET"]
    response = requests.post(
        "https://api-m.sandbox.paypal.com/v1/oauth2/token",
        headers={"Accept": "application/json", "Accept-Language": "en_US"},
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"}
    )
    return response.json().get("access_token")

# Laundry pricing
def calculate_laundry_total(weight):
    RATE_PER_POUND = 2.00  # $2 per pound
    MINIMUM_WEIGHT = 5.0   # Minimum 5 pounds
    if weight < MINIMUM_WEIGHT:
        return MINIMUM_WEIGHT * RATE_PER_POUND
    return weight * RATE_PER_POUND

# Color palette
PRIMARY_COLOR = "#FF6B6B"
SECONDARY_COLOR = "#4ECDC4"
BACKGROUND_COLOR = "#FFFFFF"
ACCENT_COLOR = "#1A3C34"

# Modern CSS
st.markdown(f"""
    <style>
    .stApp {{
        background-color: {BACKGROUND_COLOR};
        font-family: 'Arial', sans-serif;
    }}
    .stButton>button {{
        background-color: {PRIMARY_COLOR};
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
        transition: all 0.3s ease;
    }}
    .stButton>button:hover {{
        background-color: {SECONDARY_COLOR};
        transform: scale(1.05);
    }}
    .stProgress > div > div > div > div {{
        background-color: {SECONDARY_COLOR};
    }}
    .sidebar .sidebar-content {{
        background-color: {ACCENT_COLOR};
        color: white;
    }}
    h1, h2, h3 {{
        color: {ACCENT_COLOR};
    }}
    </style>
    """, unsafe_allow_html=True)

# Service dictionaries
SERVICES = {
    "Groceries": {
        "Weis Markets": {
            "url": "https://www.weismarkets.com/",
            "instructions": [
                "Order directly with Weis Markets using your account.",
                "Select store pick-up and specify date/time.",
                "Notify Local Butler to coordinate."
            ],
            "address": "2288 Blue Water Boulevard, Odenton, MD 21113",
            "phone": "(410) 672-1877"
        }
    },
    "Restaurants": {
        "The Hideaway": {
            "url": "https://order.toasttab.com/online/hideawayodenton",
            "instructions": [
                "Order directly with The Hideaway.",
                "Select pick-up and specify date/time.",
                "Notify Local Butler to coordinate."
            ],
            "address": "1439 Odenton Rd, Odenton, MD 21113",
            "phone": "(410) 874-7213"
        }
    },
    "Dog Walking": {
        "Local Butler Dog Walking": {
            "url": "https://localbutler.streamlit.app",
            "instructions": [
                "Select duration (30 or 60 minutes).",
                "Specify time and address.",
                "Our team will walk your dog with care."
            ],
            "address": "Odenton, MD 21113",
            "phone": "(410) 555-1234",
            "hours": "Mon-Sun 7am-7pm"
        }
    },
    "Laundry": {
        "Local Butler Laundry": {
            "url": "https://localbutler.streamlit.app",
            "instructions": [
                "Enter estimated laundry weight below.",
                "Schedule pick-up time and address.",
                "Our drivers verify weight with a portable scale.",
                "We wash, dry, and deliver your clothes."
            ],
            "address": "Odenton, MD 21113",
            "phone": "(410) 555-5678",
            "hours": "Mon-Fri 8am-6pm"
        }
    },
    "Home Cleaning": {
        "Local Butler Cleaning": {
            "url": "https://localbutler.streamlit.app",
            "instructions": [
                "Select number of rooms and cleaning type.",
                "Schedule a time and address.",
                "Our team ensures a spotless home."
            ],
            "address": "Odenton, MD 21113",
            "phone": "(410) 555-9012",
            "hours": "Mon-Sat 9am-5pm"
        }
    },
    "Carwash/Detailing": {
        "Local Butler Carwash": {
            "url": "https://localbutler.streamlit.app",
            "instructions": [
                "Choose wash or detailing package.",
                "Schedule time and location.",
                "We make your car shine."
            ],
            "address": "Odenton, MD 21113",
            "phone": "(410) 555-3456",
            "hours": "Mon-Sun 8am-6pm"
        }
    }
}

PARTNERSHIPS = {
    "Factor": {
        "url": "https://www.factor75.com",
        "description": "Healthy, chef-prepared meals delivered to your door.",
        "subscription_url": "https://www.factor75.com/plans",
        "commission_rate": 0.10,
        "image_url": "https://example.com/factor_logo.jpg"
    }
}

def auth0_authentication():
    if 'user' not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        auth_choice = st.sidebar.radio("Choose action", ["🔑 Login"])
        if auth_choice == "🔑 Login":
            user_info = login_button(AUTH0_CLIENT_ID, domain=AUTH0_DOMAIN)
            if user_info:
                session = Session()
                user = session.query(User).filter_by(email=user_info['email']).first()
                if not user:
                    user = User(
                        id=user_info['sub'],
                        name=user_info['name'],
                        email=user_info['email'],
                        type='customer',
                        address=''
                    )
                    session.add(user)
                    session.commit()
                st.session_state.user = user
                st.success(f"Welcome, {user.name}!")
    return st.session_state.user

def main():
    st.markdown("<h1 style='text-align: center;'>🚚 Local Butler</h1>", unsafe_allow_html=True)

    user = auth0_authentication()

    if user:
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "🏠 Home"

        menu_items = {
            "🏠 Home": home_page,
            "🛒 Order Now": place_order,
            "📦 My Orders": display_user_orders,
            "🗺️ Map": display_map,
            "🛍️ Services": display_services,
            "🤝 Subscriptions": display_subscriptions,
        }

        cols = st.columns(len(menu_items))
        for i, (emoji_label, func) in enumerate(menu_items.items()):
            if cols[i].button(emoji_label, key=emoji_label):
                st.session_state.current_page = emoji_label

        menu_items[st.session_state.current_page]()
        
        if st.sidebar.button("🚪 Log Out"):
            st.session_state.user = None
            st.success("Logged out successfully.")
    else:
        st.write("Please log in to access Local Butler’s features.")

def home_page():
    st.markdown(f"Welcome, {st.session_state.user.name}! 🎉")
    st.write("Book local services or subscribe to premium partners.")
    session = Session()
    merchants = session.query(Merchant).all()
    st.write("**Available Services:**")
    for service_type in SERVICES:
        st.markdown(f"- {service_type}")

def place_order():
    st.subheader("🛒 Place a New Order")
    if 'selected_service_type' not in st.session_state:
        st.session_state.selected_service_type = None
    if 'selected_provider' not in st.session_state:
        st.session_state.selected_provider = None
    if 'date' not in st.session_state:
        st.session_state.date = datetime.now().date()
    if 'time' not in st.session_state:
        st.session_state.time = "07:00 AM EST"
    if 'address' not in st.session_state:
        st.session_state.address = st.session_state.user.address or ""
    if 'review_clicked' not in st.session_state:
        st.session_state.review_clicked = False
    if 'total_amount' not in st.session_state:
        st.session_state.total_amount = 0.0

    session = Session()
    service_type = st.selectbox("Select Service Type", list(SERVICES.keys()), key='selected_service_type')
    provider = st.selectbox("Select Provider", list(SERVICES[service_type].keys()), key='selected_provider')
    date = st.date_input("Select Date", min_value=datetime.now().date(), key='date')
    order_time = st.selectbox(
        "Select Time",
        [f"{h:02d}:{m:02d} {'AM' if h < 12 else 'PM'} EST" for h in range(7, 22) for m in [0, 15, 30, 45]],
        key='time'
    )
    address = st.text_input("Service Address", value=st.session_state.address, key='address')
    
    # Service-specific inputs
    if service_type == "Laundry":
        weight = st.number_input("Estimated Laundry Weight (lbs)", min_value=0.0, value=5.0, step=0.1)
        st.session_state.total_amount = calculate_laundry_total(weight)
        st.markdown(f"**Estimated Total**: ${st.session_state.total_amount:.2f} (based on $2/lb, minimum 5 lbs)")
        st.info("Our drivers will verify the weight with a portable scale at pick-up.")
    else:
        st.session_state.total_amount = st.number_input("Order Amount ($)", min_value=0.01, value=10.00, step=0.01)

    if address:
        map_obj, location = update_map(address)
        if map_obj:
            folium_static(map_obj)
            st.write(f"**Coordinates**: {location.latitude}, {location.longitude}")
        delivery_notes = st.text_area("Service Notes (optional)")

    if st.button("Review Order"):
        st.session_state.review_clicked = True

    if st.session_state.review_clicked:
        with st.expander("Order Details", expanded=True):
            st.write(f"**Service Type**: {service_type}")
            st.write(f"**Provider**: {provider}")
            st.write(f"**Date**: {date}")
            st.write(f"**Time**: {order_time}")
            st.write(f"**Address**: {address}")
            st.write(f"**Total**: ${st.session_state.total_amount:.2f}")
            if 'delivery_notes' in locals():
                st.write(f"**Notes**: {delivery_notes}")

        if st.button("💳 Pay with PayPal", key='paypal_button'):
            if not all([provider, date, order_time, address, st.session_state.total_amount]):
                st.error("Please fill in all required fields.")
            else:
                order_id = generate_order_id()
                paypal_response = process_paypal_payment(order_id, st.session_state.total_amount)
                if paypal_response:
                    new_order = Order(
                        id=order_id,
                        user_id=st.session_state.user.id,
                        service=service_type,
                        date=date,
                        time=order_time,
                        address=address,
                        status='Pending',
                        payment_status='Paid',
                        total_amount=st.session_state.total_amount
                    )
                    session.add(new_order)
                    session.commit()
                    st.markdown(
                        f"<a href='{paypal_response['links'][1]['href']}' target='_blank'>Complete Payment</a>",
                        unsafe_allow_html=True
                    )
                    st.success(f"Order {order_id} created! Complete payment via PayPal.")
                    st.session_state.review_clicked = False
                else:
                    st.error("Payment failed. Try again.")
                session.close()

def display_user_orders():
    st.subheader("📦 My Orders")
    session = Session()
    user_orders = session.query(Order).filter_by(user_id=st.session_state.user.id).all()
    
    if not user_orders:
        st.info("No orders yet.")
    else:
        for order in user_orders:
            with st.expander(f"🛍️ Order ID: {order.id} - Status: {order.status}"):
                st.write(f"**Date**: {order.date}")
                st.write(f"**Time**: {order.time}")
                st.write(f"**Address**: {order.address}")
                st.write(f"**Service**: {order.service}")
                st.write(f"**Total**: ${order.total_amount:.2f}")
                st.write(f"**Payment Status**: {order.payment_status}")
                statuses = ['Pending', 'Preparing', 'On the way', 'Delivered']
                status_emojis = ['⏳', '👨‍🍳', '🚚', '✅']
                current_status_index = statuses.index(order.status)
                progress = (current_status_index + 1) * 25
                st.progress(progress)
                cols = st.columns(4)
                for i, (status, emoji) in enumerate(zip(statuses, status_emojis)):
                    cols[i].markdown(
                        f"<p style='text-align: center; color: {'blue' if i == current_status_index else 'green' if i < current_status_index else 'gray'}'>{emoji}<br>{status}</p>",
                        unsafe_allow_html=True
                    )
    session.close()

def display_map():
    st.subheader("🗺️ Service Map")
    businesses_to_show = {}
    for service_type, providers in SERVICES.items():
        businesses_to_show.update(providers)
    if not businesses_to_show:
        st.warning("No services found.")
        return
    map_obj = create_map(businesses_to_show)
    folium_static(map_obj)

def display_services():
    st.subheader("🛍️ Available Services")
    for service_name, providers in SERVICES.items():
        st.markdown(f"### {service_name}")
        for provider_name, provider_info in providers.items():
            with st.expander(provider_name):
                display_service(Service(
                    name=provider_name,
                    url=provider_info['url'],
                    instructions=provider_info['instructions'],
                    address=provider_info.get('address'),
                    phone=provider_info.get('phone'),
                    hours=provider_info.get('hours')
                ))

def display_subscriptions():
    st.subheader("🤝 Partner Subscriptions")
    st.write("Subscribe to premium services for exclusive benefits!")
    session = Session()
    for partner_name, partner_info in PARTNERSHIPS.items():
        with st.expander(partner_name):
            if partner_info.get('image_url'):
                st.image(partner_info['image_url'], caption=partner_name, use_column_width=True)
            st.write(f"**Description**: {partner_info['description']}")
            if st.button(f"Subscribe to {partner_name}", key=f"sub_{partner_name}"):
                st.markdown(f"[Start Your Subscription]({partner_info['subscription_url']})")
                subscription_id = f"SUB-{random.randint(10000, 99999)}"
                new_subscription = Subscription(
                    user_id=st.session_state.user.id,
                    partner_name=partner_name,
                    subscription_id=subscription_id,
                    status="Active"
                )
                session.add(new_subscription)
                session.commit()
                st.success(f"Subscribed to {partner_name}! Commission tracked.")
    session.close()

def driver_dashboard():
    st.subheader("🚗 Driver Dashboard")
    session = Session()
    orders_container = st.empty()
    while True:
        available_orders = session.query(Order).filter_by(status='Pending').all()
        with orders_container.container():
            if not available_orders:
                st.info("No pending orders.")
            else:
                for order in available_orders:
                    with st.expander(f"📦 Order ID: {order.id}"):
                        st.write(f"**Service**: {order.service}")
                        st.write(f"**Address**: {order.address}")
                        st.write(f"**Total**: ${order.total_amount:.2f}")
                        if order.service == "Laundry":
                            st.info("Verify laundry weight with portable scale at pick-up.")
                        if st.button(f"✅ Accept Order {order.id}", key=f"accept_{order.id}"):
                            order.status = 'Preparing'
                            session.commit()
                            st.success(f"Accepted order {order.id}!")
                            time.sleep(2)
                            st.experimental_rerun()
        time.sleep(10)
        session.commit()
    session.close()

def live_shop():
    st.subheader("📹 LIVE SHOP")
    all_stores = {**SERVICES["Groceries"], **SERVICES["Restaurants"]}
    if 'selected_store' not in st.session_state:
        st.session_state.selected_store = None
    if 'live_session_active' not in st.session_state:
        st.session_state.live_session_active = False
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []

    selected_store = st.selectbox("Select a Store", list(all_stores.keys()), index=0 if st.session_state.selected_store is None else list(all_stores.keys()).index(st.session_state.selected_store))
    
    if selected_store != st.session_state.selected_store:
        st.session_state.selected_store = selected_store
        st.session_state.live_session_active = False
        st.session_state.chat_messages = []

    if not st.session_state.selected_store:
        st.warning("Please select a store.")
        return

    store_info = all_stores[st.session_state.selected_store]
    st.write(f"**Address**: {store_info['address']}")
    st.write(f"**Phone**: {store_info['phone']}")

    if st.button("START LIVE SESSION" if not st.session_state.live_session_active else "END LIVE SESSION"):
        st.session_state.live_session_active = not st.session_state.live_session_active

    if st.session_state.live_session_active:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Your Camera**")
            def user_video_frame_callback(frame):
                img = frame.to_ndarray(format="bgr24")
                cv2.putText(img, f"User - Local Butler", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                return av.VideoFrame.from_ndarray(img, format="bgr24")
            webrtc_streamer(
                key=f"user_live_shop_{st.session_state.selected_store}",
                video_frame_callback=user_video_frame_callback,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
            )
        with col2:
            st.markdown(f"**{st.session_state.selected_store} Associate**")
            def merchant_video_frame_callback(frame):
                img = frame.to_ndarray(format="bgr24")
                cv2.putText(img, f"{st.session_state.selected_store}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                return av.VideoFrame.from_ndarray(img, format="bgr24")
            webrtc_streamer(
                key=f"merchant_live_shop_{st.session_state.selected_store}",
                video_frame_callback=merchant_video_frame_callback,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
            )

        st.markdown(f"**Chat with {st.session_state.selected_store}**")
        for message in st.session_state.chat_messages:
            st.text(message)
        user_message = st.text_input("Type your message:", key="chat_input")
        if st.button("Send", key="send_chat"):
            st.session_state.chat_messages.append(f"You: {user_message}")
            st.experimental_rerun()

if __name__ == "__main__":
    main()
