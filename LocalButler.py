import streamlit as st
from streamlit_webrtc import webrtc_streamer
import av
import cv2
import folium
from streamlit_folium import folium_static
from datetime import datetime
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
import stripe
import threading
import logging

# Logging setup for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Local Butler",
    page_icon="🦸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
load_dotenv()

# Secrets (replace with your actual secrets in deployment)
try:
    AUTH0_CLIENT_ID = st.secrets["auth0"]["AUTH0_CLIENT_ID"]
    AUTH0_DOMAIN = st.secrets["auth0"]["AUTH0_DOMAIN"]
    STRIPE_SECRET_KEY = st.secrets["stripe"]["STRIPE_SECRET_KEY"]
    STRIPE_PUBLISHABLE_KEY = st.secrets["stripe"]["STRIPE_PUBLISHABLE_KEY"]
except KeyError as e:
    st.error(f"Missing secret: {e}")
    st.stop()

# Initialize Stripe
stripe.api_key = STRIPE_SECRET_KEY

# SQLAlchemy setup with connection pooling
Base = sqlalchemy.orm.declarative_base()
engine = create_engine(
    st.secrets["database"]["url"],
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30
)
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
    payment_method = Column(String, default="Online")
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

@st.cache_data
def create_map(_hash):
    try:
        session = Session()
        merchants = session.query(Merchant).all()
        if not merchants:
            st.warning("No services found.")
            return None
        m = folium.Map(location=[39.1054, -76.7285], zoom_start=12)
        for merchant in merchants:
            popup_html = f"""
            <b>{merchant.name}</b><br>
            Type: {merchant.type}<br>
            Website: <a href='{merchant.website}' target='_blank'>Visit</a>
            """
            folium.Marker(
                [merchant.latitude, merchant.longitude],
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(m)
        return m
    except Exception as e:
        logger.error(f"Map creation error: {e}")
        st.error("Failed to load map.")
        return None
    finally:
        session.close()

@lru_cache(maxsize=100)
def geocode_with_retry(address, max_retries=3, initial_delay=1):
    geolocator = Nominatim(user_agent="local_butler_app")
    for attempt in range(max_retries):
        try:
            time.sleep(initial_delay * (2 ** attempt))
            location = geolocator.geocode(address)
            if location:
                geocoding_cache[address] = location
                return location
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            if attempt == max_retries - 1:
                logger.warning(f"Geocoding failed for {address}: {e}")
                return None
    return None

def async_geocode(address, callback):
    def geocode_task():
        location = geocode_with_retry(address)
        callback(location)
    threading.Thread(target=geocode_task, daemon=True).start()

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
        st.image(service.image_url, caption=service.name, use_column_width=True)
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
    if 'map_location' not in st.session_state:
        st.session_state.map_location = None
    def set_location(location):
        st.session_state.map_location = location
        st.experimental_rerun()
    async_geocode(address, set_location)
    if st.session_state.map_location:
        m = folium.Map(location=[st.session_state.map_location.latitude, st.session_state.map_location.longitude], zoom_start=15)
        folium.Marker(
            [st.session_state.map_location.latitude, st.session_state.map_location.longitude],
            popup=f"Service Address: {address}"
        ).add_to(m)
        return m, st.session_state.map_location
    return None, None

# Stripe online payment
def create_stripe_checkout_session(order_id, amount, service_type):
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f"Local Butler {service_type} - Order {order_id}"
                    },
                    'unit_amount': int(amount * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url="http://localhost:8501/success",
            cancel_url="http://localhost:8501/cancel"
        )
        return checkout_session
    except Exception as e:
        logger.error(f"Stripe error: {e}")
        st.error("Payment processing failed.")
        return None

# Laundry pricing
def calculate_laundry_total(weight):
    RATE_PER_POUND = 2.00
    MINIMUM_WEIGHT = 5.0
    return max(weight, MINIMUM_WEIGHT) * RATE_PER_POUND

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

# Updated SERVICES dictionary (simplified for brevity, replace with your full data)
SERVICES = {
    "Groceries": {
        "Weis Markets": {
            "url": "https://www.weismarkets.com",
            "instructions": ["Order online.", "Select pick-up.", "Notify Butler."],
            "address": "2288 Blue Water Boulevard, Odenton, MD 21113",
            "phone": "(410) 672-1877"
        }
    },
    "Restaurants": {
        "The Hideaway": {
            "url": "https://thehideaway.com",
            "instructions": ["Order online.", "Select pick-up.", "Notify Butler."],
            "address": "1439 Odenton Rd, Odenton, MD 21113",
            "phone": "(410) 874-7213"
        }
    },
    "Laundry": {
        "Local Butler Laundry": {
            "url": "http://localhost:8501",
            "instructions": ["Enter weight.", "Schedule pick-up.", "We wash and deliver."],
            "address": "Odenton, MD 21113",
            "phone": "(410) 555-5678",
            "hours": "Mon-Fri 8am-6pm"
        }
    }
}

