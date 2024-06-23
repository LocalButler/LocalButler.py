import streamlit as st
import streamlit.components.v1 as components
import sqlite3
from pathlib import Path
import bcrypt
import os
from datetime import datetime, timedelta

# Database setup
DB_FILE = "users.db"
db_path = Path(DB_FILE)
if not db_path.exists():
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            last_login DATETIME,
            login_attempts INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Database functions
def get_db_connection():
    return sqlite3.connect(DB_FILE)

def insert_user(username, password):
    conn = get_db_connection()
    try:
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
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
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT password, login_attempts, last_login FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user:
            stored_password, login_attempts, last_login = user
            if last_login:
                last_login = datetime.strptime(last_login, "%Y-%m-%d %H:%M:%S")
                if datetime.now() - last_login > timedelta(minutes=15):
                    cursor.execute("UPDATE users SET login_attempts = 0 WHERE username = ?", (username,))
                    conn.commit()
                    login_attempts = 0

            if login_attempts >= 5:
                st.error("Account locked. Please try again later.")
                return False

            if bcrypt.checkpw(password.encode(), stored_password):
                cursor.execute("UPDATE users SET login_attempts = 0, last_login = ? WHERE username = ?", (datetime.now(), username))
                conn.commit()
                return True
            else:
                cursor.execute("UPDATE users SET login_attempts = login_attempts + 1 WHERE username = ?", (username,))
                conn.commit()
                return False
        return False
    except sqlite3.Error as e:
        st.error(f"Error authenticating user: {e}")
        return False
    finally:
        conn.close()

# Service data (Consider moving this to a database in a production environment)
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
    # ... (other grocery stores)
}

RESTAURANTS = {
    "The Hideaway": {
        "url": "https://order.toasttab.com/online/hideawayodenton",
        "instructions": [
            "Place your order directly with The Hideaway using their website or app.",
            "Select pick-up and specify the date and time.",
            "Let Butler Bot know you've placed a pick-up order, and we'll take care of the rest!"
        ]
    },
    # ... (other restaurants)
}

# Service display functions
def display_service(service_type, services):
    st.write(f"Select a {service_type}:")
    service = st.selectbox(f"Choose a {service_type}:", list(services.keys()))
    service_info = services[service]
    st.write(f"ORDER NOW: [{service}]({service_info['url']})")
    
    if "video_url" in service_info:
        st.markdown(f"### {service_info['video_title']}")
        video_html = f"""
            <div style="position: relative; width: 100%; height: 0; padding-bottom: 56.25%;">
                <video autoplay playsinline controls
                    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
                    frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture">
                    <source src="{service_info['video_url']}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </div>
        """
        components.html(video_html, height=315)
    elif "image_url" in service_info:
        st.image(service_info['image_url'], caption=f"{service} App", use_column_width=True)
    
    st.write("Instructions for placing your order:")
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

    st.title("Local Butler")
    st.image("https://raw.githubusercontent.com/LocalButler/streamlit_app.py/main/Local%20Butler.jpg", width=200)

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
            category = st.selectbox("Select a service category:", ("Grocery Services", "Meal Delivery Services"))
            if category == "Grocery Services":
                display_service("grocery store", GROCERY_STORES)
            elif category == "Meal Delivery Services":
                display_service("restaurant", RESTAURANTS)

    elif choice == "Order":
        if st.session_state['logged_in']:
            st.subheader("Order")
            st.write("Order functionality coming soon!")
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
                    st.experimental_rerun()
                else:
                    st.error("Invalid username or password.")
        else:
            st.warning("You are already logged in.")

    elif choice == "Logout":
        if st.session_state['logged_in']:
            if st.button("Logout"):
                st.session_state['logged_in'] = False
                st.session_state['username'] = ''
                st.success("Logged out successfully!")
                st.experimental_rerun()
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
            elif len(new_password) < 8:
                st.error("Password must be at least 8 characters long.")
            else:
                if insert_user(new_username, new_password):
                    st.success("Registration successful! You can now log in.")
                else:
                    st.error("Registration failed. Please try again.")

if __name__ == "__main__":
    main()
