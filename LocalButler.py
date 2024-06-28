import streamlit as st
import streamlit.components.v1 as components
import sqlite3
from pathlib import Path
import bcrypt
import os
from functools import wraps
from datetime import datetime, time, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import folium
from streamlit_folium import st_folium
import geopy
from geopy.geocoders import Nominatim

# Set page config at the very beginning
st.set_page_config(page_title="Local Butler")

if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Database setup
DB_FILE = "users.db"
db_path = Path(DB_FILE)

def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, 
                       username TEXT UNIQUE, 
                       password TEXT, 
                       user_type TEXT, 
                       failed_attempts INTEGER DEFAULT 0, 
                       last_attempt TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders 
                      (id INTEGER PRIMARY KEY, 
                       user_id INTEGER, 
                       service TEXT, 
                       date DATE, 
                       time TIME, 
                       location TEXT, 
                       status TEXT, 
                       driver_id INTEGER, 
                       FOREIGN KEY (user_id) REFERENCES users(id), 
                       FOREIGN KEY (driver_id) REFERENCES users(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS schedule 
                      (id INTEGER PRIMARY KEY, 
                       date DATE, 
                       time TIME, 
                       available BOOLEAN)''')
    conn.commit()
    conn.close()

# Call setup_database at the start
setup_database()

# Database functions
def get_db_connection():
    return sqlite3.connect(DB_FILE)

def insert_user(username, password, user_type):
    with get_db_connection() as conn:
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        try:
            conn.execute("INSERT INTO users (username, password, user_type) VALUES (?,?,?)", 
                         (username, hashed_password, user_type))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def authenticate_user(username, password):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, password, user_type, failed_attempts, last_attempt FROM users WHERE username =?", (username,))
        user = cursor.fetchone()
        if user:
            user_id, stored_password, user_type, failed_attempts, last_attempt = user
            if last_attempt:
                last_attempt = datetime.fromisoformat(last_attempt)
                if last_attempt + timedelta(minutes=15) > datetime.now() and failed_attempts >= 5:
                    return False, "Account locked. Try again later.", None, None
            if bcrypt.checkpw(password.encode(), stored_password):
                cursor.execute("UPDATE users SET failed_attempts = 0, last_attempt = NULL WHERE username =?", (username,))
                conn.commit()
                return True, "Login successful", user_type, user_id
            else:
                cursor.execute("UPDATE users SET failed_attempts = failed_attempts + 1, last_attempt =? WHERE username =?", 
                               (datetime.now().isoformat(), username))
                conn.commit()
                return False, "Invalid username or password", None, None
        return False, "Invalid username or password", None, None

# Decorators
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not st.session_state.get('logged_in'):
            st.warning("Please log in to access this feature.")
            return
        return func(*args, **kwargs)
    return wrapper

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
        ]
    },
    "SafeWay": {
        "url": "https://www.safeway.com/",
        "instructions": [
            "Place your order directly with Safeway using your own account to accumulate grocery store points and clip your favorite coupons.",
            "Select store pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "image_url": "https://raw.githubusercontent.com/LocalButler/streamlit_app.py/main/safeway%20app%20ads.png"
    },
    "Commissary": {
        "url": "https://shop.commissaries.com/",
        "instructions": [
            "Place your order directly with the Commissary using your own account.",
            "Select store pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "image_url": "https://raw.githubusercontent.com/LocalButler/streamlit_app.py/main/comissaries.jpg"
    },
    "Food Lion": {
        "url": "https://shop.foodlion.com/?shopping_context=pickup&store=2517",
        "instructions": [
            "Place your order directly with Food Lion using your own account.",
            "Select store pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ],
        "image_url": "https://raw.githubusercontent.com/LocalButler/streamlit_app.py/main/foodlionhomedelivery.jpg"
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
        "image_url": "https://raw.githubusercontent.com/LocalButler/streamlit_app.py/main/TheHideAway.jpg"
    },
    "Ruth's Chris Steak House": {
        "url": "https://order.ruthschris.com/",
        "instructions": [
            "Place your order directly with Ruth's Chris Steak House using their website or app.",
            "Select pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    "Baltimore Coffee & Tea Company": {
        "url": "https://www.baltcoffee.com/sites/default/files/pdf/2023WebMenu_1.pdf",
        "instructions": [
            "Review the menu and decide on your order.",
            "Call Baltimore Coffee & Tea Company to place your order.",
            "Specify that you'll be using Local Butler for pick-up and delivery.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!",
            "We apologize for any inconvenience, but Baltimore Coffee & Tea Company does not currently offer online ordering."
        ]
    },
    "The All American Steakhouse": {
        "url": "https://order.theallamericansteakhouse.com/menu/odenton",
        "instructions": [
            "Place your order directly with The All American Steakhouse by using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    "Jersey Mike's Subs": {
        "url": "https://www.jerseymikes.com/menu",
        "instructions": [
            "Place your order directly with Jersey Mike's Subs using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    "Bruster's Real Ice Cream": {
        "url": "https://brustersonline.com/brusterscom/shoppingcart.aspx?number=415&source=homepage",
        "instructions": [
            "Place your order directly with Bruster's Real Ice Cream using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    "Luigino's": {
        "url": "https://order.yourmenu.com/luiginos",
        "instructions": [
            "Place your order directly with Luigino's by using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    "PHO 5UP ODENTON": {
        "url": "https://www.clover.com/online-ordering/pho-5up-odenton",
        "instructions": [
            "Place your order directly with PHO 5UP ODENTON by using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    "Dunkin": {
        "url": "https://www.dunkindonuts.com/en/mobile-app",
        "instructions": [
            "Place your order directly with Dunkin' by using their APP.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    "Baskin-Robbins": {
        "url": "https://order.baskinrobbins.com/categories?storeId=BR-339568",
        "instructions": [
            "Place your order directly with Baskin-Robbins by using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    }
}

# Service display functions
@login_required
def display_grocery_services():
    st.write("Order fresh groceries from your favorite local stores and have them delivered straight to your doorstep.")
    video_url = "https://raw.githubusercontent.com/LocalButler/streamlit_app.py/119398d25abc62218ccaec71f44b30478d96485f/Local%20Butler%20Groceries.mp4"
    video_html = f"""
        <video controls width="100%">
            <source src="{video_url}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
    """
    st.components.v1.html(video_html, height=300)
    
    for store, details in GROCERY_STORES.items():
        st.subheader(store)
        st.write(f"[Order from {store}]({details['url']})")
        for instruction in details['instructions']:
            st.write(f"- {instruction}")
        if 'video_url' in details:
            st.video(details['video_url'])
        if 'image_url' in details:
            st.image(details['image_url'])

@login_required
def display_restaurant_services():
    st.write("Order delicious meals from your favorite local restaurants and have them delivered hot and fresh to your doorstep.")
    for restaurant, details in RESTAURANTS.items():
        st.subheader(restaurant)
        st.write(f"[Order from {restaurant}]({details['url']})")
        for instruction in details['instructions']:
            st.write(f"- {instruction}")
        if 'image_url' in details:
            st.image(details['image_url'])

@login_required
def display_laundry_services():
    st.write("Let us take care of your laundry needs. We'll pick up, wash, fold, and deliver your clothes back to you.")
    st.write("Our laundry service costs $1.50 per pound.")
    st.write("Benefits of using our laundry services:")
    st.write("- Save on utilities: No need to worry about water, electricity, or gas costs.")
    st.write("- No detergent costs: We provide all necessary cleaning agents.")
    st.write("- Time-saving: Let us handle your laundry while you focus on other tasks.")
    st.write("To use our laundry service, simply let us know how many bags of laundry you have and their approximate sizes.")

@login_required
def display_pet_care_services():
    st.write("We offer a range of pet care services to keep your furry friends happy and healthy.")
    st.write("Our services include:")
    st.write("- Dog walking")
    st.write("- Pet sitting")
    st.write("- Grooming")
    st.write("Let us know what type of pet care service you need, and we'll connect you with trusted professionals in your area.")

@login_required
def display_car_wash_services():
    st.write("Keep your vehicle looking its best with our car wash services.")
    st.write("We offer:")
    st.write("- Quick wash")
    st.write("- Detailed cleaning")
    st.write("- Interior cleaning")
    st.write("Let us know what type of car wash service you need, and we'll schedule it for you.")

def login():
    st.subheader("Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type='password', key="login_password")
    if st.button("Login", key="login_button"):
        success, message, user_type, user_id = authenticate_user(username, password)
        if success:
            st.session_state['logged_in'] = True
            st.session_state['user_id'] = user_id
            st.session_state['username'] = username
            st.session_state['user_type'] = user_type
            st.success(message)
        else:
            st.error(message)

def register():
    st.subheader("Register")
    new_username = st.text_input("Username", key="register_username")
    new_password = st.text_input("Password", type='password', key="register_password")
    confirm_password = st.text_input("Confirm Password", type='password', key="register_confirm_password")
    user_type = st.selectbox("User Type", ["Consumer", "Driver", "Merchant", "Partner"], key="register_user_type")
    if st.button("Register", key="register_button"):
        if not new_username or not new_password or not confirm_password:
            st.error("Please fill in all fields.")
        elif new_password != confirm_password:
            st.error("Passwords do not match. Please try again.")
        elif len(new_password) < 8:
            st.error("Password must be at least 8 characters long.")
        else:
            if insert_user(new_username, new_password, user_type):
                st.success("Registration successful! You can now log in.")
            else:
                st.error("Username already exists. Please choose a different username.")

def chatbot():
    st.subheader("Chat with Butler Bot")
    user_input = st.text_input("You:", key="chatbot_input")
    if st.button("Send", key="chatbot_send"):
        if user_input.lower() == "hello":
            st.write("Butler Bot: Hello there! My name is Butler Bot, and I'm here to assist you with anything you need from Local Butler. How can I be of service to you today?")
        elif "laundry" in user_input.lower() and "price" in user_input.lower():
            st.write("Butler Bot: Hello there! I'm delighted to assist you with our laundry services. The cost for our laundry services is $1.50 per pound. We understand that laundry needs may vary, so we offer this per-pound rate to ensure you only pay for the exact amount of laundry you need cleaned. This price includes the pickup, washing, drying, folding, and delivery of your clothes.")
        elif "order" in user_input.lower() and "myself" in user_input.lower():
            st.write("Butler Bot: That's a great idea! Here's how it works: you'll provide me with the list of ingredients you need, and I'll help you find the best options available for purchase. Once you have the list ready, you can place the order yourself through your preferred grocery store's website or app. After you've placed the order and obtained the order number, simply share it with me, and I'll take care of the pickup and delivery process.")
        else:
            st.write("Butler Bot: I'm here to help! Could you please provide more details about what you need assistance with?")

def main():
    st.title("Welcome to Local Butler")
    
    if not st.session_state['logged_in']:
        login()
        register()
    else:
        st.write(f"Welcome back, {st.session_state['username']}!")
        service = st.selectbox("Select a service", 
                               ["Grocery Delivery", "Restaurant Delivery", "Laundry Services", "Pet Care", "Car Wash", "Chat with Butler Bot"],
                               key="service_selector")
        
        if service == "Grocery Delivery":
            display_grocery_services()
        elif service == "Restaurant Delivery":
            display_restaurant_services()
        elif service == "Laundry Services":
            display_laundry_services()
        elif service == "Pet Care":
            display_pet_care_services()
        elif service == "Car Wash":
            display_car_wash_services()
        elif service == "Chat with Butler Bot":
            chatbot()

if __name__ == "__main__":
    main()