PARTNERSHIPS = {
    "Factor": {
        "url": "https://www.factor75.com",
        "description": "Healthy meals delivered.",
        "subscription_url": "https://www.factor75.com/plans",
        "commission_rate": 0.10,
        "image_url": "https://via.placeholder.com/150"
    }
}

def populate_merchants():
    if 'merchants_populated' not in st.session_state:
        st.session_state.merchants_populated = False
    if st.session_state.merchants_populated:
        return
    try:
        session = Session()
        for service_type, providers in SERVICES.items():
            for provider_name, provider_info in providers.items():
                merchant = session.query(Merchant).filter_by(name=provider_name).first()
                if not merchant:
                    location = geocode_with_retry(provider_info['address'])
                    if location:
                        merchant = Merchant(
                            name=provider_name,
                            type=service_type,
                            latitude=location.latitude,
                            longitude=location.longitude,
                            website=provider_info['url']
                        )
                        session.add(merchant)
                    else:
                        logger.warning(f"Failed to geocode {provider_name}")
        session.commit()
        st.session_state.merchants_populated = True
    except Exception as e:
        logger.error(f"Populate merchants error: {e}")
        st.error("Failed to initialize merchants.")
    finally:
        session.close()

def auth0_authentication():
    if 'user' not in st.session_state:
        st.session_state.user = None
    if st.session_state.user is None:
        auth_choice = st.sidebar.radio("Choose action", ["🔑 Login"])
        if auth_choice == "🔑 Login":
            try:
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
                    session.close()
            except Exception as e:
                logger.error(f"Auth0 error: {e}")
                st.error("Login failed.")
    return st.session_state.user

def main():
    st.markdown("<h1 style='text-align: center;'>🚚 Local Butler</h1>", unsafe_allow_html=True)
    populate_merchants()

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
            "🚗 Driver Dashboard": driver_dashboard,
            "📹 LIVE SHOP": live_shop
        }

        cols = st.columns(len(menu_items))
        for i, (emoji_label, _) in enumerate(menu_items.items()):
            if cols[i].button(emoji_label, key=emoji_label):
                st.session_state.current_page = emoji_label

        menu_items[st.session_state.current_page]()

        if st.sidebar.button("🚪 Log Out"):
            st.session_state.user = None
            st.session_state.current_page = "🏠 Home"
            st.success("Logged out successfully.")
    else:
        st.write("Please log in to access Local Butler’s features.")

def home_page():
    st.markdown(f"Welcome, {st.session_state.user.name}! 🎉")
    st.write("Book local services or subscribe to premium partners.")
    st.write("**Available Services:**")
    for service_type in SERVICES:
        st.markdown(f"- {service_type}")

