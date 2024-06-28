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
            conn.execute("INSERT INTO users (username, password, user_type) VALUES (?, ?, ?)", 
                         (username, hashed_password, user_type))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def register():
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
            if insert_user(new_username, new_password, user_type):
                st.success("Registration successful! You can now log in.")
            else:
                st.error("Username already exists. Please choose a different username.")

def authenticate_user(username, password):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, password, user_type, failed_attempts, last_attempt FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user:
            user_id, stored_password, user_type, failed_attempts, last_attempt = user
            if last_attempt:
                last_attempt = datetime.fromisoformat(last_attempt)
                if last_attempt + timedelta(minutes=15) > datetime.now() and failed_attempts >= 5:
                    return False, "Account locked. Try again later.", None, None
            
            if bcrypt.checkpw(password.encode(), stored_password):
                cursor.execute("UPDATE users SET failed_attempts = 0, last_attempt = NULL WHERE username = ?", (username,))
                conn.commit()
                return True, "Login successful", user_type, user_id
            else:
                cursor.execute("UPDATE users SET failed_attempts = failed_attempts + 1, last_attempt = ? WHERE username = ?", 
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
        "url": "https://brusters.com/menu/",
        "instructions": [
            "Place your order directly with Bruster's Real Ice Cream using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    }
}

NON_PRESCRIPTION_ITEMS = {
    "CVS": {
        "url": "https://www.cvs.com/",
        "instructions": [
            "Place your order directly with CVS using their website or app.",
            "Select store pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    "Walgreens": {
        "url": "https://www.walgreens.com/",
        "instructions": [
            "Place your order directly with Walgreens using their website or app.",
            "Select store pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    "Walmart": {
        "url": "https://www.walmart.com/",
        "instructions": [
            "Place your order directly with Walmart using their website or app.",
            "Select store pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    "Target": {
        "url": "https://www.target.com/",
        "instructions": [
            "Place your order directly with Target using their website or app.",
            "Select store pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    }
}

# Email function
def send_email(to, subject, body):
    email = "your-email@gmail.com"
    password = "your-password"

    message = MIMEMultipart()
    message["From"] = email
    message["To"] = to
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(email, password)
        server.sendmail(email, to, message.as_string())

# Logging in
def login():
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type='password')
    if st.button("Login"):
        success, message, user_type, user_id = authenticate_user(username, password)
        if success:
            st.session_state['logged_in'] = True
            st.session_state['user_type'] = user_type
            st.session_state['user_id'] = user_id
            st.success(message)
            st.experimental_rerun()
        else:
            st.error(message)

def logout():
    st.session_state['logged_in'] = False
    st.session_state['user_type'] = None
    st.session_state['user_id'] = None
    st.success("Logged out successfully.")
    st.experimental_rerun()

# Main app
def main():
    st.title("Local Butler")

    if st.session_state['logged_in']:
        st.sidebar.write(f"Logged in as: {st.session_state['user_type']}")
        if st.sidebar.button("Logout"):
            logout()
    else:
        login()
        if st.button("Register Here"):
            register()
        return

    if st.session_state['user_type'] == 'Consumer':
        st.header("Welcome to Local Butler's Consumer Dashboard")
        st.subheader("Order Services")

        service = st.selectbox("Select Service", ["Grocery Delivery", "Food Delivery", "Non-Prescription Pharmacy Items Delivery"])

        if service == "Grocery Delivery":
            st.write("Available Stores:")
            for store, details in GROCERY_STORES.items():
                st.write(f"### [{store}]({details['url']})")
                if 'video_url' in details:
                    st.video(details['video_url'], format='mp4')
                    st.write(details['video_title'])
                if 'image_url' in details:
                    st.image(details['image_url'])
                st.write("Instructions:")
                for instruction in details['instructions']:
                    st.write(f"- {instruction}")

        elif service == "Food Delivery":
            st.write("Available Restaurants:")
            for restaurant, details in RESTAURANTS.items():
                st.write(f"### [{restaurant}]({details['url']})")
                if 'image_url' in details:
                    st.image(details['image_url'])
                st.write("Instructions:")
                for instruction in details['instructions']:
                    st.write(f"- {instruction}")

        elif service == "Non-Prescription Pharmacy Items Delivery":
            st.write("Available Stores:")
            for store, details in NON_PRESCRIPTION_ITEMS.items():
                st.write(f"### [{store}]({details['url']})")
                st.write("Instructions:")
                for instruction in details['instructions']:
                    st.write(f"- {instruction}")

    elif st.session_state['user_type'] == 'Driver':
        st.header("Welcome to Local Butler's Driver Dashboard")
        st.write("Your assigned orders will be displayed here.")

    elif st.session_state['user_type'] == 'Merchant':
        st.header("Welcome to Local Butler's Merchant Dashboard")
        st.write("You can manage your store's orders and availability here.")

    elif st.session_state['user_type'] == 'Partner':
        st.header("Welcome to Local Butler's Partner Dashboard")
        st.write("You can manage your partnership details here.")

if __name__ == "__main__":
    main()
