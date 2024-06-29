import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date, Time, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from dataclasses import dataclass
from datetime import datetime, time, timedelta
import argon2
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import folium
from streamlit_folium import st_folium
import geopy
from geopy.geocoders import Nominatim

# Set page config at the very beginning
st.set_page_config(page_title="Local Butler")

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()

class UserModel(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password = Column(String)
    user_type = Column(String)
    failed_attempts = Column(Integer, default=0)
    last_attempt = Column(DateTime)
    orders = relationship("OrderModel", back_populates="user", foreign_keys="OrderModel.user_id")

class OrderModel(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    driver_id = Column(Integer, ForeignKey('users.id'))
    service = Column(String)
    date = Column(Date)
    time = Column(Time)
    location = Column(String)
    status = Column(String)
    delivery_notes = Column(String)
    user = relationship("UserModel", back_populates="orders", foreign_keys=[user_id])
    driver = relationship("UserModel", foreign_keys=[driver_id])

class ScheduleModel(Base):
    __tablename__ = 'schedule'
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    time = Column(Time)
    available = Column(Boolean)

# Initialize database connection
@st.cache(allow_output_mutation=True)
def init_db():
    engine = create_engine(st.secrets["db_connection_string"])
    Base.metadata.create_all(engine)
    return engine

engine = init_db()
Session = sessionmaker(bind=engine)

# Dataclasses
@dataclass
class User:
    id: int
    username: str
    password: str
    user_type: str
    failed_attempts: int
    last_attempt: datetime

@dataclass
class Order:
    id: int
    user_id: int
    service: str
    date: datetime.date
    time: time
    location: str
    status: str
    driver_id: int
    delivery_notes: str

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

# Security
ph = argon2.PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(hashed_password: str, password: str) -> bool:
    try:
        ph.verify(hashed_password, password)
        return True
    except argon2.exceptions.VerifyMismatchError:
        return False

# Error handling
def handle_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            st.error(f"An error occurred: {str(e)}")
    return wrapper

# Logging decorator
def log_action(action: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.info(f"User {st.session_state.get('username', 'Anonymous')} performed action: {action}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

# UI Components
def create_form(fields):
    values = {}
    for field, field_type in fields.items():
        if field_type == 'text':
            values[field] = st.text_input(field.capitalize())
        elif field_type == 'password':
            values[field] = st.text_input(field.capitalize(), type='password')
        elif field_type == 'date':
            values[field] = st.date_input(field.capitalize())
        elif field_type == 'time':
            values[field] = st.time_input(field.capitalize())
        elif field_type == 'select':
            values[field] = st.selectbox(field.capitalize(), field_type[1])
    return values

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

# Authentication
@handle_error
def authenticate_user(username: str, password: str) -> tuple:
    with Session() as session:
        user = session.query(UserModel).filter_by(username=username).first()
        if user:
            if user.last_attempt and user.last_attempt + timedelta(minutes=15) > datetime.now() and user.failed_attempts >= 5:
                return False, "Account locked. Try again later.", None, None
            if verify_password(user.password, password):
                user.failed_attempts = 0
                user.last_attempt = None
                session.commit()
                return True, "Login successful", user.user_type, user.id
            else:
                user.failed_attempts += 1
                user.last_attempt = datetime.now()
                session.commit()
                return False, "Invalid username or password", None, None
        return False, "Invalid username or password", None, None

# Order placement
@handle_error
@log_action("place_order")
def place_order(user_id: int, service: str, date: datetime.date, time: time, location: str, delivery_notes: str) -> int:
    with Session() as session:
        schedule = session.query(ScheduleModel).filter_by(date=date, time=time).first()
        if schedule and schedule.available:
            order = OrderModel(user_id=user_id, service=service, date=date, time=time, location=location, status="Pending", delivery_notes=delivery_notes)
            session.add(order)
            schedule.available = False
            session.commit()
            return order.id
        return None

def create_map(businesses_to_show):
    geolocator = Nominatim(user_agent="local_butler_app")
    m = folium.Map(location=[39.1054, -76.7285], zoom_start=12)  # Centered on Fort Meade area

    for name, info in businesses_to_show.items():
        try:
            location = geolocator.geocode(info['address'])
            if location:
                popup_html = f"""
                <b>{name}</b><br>
                Address: {info['address']}<br>
                Phone: {info['phone']}<br>
                Hours: {info['hours']}
                """
                folium.Marker(
                    [location.latitude, location.longitude],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=name
                ).add_to(m)
        except Exception as e:
            st.warning(f"Could not locate {name}: {str(e)}")

    return m

# Create maps
grocery_map = create_map(GROCERY_STORES)
restaurant_map = create_map(RESTAURANTS)
all_businesses = {**GROCERY_STORES, **RESTAURANTS}
combined_map = create_map(all_businesses)

# Display maps in your Streamlit app
st.subheader("Grocery Stores Map")
st.folium_chart(grocery_map)

st.subheader("Restaurants Map")
st.folium_chart(restaurant_map)

st.subheader("All Businesses Map")
st.folium_chart(combined_map)

# Email sending
def send_email(subject: str, body: str):
    sender_email = st.secrets["email"]["sender"]
    receiver_email = st.secrets["email"]["receiver"]
    password = st.secrets["email"]["password"]

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

# Service data
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
        "address": "2641 Brandermill Blvd, Gambrills, MD 21054",
        "phone": "(410) 721-7440",
        "hours": "Open daily 6am-11pm"
    },
    "SafeWay": {
        "url": "https://www.safeway.com/",
        "instructions": [
            "Place your order directly with Safeway using your own account to accumulate grocery store points and clip your favorite coupons.",
            "Select store pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "image_url": "https://raw.githubusercontent.com/LocalButler/streamlit_app.py/main/safeway%20app%20ads.png",
        "address": "2624 Chapel Lake Dr, Gambrills, MD 21054",
        "phone": "(410) 721-0881",
        "hours": "Open daily 6am-11pm"
    },
    "Commissary": {
        "url": "https://shop.commissaries.com/",
        "instructions": [
            "Place your order directly with the Commissary using your own account.",
            "Select store pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "image_url": "https://raw.githubusercontent.com/LocalButler/streamlit_app.py/main/comissaries.jpg",
        "address": "2789 MacArthur Rd, Fort Meade, MD 20755",
        "phone": "(301) 677-3060",
        "hours": "Mon-Sat 9am-7pm, Sun 10am-6pm"
    },
    "Food Lion": {
        "url": "https://shop.foodlion.com/?shopping_context=pickup&store=2517",
        "instructions": [
            "Place your order directly with Food Lion using your own account.",
            "Select store pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "image_url": "https://raw.githubusercontent.com/LocalButler/streamlit_app.py/main/foodlionhomedelivery.jpg",
        "address": "1077 MD-3 North, Gambrills, MD 21054",
        "phone": "(410) 721-5830",
        "hours": "Open daily 7am-10pm"
    }
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
        "phone": "(410) 874-7213",
        "hours": "Mon-Sat 11am-9pm, Sun 11am-8pm"
    },
    "Ruth's Chris Steak House": {
        "url": "https://order.ruthschris.com/",
        "instructions": [
            "Place your order directly with Ruth's Chris Steak House using their website or app.",
            "Select pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "address": "1110 Town Center Blvd, Odenton, MD 21113",
        "phone": "(410) 451-9600",
        "hours": "Mon-Thur 4pm-10pm, Fri-Sat 4pm-11pm, Sun 4pm-9pm"
    },
    "Baltimore Coffee & Tea Company": {
        "url": "https://www.baltcoffee.com/sites/default/files/pdf/2023WebMenu_1.pdf",
        "instructions": [
            "Review the menu and decide on your order.",
            "Call Baltimore Coffee & Tea Company to place your order.",
            "Specify that you'll be using Local Butler for pick-up and delivery.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!",
            "We apologize for any inconvenience, but Baltimore Coffee & Tea Company does not currently offer online ordering."
        ],
        "address": "8488 Baltimore Annapolis Blvd, Pasadena, MD 21122",
        "phone": "(410) 439-8669",
        "hours": "Mon-Sat 6am-6pm, Sun 7am-5pm"
    },
    "The All American Steakhouse": {
        "url": "https://order.theallamericansteakhouse.com/menu/odenton",
        "instructions": [
            "Place your order directly with The All American Steakhouse by using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "address": "2367 Brandermill Blvd, Gambrills, MD 21054",
        "phone": "(410) 674-8350",
        "hours": "Mon-Thur 11am-10pm, Fri-Sat 11am-11pm, Sun 11am-9pm"
    },
    "Jersey Mike's Subs": {
        "url": "https://www.jerseymikes.com/menu",
        "instructions": [
            "Place your order directly with Jersey Mike's Subs using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "address": "2637 Brandermill Blvd, Gambrills, MD 21054",
        "phone": "(410) 721-5550",
        "hours": "Daily 10am-9pm"
    },
    "Bruster's Real Ice Cream": {
        "url": "https://brustersonline.com/brusterscom/shoppingcart.aspx?number=415&source=homepage",
        "instructions": [
            "Place your order directly with Bruster's Real Ice Cream using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "address": "1202 Annapolis Rd, Odenton, MD 21113",
        "phone": "(410) 672-0020",
       "hours": "Sun-Thur 12pm-9pm, Fri-Sat 12pm-10pm"
    },
    "Luigino's": {
        "url": "https://order.yourmenu.com/luiginos",
        "instructions": [
            "Place your order directly with Luigino's by using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "address": "2716 Brandermill Blvd, Gambrills, MD 21054",
        "phone": "(410) 451-6010",
        "hours": "Tue-Thur 11am-9pm, Fri-Sat 11am-10pm, Sun 12pm-9pm, Mon Closed"
    },
    "PHO 5UP ODENTON": {
        "url": "https://www.clover.com/online-ordering/pho-5up-odenton",
        "instructions": [
            "Place your order directly with PHO 5UP ODENTON by using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "address": "8777 Piney Orchard Pkwy, Odenton, MD 21113",
        "phone": "(443) 713-1293",
        "hours": "Daily 11am-9pm"
    },
    "Dunkin": {
        "url": "https://www.dunkindonuts.com/en/mobile-app",
        "instructions": [
            "Place your order directly with Dunkin' by using their APP.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "address": "2613 Brandermill Blvd, Gambrills, MD 21054",
        "phone": "(410) 721-2524",
        "hours": "Daily 5am-9pm"
    },
    "Baskin-Robbins": {
        "url": "https://order.baskinrobbins.com/categories?storeId=BR-339568",
        "instructions": [
            "Place your order directly with Baskin-Robbins by using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "address": "2617 Brandermill Blvd, Gambrills, MD 21054",
        "phone": "(410) 721-5661",
        "hours": "Sun-Thur 11am-10pm, Fri-Sat 11am-11pm"
    }
}

# Main application logic
@handle_error
@log_action("main")
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    menu = ["Home", "Menu", "Order", "Butler Bot", "About Us", "Login", "Register"]
    if st.session_state.get('logged_in'):
        menu.append("Logout")
        if st.session_state.get('user_type') == 'Driver':
            menu.append("Driver Dashboard")
        else:
            menu.extend(["Modify Booking", "Cancel Booking"])

    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Home":
        st.subheader("Welcome to Local Butler!")
        st.write("Please navigate through the sidebar to explore our app.")
    elif choice == "Menu":
        display_menu()
    elif choice == "Order":
        if st.session_state['logged_in']:
            display_new_order()
        else:
            st.warning("Please log in to place an order.")
    elif choice == "Butler Bot":
        display_butler_bot()
    elif choice == "About Us":
        display_about_us()
    elif choice == "Login":
        display_login()
    elif choice == "Register":
        display_register()
    elif choice == "Logout":
        logout()
    elif choice == "Driver Dashboard":
        if st.session_state.get('user_type') == 'Driver':
            driver_dashboard()
        else:
            st.warning("Access denied. This page is only for drivers.")
    elif choice == "Modify Booking":
        st.subheader("Modify Booking")
        # Implement modify booking functionality here
    elif choice == "Cancel Booking":
        st.subheader("Cancel Booking")
        # Implement cancel booking functionality here

def display_menu():
    st.subheader("Menu")
    category = st.selectbox("Select a service category:", ("Grocery Services", "Meal Delivery Services"))
    if category == "Grocery Services":
        grocery_store = st.selectbox("Choose a store:", list(GROCERY_STORES.keys()))
        display_service(Service(name=grocery_store, **GROCERY_STORES[grocery_store]))
    elif category == "Meal Delivery Services":
        restaurant = st.selectbox("Choose a restaurant:", list(RESTAURANTS.keys()))
        display_service(Service(name=restaurant, **RESTAURANTS[restaurant]))

@handle_error
@log_action("display_new_order")
def display_new_order():
    st.subheader("Place a New Order")
    
    service_options = ["Grocery Delivery", "Meal Delivery", "Laundry Service"]
    service = st.selectbox("Select a service:", service_options)
    
    # Add dropdown for preferred store/restaurant based on service
    if service == "Grocery Delivery":
        preferred_store = st.selectbox("Preferred grocery store:", list(GROCERY_STORES.keys()))
    elif service == "Meal Delivery":
        preferred_restaurant = st.selectbox("Preferred restaurant:", list(RESTAURANTS.keys()))
    elif service == "Laundry Service":
        laundry_type = st.radio("Service type", ["Wash & Fold", "Dry Cleaning"])
    
    date = st.date_input("Select date")
    time_options = [f"{h:02d}:{m:02d} {'AM' if h < 12 else 'PM'}" for h in range(7, 22) for m in (0, 15, 30, 45)]
    time = st.selectbox("Select time:", time_options)
    
    location = st.text_input("Enter your address")
    if location:
        geolocator = Nominatim(user_agent="local_butler_app")
        try:
            location_data = geolocator.geocode(location)
            if location_data:
                m = folium.Map(location=[location_data.latitude, location_data.longitude], zoom_start=15)
                folium.Marker([location_data.latitude, location_data.longitude]).add_to(m)
                st_folium(m, width=700, height=400)
                full_address = location_data.address
                st.text_input("Verified address (you can edit if needed):", value=full_address, key="verified_address")
            else:
                st.warning("Location not found. Please enter a valid address.")
        except Exception as e:
            st.error(f"Error occurred while geocoding: {str(e)}")
    
    delivery_notes = st.text_area("Delivery Notes (optional)")
    
    if st.button("Review Order"):
        with st.expander("Order Details", expanded=True):
            st.write(f"Service: {service}")
            if service == "Grocery Delivery":
                st.write(f"Preferred Store: {preferred_store}")
            elif service == "Meal Delivery":
                st.write(f"Preferred Restaurant: {preferred_restaurant}")
            elif service == "Laundry Service":
                st.write(f"Service Type: {laundry_type}")
            st.write(f"Date: {date}")
            st.write(f"Time: {time}")
            st.write(f"Address: {st.session_state.get('verified_address', location)}")
            st.write(f"Delivery Notes: {delivery_notes}")
        
        if st.button("Confirm Order"):
            order_id = place_order(st.session_state['user_id'], service, date, datetime.strptime(time.split()[0], "%H:%M").time(), 
                                   st.session_state.get('verified_address', location), delivery_notes)
            if order_id:
                st.success("Order confirmed! Please proceed to place your order with the merchant.")
                
                if service == "Grocery Delivery":
                    merchant_link = GROCERY_STORES[preferred_store]["url"]
                    instructions = GROCERY_STORES[preferred_store]["instructions"]
                elif service == "Meal Delivery":
                    merchant_link = RESTAURANTS[preferred_restaurant]["url"]
                    instructions = RESTAURANTS[preferred_restaurant]["instructions"]
                else:
                    merchant_link = "#"  # Placeholder for laundry service
                    instructions = ["Please follow the laundry service provider's instructions."]
                
                st.markdown(f"[Click here to place your order with the merchant]({merchant_link})")
                st.info("Remember to apply any coupons, rewards, or discount codes directly with the merchant.")
                
                st.subheader("Instructions:")
                for instruction in instructions:
                    st.write(f"- {instruction}")
                
                st.write("After placing your order with the merchant, please return here to complete your Local Butler order.")
                
                order_proof = st.radio("How would you like to confirm your merchant order?", ["Enter Order Number", "Upload Screenshot"])
                if order_proof == "Enter Order Number":
                    order_number = st.text_input("Enter your order number from the merchant:")
                    if st.button("Submit Order Proof"):
                        if order_number:
                            # Here you would update the order in your database with the proof
                            st.success("Order has been successfully placed and verified!")
                            st.info("You will now be redirected to your orders page.")
                            # Here you would implement the redirection to the user's orders page
                        else:
                            st.error("Please provide the order number to complete your order.")
                else:
                    order_screenshot = st.file_uploader("Upload a screenshot of your order:", type=["png", "jpg", "jpeg"])
                    if st.button("Submit Order Proof"):
                        if order_screenshot:
                            # Here you would update the order in your database with the proof
                            st.success("Order has been successfully placed and verified!")
                            st.info("You will now be redirected to your orders page.")
                            # Here you would implement the redirection to the user's orders page
                        else:
                            st.error("Please upload a screenshot to complete your order.")
            else:
                st.error("Unable to place order. The selected time slot may not be available.")

def display_butler_bot():
    st.subheader("Butler Bot")
    iframe_html = """
    <iframe title="Pico embed" src="https://a.picoapps.xyz/shoulder-son?utm_medium=embed&utm_source=embed" width="98%" height="680px" style="background:white"></iframe>
    """
    st.markdown(iframe_html, unsafe_allow_html=True)

def display_about_us():
    st.subheader("About Us")
    st.write("Local Butler is a dedicated concierge service aimed at providing convenience and peace of mind to residents of Fort Meade, Maryland 20755. Our mission is to simplify everyday tasks and errands, allowing our customers to focus on what matters most.")
    st.subheader("How It Works")
    st.write("1. Choose a service category from the menu.")
    st.write("2. Select your desired service.")
    st.write("3. Follow the prompts to complete your order.")
    st.write("4. Sit back and relax while we take care of the rest!")

def display_login():
    if not st.session_state['logged_in']:
        username = st.text_input("Username")
        password = st.text_input("Password", type='password')
        if st.button("Login"):
            success, message, user_type, user_id = authenticate_user(username, password)
            if success:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['user_type'] = user_type
                st.session_state['user_id'] = user_id
                st.success(message)
            else:
                st.error(message)
    else:
        st.warning("You are already logged in.")

@handle_error
@log_action("register")
def display_register():
    st.subheader("Register")
    new_username = st.text_input("Username")
    new_password = st.text_input("Password", type='password')
    confirm_password = st.text_input("Confirm Password", type='password')
    user_type = st.selectbox("User Type", ["Consumer", "Driver", "Merchant", "Partner"])
    
    if st.button("Register"):
        if not new_username or not new_password or not confirm_password:
            st.error("Please fill in all fields.")
        elif new_password != confirm_password:
            st.error("Passwords do not match. Please try again.")
        elif len(new_password) < 8:
            st.error("Password must be at least 8 characters long.")
        else:
            with Session() as session:
                existing_user = session.query(UserModel).filter_by(username=new_username).first()
                if existing_user:
                    st.error("Username already exists. Please choose a different username.")
                else:
                    hashed_password = hash_password(new_password)
                    new_user = UserModel(username=new_username, password=hashed_password, user_type=user_type)
                    session.add(new_user)
                    session.commit()
                    st.success("Registration successful! You can now log in.")

def logout():
    if st.session_state['logged_in']:
        if st.button("Logout"):
            st.session_state['logged_in'] = False
            st.session_state['username'] = ''
            st.session_state['user_type'] = ''
            st.session_state['user_id'] = None
            st.success("Logged out successfully!")
    else:
        st.warning("You are not logged in.")

@handle_error
@log_action("driver_dashboard")
def driver_dashboard():
    st.subheader("Driver Dashboard")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Marketplace", "Current Delivery", "Scheduling", "Earnings"])
    
    with tab1:
        st.subheader("Available Orders")
        with Session() as session:
            orders = session.query(OrderModel).filter_by(status="Pending").all()
            for order in orders:
                with st.expander(f"Order {order.id} - {order.service}"):
                    st.write(f"Date: {order.date}, Time: {order.time}")
                    st.write(f"Location: {order.location}")
                    if st.button(f"Accept Order", key=f"accept_{order.id}"):
                        order.status = "Assigned"
                        order.driver_id = st.session_state['user_id']
                        session.commit()
                        st.success(f"You have accepted order {order.id}")
                        st.experimental_rerun()
    
    with tab2:
        st.subheader("Current Delivery")
        with Session() as session:
            current_order = session.query(OrderModel).filter_by(driver_id=st.session_state['user_id'], status="Assigned").first()
            if current_order:
                st.write(f"Order {current_order.id} - {current_order.service}")
                st.write(f"Date: {current_order.date}, Time: {current_order.time}")
                st.write(f"Location: {current_order.location}")
                if st.button("Complete Delivery"):
                    current_order.status = "Completed"
                    session.commit()
                    st.success(f"Order {current_order.id} marked as completed.")
                    st.experimental_rerun()
            else:
                st.info("No current delivery.")
    
    with tab3:
        st.subheader("Scheduling")
        date = st.date_input("Select date")
        start_time = st.time_input("Start time")
        end_time = st.time_input("End time")
        if st.button("Set Availability"):
            with Session() as session:
                current_time = start_time
                while current_time <= end_time:
                    schedule = ScheduleModel(date=date, time=current_time, available=True)
                    session.add(schedule)
                    current_time = (datetime.combine(date, current_time) + timedelta(minutes=15)).time()
                session.commit()
                st.success("Availability set successfully!")
    
    with tab4:
        st.subheader("Earnings")
        with Session() as session:
            completed_orders = session.query(OrderModel).filter_by(driver_id=st.session_state['user_id'], status="Completed").all()
            total_earnings = len(completed_orders) * st.secrets["driver"]["earnings_per_delivery"]
            st.write(f"Total Earnings: ${total_earnings:.2f}")
            st.write(f"Completed Orders: {len(completed_orders)}")
    
    # Location permission and map
    st.subheader("Your Location")
    if 'location_enabled' not in st.session_state:
        st.session_state['location_enabled'] = False
    
    if st.button("Enable Location"):
        st.session_state['location_enabled'] = True
        st.success("Location enabled. Please refresh the page.")
    
    if st.session_state['location_enabled']:
        geolocator = Nominatim(user_agent="local_butler_app")
        fort_meade = geolocator.geocode("Fort Meade, MD")
        m = folium.Map(location=[fort_meade.latitude, fort_meade.longitude], zoom_start=13)
        st_folium(m, height=400, width=700)
    else:
        st.info("Please enable location to view the map.")

if __name__ == "__main__":
    main()