def place_order():
    st.subheader("🛒 Place a New Order")
    if 'order_state' not in st.session_state:
        st.session_state.order_state = {
            'selected_service_type': None,
            'selected_provider': None,
            'date': datetime.now().date(),
            'time': "07:00 AM EST",
            'address': st.session_state.user.address or "",
            'review_clicked': False,
            'total_amount': 0.0,
            'payment_method': "Online"
        }

    state = st.session_state.order_state
    session = Session()
    try:
        service_type = st.selectbox("Select Service Type", list(SERVICES.keys()), key='selected_service_type')
        if service_type not in SERVICES:
            st.error("Invalid service type.")
            return
        state['selected_service_type'] = service_type

        provider = st.selectbox("Select Provider", list(SERVICES[service_type].keys()), key='selected_provider')
        if provider not in SERVICES[service_type]:
            st.error("Invalid provider.")
            return
        state['selected_provider'] = provider

        merchant = session.query(Merchant).filter_by(name=provider).first()
        if not merchant:
            st.error(f"Provider {provider} not found.")
            return

        state['date'] = st.date_input("Select Date", min_value=datetime.now().date(), value=state['date'])
        state['time'] = st.selectbox(
            "Select Time",
            [f"{h:02d}:{m:02d} {'AM' if h < 12 else 'PM'} EST" for h in range(7, 22) for m in [0, 15, 30, 45]],
            index=0
        )
        state['address'] = st.text_input("Service Address", value=state['address'])

        if service_type == "Laundry":
            weight = st.number_input("Estimated Laundry Weight (lbs)", min_value=0.0, value=5.0, step=0.1)
            state['total_amount'] = calculate_laundry_total(weight)
            st.markdown(f"**Estimated Total**: ${state['total_amount']:.2f}")
            st.info("Weight will be verified at pick-up.")
        else:
            state['total_amount'] = st.number_input("Order Amount ($)", min_value=0.01, value=10.00, step=0.01)

        state['payment_method'] = st.radio("Payment Method", ["Online", "In-Person (Tap to Pay)"])

        if state['address']:
            with st.spinner("Loading map..."):
                map_obj, location = update_map(state['address'])
            if map_obj:
                folium_static(map_obj)
                if location:
                    st.write(f"**Coordinates**: {location.latitude}, {location.longitude}")
            delivery_notes = st.text_area("Service Notes (optional)")

        if st.button("Review Order"):
            state['review_clicked'] = True

        if state['review_clicked']:
            with st.expander("Order Details", expanded=True):
                st.write(f"**Service Type**: {state['selected_service_type']}")
                st.write(f"**Provider**: {state['selected_provider']}")
                st.write(f"**Date**: {state['date']}")
                st.write(f"**Time**: {state['time']}")
                st.write(f"**Address**: {state['address']}")
                st.write(f"**Total**: ${state['total_amount']:.2f}")
                st.write(f"**Payment Method**: {state['payment_method']}")
                if 'delivery_notes' in locals():
                    st.write(f"**Notes**: {delivery_notes}")

            if state['payment_method'] == "Online":
                if st.button("💳 Pay with Card"):
                    if not all([state['selected_provider'], state['date'], state['time'], state['address'], state['total_amount']]):
                        st.error("Please fill in all fields.")
                    else:
                        order_id = generate_order_id()
                        checkout_session = create_stripe_checkout_session(order_id, state['total_amount'], state['selected_service_type'])
                        if checkout_session:
                            new_order = Order(
                                id=order_id,
                                user_id=st.session_state.user.id,
                                merchant_id=merchant.id,
                                service=state['selected_service_type'],
                                date=state['date'],
                                time=state['time'],
                                address=state['address'],
                                status='Pending',
                                payment_status='Pending',
                                payment_method='Online',
                                total_amount=state['total_amount']
                            )
                            session.add(new_order)
                            session.commit()
                            st.markdown(
                                f"""
                                <script src="https://js.stripe.com/v3/"></script>
                                <script>
                                    var stripe = Stripe('{STRIPE_PUBLISHABLE_KEY}');
                                    stripe.redirectToCheckout({{ sessionId: '{checkout_session.id}' }});
                                </script>
                                """,
                                unsafe_allow_html=True
                            )
                            state['review_clicked'] = False
                        else:
                            st.error("Payment failed.")
            else:
                if st.button("✅ Confirm In-Person Payment"):
                    if not all([state['selected_provider'], state['date'], state['time'], state['address'], state['total_amount']]):
                        st.error("Please fill in all fields.")
                    else:
                        order_id = generate_order_id()
                        new_order = Order(
                            id=order_id,
                            user_id=st.session_state.user.id,
                            merchant_id=merchant.id,
                            service=state['selected_service_type'],
                            date=state['date'],
                            time=state['time'],
                            address=state['address'],
                            status='Pending',
                            payment_status='Pending',
                            payment_method='In-Person',
                            total_amount=state['total_amount']
                        )
                        session.add(new_order)
                        session.commit()
                        st.success(f"Order {order_id} created! Payment will be collected in-person.")
                        state['review_clicked'] = False
    except Exception as e:
        logger.error(f"Place order error: {e}")
        st.error("An error occurred while placing the order.")
    finally:
        session.close()

@st.cache_data
def get_user_orders(user_id):
    session = Session()
    try:
        orders = session.query(Order).filter_by(user_id=user_id).all()
        return orders
    except Exception as e:
        logger.error(f"Get user orders error: {e}")
        return []
    finally:
        session.close()

def display_user_orders():
    st.subheader("📦 My Orders")
    user_orders = get_user_orders(st.session_state.user.id)
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
                st.write(f"**Payment Method**: {order.payment_method}")
                session = Session()
                try:
                    merchant = session.query(Merchant).filter_by(id=order.merchant_id).first()
                    if merchant:
                        st.write(f"**Merchant**: {merchant.name}")
                finally:
                    session.close()
                statuses = ['Pending', 'Preparing', 'On the way', 'Delivered']
                status_emojis = ['⏳', '👨‍🍳', '🚚', '✅']
                try:
                    current_status_index = statuses.index(order.status)
                except ValueError:
                    current_status_index = 0
                progress = (current_status_index + 1) * 25
                st.progress(progress)
                cols = st.columns(4)
                for i, (status, emoji) in enumerate(zip(statuses, status_emojis)):
                    cols[i].markdown(
                        f"<p style='text-align: center; color: {'blue' if i == current_status_index else 'green' if i < current_status_index else 'gray'}'>{emoji}<br>{status}</p>",
                        unsafe_allow_html=True
                    )

