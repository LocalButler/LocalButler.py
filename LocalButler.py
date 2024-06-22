import streamlit as st
import streamlit.components.v1 as components
import sqlite3
from pathlib import Path
import hashlib
import os

# Database setup
DB_FILE = "users.db"
db_path = Path(DB_FILE)
if not db_path.exists():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Database functions
def get_db_connection():
    """
    Get a connection to the SQLite database.
    Returns:
        Connection object or None
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except sqlite3.Error as e:
        st.error(f"Error connecting to the database: {e}")
        return None

def insert_user(username, password):
    """
    Insert a new user into the database.
    Args:
        username (str): The username of the new user.
        password (str): The password of the new user.
    Returns:
        True if the user was inserted successfully, False otherwise.
    """
    conn = get_db_connection()
    if conn is None:
        return False

    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Error inserting user: {e}")
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    """
    Authenticate a user by checking their username and password against the database.
    Args:
        username (str): The username of the user.
        password (str): The password of the user.
    Returns:
        True if the user is authenticated, False otherwise.
    """
    conn = get_db_connection()
    if conn is None:
        return False

    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_password))
        user = cursor.fetchone()
        return user is not None
    except sqlite3.Error as e:
        st.error(f"Error authenticating user: {e}")
        return False
    finally:
        conn.close()

# Service data
GROCERY_STORES = {
    "Weis Markets": {
        "url": "https://www.weismarkets.com/",
        "video_url": "https://raw.githubusercontent.com/LocalButler/streamlit_app.py/1ff75ee91b2717fabadb44ee645612d6e48e8ee3/Weis%20Promo%20Online%20ordering%20%E2%80%90.mp4",
        "video_title": "Watch this video to learn how to order from Weis Markets:",
        "instructions": [
            "Place your order directly with Weis Markets using your own account to accumulate grocery store points and clip your favorite coupons.",
            "Select store pick-up and specify the date and time.",
            "Let your assigned butler know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    "SafeWay": {
        "url": "https://www.safeway.com/",
        "instructions": [
            "Place your order directly with Safeway using your own account to accumulate grocery store points and clip your favorite coupons.",
            "Select store pick-up and specify the date and time.",
            "Let your assigned butler know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    "Commissary": {
        "url": "https://shop.commissaries.com/",
        "instructions": [
            "Place your order directly with the Commissary using your own account.",
            "Select store pick-up and specify the date and time.",
            "Let your assigned butler know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    "Food Lion": {
        "url": "https://shop.foodlion.com/?shopping_context=pickup&store=2517",
        "instructions": [
            "Place your order directly with Food Lion using your own account.",
            "Select store pick-up and specify the date and time.",
            "Let your assigned butler know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    }
}

RESTAURANTS = {
    "The Hideaway": {
        "url": "https://order.toasttab.com/online/hideawayodenton",
        "instructions": [
            "Place your order directly with The Hideaway using their website or app.",
            "Select pick-up and specify the date and time.",
            "Let your assigned butler know you've placed an order, and we'll take care of the rest!"
        ]
    },
    "Ruth's Chris Steak House": {
        "url": "https://order.ruthschris.com/",
        "instructions": [
            "Place your order directly with Ruth's Chris Steak House using their website or app.",
            "Select pick-up and specify the date and time.","Let your assigned butler know you've placed an order, and we'll take care of the rest!"
        ]
    },
    "Baltimore Coffee & Tea Company": {
        "url": "https://www.baltcoffee.com/sites/default/files/pdf/2023WebMenu_1.pdf",
        "instructions": [
            "Review the menu and decide on your order.",
            "Call Baltimore Coffee & Tea Company to place your order.",
            "Specify that you'll be using Local Butler for pick-up and delivery.",
            "Let your assigned butler know the order you've placed, and we'll take care of the rest!",
            "We apologize for any inconvenience, but Baltimore Coffee & Tea Company does not currently offer online ordering."
        ]
    },
    "The All American Steakhouse": {
        "url": "https://order.theallamericansteakhouse.com/menu/odenton",
        "instructions": [
            "Place your order directly with The All American Steakhouse by using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let your assigned butler know you've placed an order, and we'll take care of the rest!"
        ]
    },
    "Jersey Mike's Subs": {
        "url": "https://www.jerseymikes.com/menu",
        "instructions": [
            "Place your order directly with Jersey Mike's Subs using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let your assigned butler know you've placed an order, and we'll take care of the rest!"
        ]
    },
    "Bruster's Real Ice Cream": {
        "url": "https://brustersonline.com/brusterscom/shoppingcart.aspx?number=415&source=homepage",
        "instructions": [
            "Place your order directly with Bruster's Real Ice Cream using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let your assigned butler know you've placed an order, and we'll take care of the rest!"
        ]
    },
    "Luigino's": {
        "url": "https://order.yourmenu.com/luiginos",
        "instructions": [
            "Place your order directly with Luigino's by using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let your assigned butler know you've placed an order, and we'll take care of the rest!"
        ]
    },
    "PHO 5UP ODENTON": {
        "url": "https://www.clover.com/online-ordering/pho-5up-odenton",
        "instructions": [
            "Place your order directly with PHO 5UP ODENTON by using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let your assigned butler know you've placed an order, and we'll take care of the rest!"
        ]
    },
    "Dunkin": {
        "url": "https://www.dunkindonuts.com/en/mobile-app",
        "instructions": [
            "Place your order directly with Dunkin' by using their APP.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let your assigned butler know you've placed an order, and we'll take care of the rest!"
        ]
    },
    "Baskin-Robbins": {
        "url": "https://order.baskinrobbins.com/categories?storeId=BR-339568",
        "instructions": [
            "Place your order directly with Baskin-Robbins by using their website or app.",
            "Specify the items you want to order and the pick-up date and time.",
            "Let your assigned butler know you've placed an order, and we'll take care of the rest!"
        ]
    }
}

HOUSE_CLEANING_SERVICES = {
    "Professional House Cleaning": {
        "url": "https://www.example.com/house-cleaning",
        "instructions": [
            "Visit our website and fill out the online form to schedule a professional house cleaning service.",
            "Provide details about your home, including the number of rooms, bathrooms, and any specific cleaning requirements.",
            "Select a convenient date and time for the cleaning service.",
            "Our team of professional cleaners will arrive at your home at the scheduled time and ensure a thorough cleaning."
        ]
    }
}

# Service display functions
def display_grocery_services():
    st.write("Order fresh groceries from your favorite local stores and have them delivered straight to your doorstep.")
    
    # Use the GitHub raw video link
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

    st.write("Select a grocery store:")
    grocery_store = st.selectbox("Choose a store:", list(GROCERY_STORES.keys()))
    store_info = GROCERY_STORES[grocery_store]
    st.write(f"You selected: [{grocery_store}]({store_info['url']})")
    
    # Display store-specific video if available (using the same HTML5 video structure)
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
    
    st.write("Instructions for placing your order:")
    for instruction in store_info["instructions"]:
        st.write(f"- {instruction}")

def display_meal_delivery_services():
    st.write("Enjoy delicious meals from top restaurants in your area delivered to your home or office.")
    st.write("Select a restaurant:")
    restaurant = st.selectbox("Choose a restaurant:", list(RESTAURANTS.keys()))
    restaurant_info = RESTAURANTS[restaurant]
    st.write(f"You selected: [{restaurant}]({restaurant_info['url']})")
    st.write("Instructions for placing your order:")
    for instruction in restaurant_info["instructions"]:
        st.write(f"- {instruction}")

def display_laundry_services():
    st.write("Schedule laundry pickup and delivery services, ensuring your clothes are clean and fresh with minimal effort.")
    # Add any additional instructions or options for laundry services

def display_errand_services():
    st.write("Get help with various errands such as shopping, mailing packages, or picking up prescriptions.")
    # Add any additional instructions or options for errand services

def display_pharmacy_services():
    st.write("Order prescription medications and over-the-counter products from local pharmacies with convenient delivery options.")
    # Add any additional instructions or options for pharmacy services

def display_pet_care_services():
    st.write("Ensure your furry friends receive the care they deserve with pet sitting, grooming, and walking services.")
    # Add any additional instructions or options for pet care services

def display_car_wash_services():
    st.write("Schedule car wash and detailing services to keep your vehicle clean and looking its best.")
    # Add any additional instructions or options for car wash services

def display_house_cleaning_services():
    st.write("Keep your home clean and tidy with our professional house cleaning services.")
    service = st.selectbox("Choose a house cleaning service:", list(HOUSE_CLEANING_SERVICES.keys()))
    service_info = HOUSE_CLEANING_SERVICES[service]
    st.write(f"You selected: [{service}]({service_info['url']})")
    st.write("Instructions for scheduling your service:")
    for instruction in service_info["instructions"]:
        st.write(f"- {instruction}")

def display_about_us():
    st.write("Local Butler is a dedicated concierge service aimed at providing convenience and peace of mind to residents of Fort Meade, Maryland 20755. Our mission is to simplify everyday tasks and errands, allowing our customers to focus on what matters most.")

def display_how_it_works():
    st.write("1. Choose a service category from the menu.")
    st.write("2. Select your desired service.")
    st.write("3. Follow the prompts to complete your order.")
    st.write("4. Sit back and relax while we take care of the rest!")

def display_new_order():
    iframe_html = """
    <iframe title="Pico embed" src="https://a.picoapps.xyz/shoulder-son?utm_medium=embed&utm_source=embed" width="98%" height="680px" style="background:white"></iframe>
    """
    components.html(iframe_html, height=680)

def display_calendar():
    iframe_html = """
    <iframe title="Calendar" src="https://localbutler.durablesites.com/book-now?pt=NjY2ODQ3Mjk2OTI2NTgzMjJmNGMwNDA5OjE3MTgxMTU0MDYuMjk3OnByZXZpZXc=" width="100%" height="680px" style="background:white"></iframe>
    """
    components.html(iframe_html, height=680)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''

def main():
    st.set_page_config(page_title="Local Butler")

    # ... (existing title and logo code)

    menu = ["Home", "Menu", "Order", "Butler Bot", "Calendar", "About Us", "Login"]
    if st.session_state['logged_in']:
        menu.append("Logout")
    else:
        menu.append("Register")

    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Home":
        st.subheader("Welcome to Local Butler!")
        st.write("Please navigate through the sidebar to explore our app.")

    elif choice == "Menu":
        st.subheader("Menu")
        with st.expander("Service Categories", expanded=False):
            category = st.selectbox("Select a service category:", ("Grocery Services", "Meal Delivery Services", "Laundry Services", "Errand Services", "Pharmacy Services", "Pet Care Services", "Car Wash Services", "House Cleaning Services"))
            if category == "Grocery Services":
                display_grocery_services()
            elif category == "Meal Delivery Services":
                display_meal_delivery_services()
            elif category == "Laundry Services":
                display_laundry_services()
            elif category == "Errand Services":
                display_errand_services()
            elif category == "Pharmacy Services":
                display_pharmacy_services()
            elif category == "Pet Care Services":
                display_pet_care_services()
            elif category == "Car Wash Services":
                display_car_wash_services()
            elif category == "House Cleaning Services":
                display_house_cleaning_services()

    elif choice == "Order":
        if st.session_state['logged_in']:
            st.subheader("Order")
            # Add order placement functionality here
        else:
            st.warning("Please log in to place an order.")

    elif choice == "Butler Bot":
        st.subheader("Butler Bot")
        display_new_order()

    elif choice == "Calendar":
        st.subheader("Calendar")
        display_calendar()

    elif choice == "About Us":
        st.subheader("About Us")
        display_about_us()
        display_how_it_works()

    elif choice == "Login":
        if not st.session_state['logged_in']:
            username = st.text_input("Username")
            password = st.text_input("Password", type='password')
            if st.button("Login"):
                if not username or not password:
                    st.error("Please enter both username and password.")
                elif authenticate_user(username, password):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.success("Logged in successfully!")
                else:
                    st.error("Invalid username or password.")
        else:
            st.warning("You are already logged in.")

    elif choice == "Logout":
        if st.session_state['logged_in']:
            if st.button("Logout"):
                logout()
                st.session_state['logged_in'] = False
                st.session_state['username'] = ''
                st.success("Logged out successfully!")
        else:
            st.warning("You are not logged in.")


    elif choice == "Register":
        st.subheader("Register")
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type='password')
        confirm_password = st.text_input("Confirm Password", type='password')
        if st.button("Register"):
            if not new_username or not new_password or not confirm_password:
                st.error("Please fill in all fields.")
            elif new_password != confirm_password:
                st.error("Passwords do not match. Please try again.")
            else:
                if insert_user(new_username, new_password):
                    st.success("Registration successful! You can now log in.")
                else:
                    st.error("Registration failed. Please try again.")


def logout():
    """
    Log out the current user by resetting the session state.
    """
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

if __name__ == "__main__":
    main()
