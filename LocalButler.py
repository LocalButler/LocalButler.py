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
        <div style="position: relative; width: 100%; height: 0; padding-bottom: 56.25%;">
            <video autoplay loop muted playsinline
                style="position: absolute; top: -25%; left: 0; width: 100%; height: 125%;"
                frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">
                <source src="{video_url}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            <div style="position: absolute; top: -5%; left: 0; width: 100%; height: 92%; background-color: black; opacity: 0.3;"></div>
        </div>
    """
    components.html(video_html, height=315)

    grocery_store = st.selectbox("Choose a store:", list(GROCERY_STORES.keys()))
    store_info = GROCERY_STORES[grocery_store]
    st.write(f"ORDER NOW: [{grocery_store}]({store_info['url']})")
    
    if "video_url" in store_info:
        st.markdown(f"### {store_info['video_title']}")
        store_video_html = f"""
            <div style="position: relative; width: 100%; height: 0; padding-bottom: 56.25%;">
                <video autoplay playsinline controls
                    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
                    frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">
                    <source src="{store_info['video_url']}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </div>
        """
        components.html(store_video_html, height=315)
    elif "image_url" in store_info:
        st.image(store_info['image_url'], caption=f"{grocery_store} App", use_column_width=True)
    
    st.write("Instructions for placing your order:")
    for instruction in store_info["instructions"]:
        st.write(f"- {instruction}")

@login_required
def display_meal_delivery_services():
    st.write("Enjoy delicious meals from top restaurants in your area delivered to your home or office.")
    restaurant = st.selectbox("Choose a restaurant:", list(RESTAURANTS.keys()))
    restaurant_info = RESTAURANTS[restaurant]
    st.write(f"ORDER NOW: [{restaurant}]({restaurant_info['url']})")
    st.write("Instructions for placing your order:")
    for instruction in restaurant_info["instructions"]:
        st.write(f"- {instruction}")

def display_about_us():
    st.write("Local Butler is a dedicated concierge service aimed at providing convenience and peace of mind to residents of Fort Meade, Maryland 20755. Our mission is to simplify everyday tasks and errands, allowing our customers to focus on what matters most.")

def display_how_it_works():
    st.write("1. Choose a service category from the menu.")
    st.write("2. Select your desired service.")
    st.write("3. Follow the prompts to complete your order.")
    st.write("4. Sit back and relax while we take care of the rest!")

def generate_time_slots():
    start = datetime.combine(datetime.today(), time(7, 0))  # 7 AM
    end = datetime.combine(datetime.today(), time(21, 0))  # 9 PM
    time_slots = []
    while start <= end:
        time_slots.append(start.strftime("%I:%M %p"))
        start += timedelta(minutes=15)
    return time_slots

@login_required
def display_new_order():
    st.subheader("Place a New Order")
    
    service = st.selectbox("Select a service:", ["Grocery Pickup", "Meal Delivery"])
    date = st.date_input("Select a date:")
    
    # Replace the original time input with a custom time slot selector
    time_slots = generate_time_slots()
    selected_time = st.selectbox("Select a time:", time_slots)
    
    location = st.text_input("Enter your location:")
    
    if location:
        geolocator = Nominatim(user_agent="local_butler_app")
        try:
            location_data = geolocator.geocode(location)
            if location_data:
                m = folium.Map(location=[location_data.latitude, location_data.longitude], zoom_start=15)
                folium.Marker([location_data.latitude, location_data.longitude]).add_to(m)
                st_folium(m, width=700, height=400)
            else:
                st.warning("Location not found. Please enter a valid address.")
        except Exception as e:
            st.error(f"Error occurred while geocoding: {str(e)}")
    
    if st.button("Place Order"):
        if not service or not date or not selected_time or not location:
            st.error("Please fill in all fields.")
        else:
            # Convert selected_time string back to time object
            time_obj = datetime.strptime(selected_time, "%I:%M %p").time()
            order_id = place_order(st.session_state['user_id'], service, date, time_obj, location)
            if order_id:
                st.success(f"Order placed successfully! Your order ID is {order_id}")
                send_email("New Order Placed", f"A new order (ID: {order_id}) has been placed for {service} on {date} at {selected_time} to be delivered to {location}.")
            else:
                st.error("Unable to place order. The selected time slot may not be available.")

    st.write("---")
    st.subheader("Your Orders")
    
    # Fetch and display user's orders
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("SELECT id, service, date, time, location, status FROM orders WHERE user_id = ? ORDER BY date DESC, time DESC", (st.session_state['user_id'],))
orders = cursor.fetchall()
conn.close()

if orders:
    for order in orders:
        order_id, service, date, time_str, location, status = order
        time_obj = datetime.strptime(time_str, '%H:%M:%S').time()  # Convert time string to time object
        with st.expander(f"Order {order_id} - {service} ({status})"):
            st.write(f"Date: {date}, Time: {time_obj.strftime('%I:%M %p')}")
            st.write(f"Location: {location}")
            st.write(f"Status: {status}")
else:
    st.info("You have no orders yet.")

@login_required
def modify_booking():
    st.subheader("Modify Booking")
    # Here you would typically fetch existing bookings from your database
    # For this example, we'll use a dummy booking
    existing_booking = {
        "date": "2024-07-01",
        "time": "14:00",
        "service": "Grocery Pickup"
    }
    
    st.write(f"Current booking: {existing_booking['date']} at {existing_booking['time']} for {existing_booking['service']}")
    
    new_date = st.date_input("New date", datetime.strptime(existing_booking['date'], '%Y-%m-%d'))
    new_time = st.time_input("New time", datetime.strptime(existing_booking['time'], '%H:%M').time())
    new_service = st.selectbox("New service", ["Grocery Pickup", "Meal Delivery"], index=0 if existing_booking['service'] == "Grocery Pickup" else 1)
    
    if st.button("Confirm Modification"):
        # Here you would update the booking in your database
        st.success("Booking modified successfully!")
        send_email("Booking Modified", f"Your booking has been modified to {new_date} at {new_time} for {new_service}")

@login_required
def cancel_booking():
    st.subheader("Cancel Booking")
    # Again, you would typically fetch existing bookings from your database
    existing_booking = {
        "date": "2024-07-01",
        "time": "14:00",
        "service": "Grocery Pickup"
    }
    
    st.write(f"Current booking: {existing_booking['date']} at {existing_booking['time']} for {existing_booking['service']}")
    
    if st.button("Cancel Booking"):
        # Here you would remove the booking from your database
        st.success("Booking cancelled successfully!")
        send_email("Booking Cancelled", f"Your booking for {existing_booking['date']} at {existing_booking['time']} for {existing_booking['service']} has been cancelled.")

def check_time_slot_available(date, time):
    conn = get_db_connection()
    cursor = conn.cursor()
    time_str = time.strftime('%H:%M:%S')  # Convert time to string
    cursor.execute("SELECT available FROM schedule WHERE date = ? AND time = ?", (date, time_str))
    result = cursor.fetchone()
    conn.close()
    return result and result[0]

def update_time_slot(date, time, available):
    if isinstance(time, datetime.time):
        time = time.strftime('%H:%M:%S')  # Convert time to string if it's a time object
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO schedule (date, time, available) VALUES (?, ?, ?)", 
                   (date, time, available))
    conn.commit()
    conn.close()
def place_order(user_id, service, date, time, location):
    time_str = time.strftime('%H:%M:%S')  # Convert time to string
    if check_time_slot_available(date, time_str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO orders (user_id, service, date, time, location, status) VALUES (?, ?, ?, ?, ?, ?)",
                       (user_id, service, date, time_str, location, "Pending"))
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        update_time_slot(date, time_str, False)
        return order_id
    else:
        return None

def get_available_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, service, date, time, location FROM orders WHERE status = 'Pending' ORDER BY date, time")
    orders = cursor.fetchall()
    conn.close()
    return orders

def assign_order_to_driver(order_id, driver_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = 'Assigned', driver_id = ? WHERE id = ?", (driver_id, order_id))
    conn.commit()
    conn.close()

def driver_dashboard():
    st.subheader("Driver Dashboard")
    
    # Add a sign out button in the sidebar
    if st.sidebar.button("Sign Out"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''
        st.session_state['user_type'] = ''
        st.session_state['user_id'] = None
        st.experimental_rerun()
    
    tab1, tab2, tab3, tab4 = st.tabs(["Marketplace", "Current Delivery", "Scheduling", "Earnings"])
    
    with tab1:
        st.subheader("Available Orders")
        orders = get_available_orders()
        for order in orders:
            order_id, service, date, time, location = order
            with st.expander(f"Order {order_id} - {service}"):
                st.write(f"Date: {date}, Time: {time}")
                st.write(f"Location: {location}")
                if st.button(f"Accept Order", key=f"accept_{order_id}"):
                    assign_order_to_driver(order_id, st.session_state['user_id'])
                    st.success(f"You have accepted order {order_id}")
                    st.experimental_rerun()
    
    with tab2:
        st.subheader("Current Delivery")
        st.info("No current delivery.")  # Placeholder, implement actual logic later
    
    with tab3:
        st.subheader("Scheduling")
        date = st.date_input("Select date")
        start_time = st.time_input("Start time")
        end_time = st.time_input("End time")
        if st.button("Set Availability"):
            st.success("Availability set successfully!")  # Placeholder, implement actual logic later
    
    with tab4:
        st.subheader("Earnings")
        st.write("Total Earnings: $0.00")  # Placeholder, implement actual logic later
    
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
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'username' not in st.session_state:
        st.session_state['username'] = ''
    if 'user_type' not in st.session_state:
        st.session_state['user_type'] = ''
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None

    if st.session_state['logged_in'] and st.session_state['user_type'] == 'Driver':
        driver_dashboard()
    else:
        # Your existing code for other user types
        menu = ["Home", "Menu", "Order", "Butler Bot", "About Us", "Login"]
        if st.session_state['logged_in']:
            menu.append("Logout")
            if user_has_orders(st.session_state['username']):
                menu.extend(["Modify Booking", "Cancel Booking"])
        else:
            menu.append("Register")

        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Home":
            st.subheader("Welcome to Local Butler!")
            st.write("Please navigate through the sidebar to explore our app.")
        elif choice == "Menu":
            st.subheader("Menu")
            with st.expander("Service Categories", expanded=False):
                category = st.selectbox("Select a service category:", ("Grocery Services", "Meal Delivery Services"))
                if category == "Grocery Services":
                    display_grocery_services()
                elif category == "Meal Delivery Services":
                    display_meal_delivery_services()
        elif choice == "Order":
            if st.session_state['logged_in']:
                display_new_order()
            else:
                st.warning("Please log in to place an order.")
        elif choice == "Butler Bot":
            st.subheader("Butler Bot")
            iframe_html = """
            <iframe title="Pico embed" src="https://a.picoapps.xyz/shoulder-son?utm_medium=embed&utm_source=embed" width="98%" height="680px" style="background:white"></iframe>
            """
            components.html(iframe_html, height=680)
        elif choice == "About Us":
            st.subheader("About Us")
            display_about_us()
            display_how_it_works()
        elif choice == "Login":
    if not st.session_state['logged_in']:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type='password', key="login_password")
        if st.button("Login"):
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                success, message, user_type, user_id = authenticate_user(username, password)
                if success:
                    user_id = get_user_id_from_database(username)  # This line should be indented correctly
                    st.session_state['user_id'] = user_id
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.session_state['user_type'] = user_type
                    st.session_state['user_id'] = user_id
                    st.success(message)
                    st.experimental_rerun()
                else:
                    st.error(message)
        else:
            st.warning("You are already logged in.")

        elif choice == "Logout":
            if st.session_state['logged_in']:
                if st.button("Logout"):
                    st.session_state['logged_in'] = False
                    st.session_state['username'] = ''
                    st.session_state['user_type'] = ''
                    st.session_state['user_id'] = None
                    st.success("Logged out successfully!")
                    st.experimental_rerun()
            else:
                st.warning("You are not logged in.")
        elif choice == "Register":
            register()
        elif choice == "Modify Booking":
            modify_booking()
        elif choice == "Cancel Booking":
            cancel_booking()

def user_has_orders(username):
    # Implement this function to check if the user has any existing orders
    # For now, we'll return True for demonstration purposes
    return True

if __name__ == "__main__":
    main()