def display_map():
    st.subheader("🗺️ Service Map")
    map_hash = str(random.randint(0, 1000000))  # Force cache refresh if needed
    map_obj = create_map(map_hash)
    if map_obj:
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
    try:
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
                    st.success(f"Subscribed to {partner_name}!")
    except Exception as e:
        logger.error(f"Subscriptions error: {e}")
        st.error("Failed to process subscription.")
    finally:
        session.close()

@st.cache_data
def get_pending_orders():
    session = Session()
    try:
        orders = session.query(Order).filter_by(status='Pending').all()
        return orders
    except Exception as e:
        logger.error(f"Get pending orders error: {e}")
        return []
    finally:
        session.close()

def driver_dashboard():
    st.subheader("🚗 Driver Dashboard")
    orders_container = st.container()
    with orders_container:
        available_orders = get_pending_orders()
        if not available_orders:
            st.info("No pending orders.")
        else:
            for order in available_orders:
                with st.expander(f"📦 Order ID: {order.id}"):
                    st.write(f"**Service**: {order.service}")
                    st.write(f"**Address**: {order.address}")
                    st.write(f"**Total**: ${order.total_amount:.2f}")
                    st.write(f"**Payment Method**: {order.payment_method}")
                    session = Session()
                    try:
                        merchant = session.query(Merchant).filter_by(id=order.merchant_id).first()
                        if merchant:
                            st.write(f"**Pickup**: {merchant.name}")
                    finally:
                        session.close()
                    if order.service == "Laundry":
                        st.info("Verify laundry weight at pick-up.")
                    if order.payment_method == "In-Person":
                        st.warning("Collect payment via Tap to Pay.")
                    if st.button(f"✅ Accept Order {order.id}", key=f"accept_{order.id}"):
                        session = Session()
                        try:
                            order_to_update = session.query(Order).filter_by(id=order.id).first()
                            if order_to_update:
                                order_to_update.status = 'Preparing'
                                session.commit()
                                st.success(f"Accepted order {order.id}!")
                        except Exception as e:
                            logger.error(f"Accept order error: {e}")
                            st.error("Failed to accept order.")
                        finally:
                            session.close()
    if st.button("Refresh Orders"):
        st.experimental_rerun()

def live_shop():
    st.subheader("📹 LIVE SHOP")
    all_stores = {**SERVICES["Groceries"], **SERVICES["Restaurants"]}
    if 'live_shop_state' not in st.session_state:
        st.session_state.live_shop_state = {
            'selected_store': None,
            'live_session_active': False,
            'chat_messages': []
        }

    state = st.session_state.live_shop_state
    selected_store = st.selectbox("Select a Store", list(all_stores.keys()), index=0 if state['selected_store'] is None else list(all_stores.keys()).index(state['selected_store']))

    if selected_store != state['selected_store']:
        state['selected_store'] = selected_store
        state['live_session_active'] = False
        state['chat_messages'] = []

    if not state['selected_store']:
        st.warning("Please select a store.")
        return

    store_info = all_stores[state['selected_store']]
    st.write(f"**Address**: {store_info['address']}")
    st.write(f"**Phone**: {store_info['phone']}")

    if st.button("START LIVE SESSION" if not state['live_session_active'] else "END LIVE SESSION"):
        state['live_session_active'] = not state['live_session_active']
        if state['live_session_active']:
            st.info("Starting live session...")
            time.sleep(1)

    if state['live_session_active']:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Your Camera**")
            def user_video_frame_callback(frame):
                img = frame.to_ndarray(format="bgr24")
                cv2.putText(img, "User - Local Butler", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                return av.VideoFrame.from_ndarray(img, format="bgr24")
            webrtc_streamer(
                key=f"user_live_shop_{state['selected_store']}",
                video_frame_callback=user_video_frame_callback,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
            )
        with col2:
            st.markdown(f"**{state['selected_store']} Associate**")
            def merchant_video_frame_callback(frame):
                img = frame.to_ndarray(format="bgr24")
                cv2.putText(img, state['selected_store'], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                return av.VideoFrame.from_ndarray(img, format="bgr24")
            webrtc_streamer(
                key=f"merchant_live_shop_{state['selected_store']}",
                video_frame_callback=merchant_video_frame_callback,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
            )

        st.markdown(f"**Chat with {state['selected_store']}**")
        for message in state['chat_messages']:
            st.text(message)
        user_message = st.text_input("Type your message:", key=f"chat_input_{state['selected_store']}")
        if st.button("Send", key=f"send_chat_{state['selected_store']}"):
            if user_message:
                state['chat_messages'].append(f"You: {user_message}")
                st.experimental_rerun()

if __name__ == "__main__":
    main()
