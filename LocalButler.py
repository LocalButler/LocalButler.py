import streamlit as st
import streamlit.components.v1 as components
import sqlite3
from pathlib import Path
import hashlib
import os
import requests
import openai

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
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except sqlite3.Error as e:
        st.error(f"Error connecting to the database: {e}")
        return None

def insert_user(username, password):
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
    # ... other grocery stores ...
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
    # ... other restaurants ...
}

# Firebase Functions URLs
FIREBASE_FUNCTIONS = {
    "placeOrder": "https://us-central1-MY_PROJECT.cloudfunctions.net/placeOrder",
    "updateOrderStatus": "https://us-central1-MY_PROJECT.cloudfunctions.net/updateOrderStatus",
    "updateButlerStatus": "https://us-central1-MY_PROJECT.cloudfunctions.net/updateButlerStatus"
}

# Replace 'MY_PROJECT' with your actual Firebase project ID

# Service display functions
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

    st.write("Select a grocery store:")
    grocery_store = st.selectbox("Choose a store:", list(GROCERY_STORES.keys()))
    store_info = GROCERY_STORES[grocery_store]
    st.write(f"You selected: [{grocery_store}]({store_info['url']})")
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

# Functions to interact with Firebase
def place_order(service, provider, items, pickup_time):
    url = FIREBASE_FUNCTIONS["placeOrder"]
    data = {
        "service": service,
        "provider": provider,
        "items": items,
        "pickupTime": pickup_time,
        "userId": st.session_state['username']
    }
    response = requests.post(url, json=data)
    return response.json()

def update_order_status(order_id, status):
    url = FIREBASE_FUNCTIONS["updateOrderStatus"]
    data = {
        "orderId": order_id,
        "status": status
    }
    response = requests.post(url, json=data)
    return response.json()

def update_butler_status(butler_id, available):
    url = FIREBASE_FUNCTIONS["updateButlerStatus"]
    data = {
        "butlerId": butler_id,
        "available": available
    }
    response = requests.post(url, json=data)
    return response.json()

# Chatbot functions and data
SERVICE_INFO = """
Local Butler is your reliable delivery partner offering a range of services to make your life easier. Here's a quick overview of what we do:

1. **Grocery Services**:
    - Order fresh groceries from your favorite local stores like Weis Markets, SafeWay, Commissary, and Food Lion.
    - Place your order directly with the store and select store pick-up. We'll handle the rest!

2. **Meal Delivery Services**:
    - Enjoy delicious meals from top restaurants such as The Hideaway, Ruth's Chris Steak House, Baltimore Coffee & Tea Company, and more.
    - Place your order directly with the restaurant and select pick-up. We'll handle the delivery!

3. **Laundry Services**:
    - Schedule laundry pick-up and delivery, ensuring your clothes are clean and fresh with minimal effort.

4. **Errand Services**:
    - Get help with various errands such as shopping, mailing packages, or picking up prescriptions.

5. **Pharmacy Services**:
    - Order prescription medications and over-the-counter products from local pharmacies with convenient delivery options.

6. **Pet Care Services**:
    - Ensure your furry friends receive the care they deserve with pet sitting, grooming, and walking services.

7. **Car Wash Services**:
    - Schedule car wash and detailing services to keep your vehicle clean and looking its best.

Let me know how I can assist you with any of these services!
"""

# Initialize session state for messages if not already present
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Hello! How can I assist you today with Local Butler services?"}]

# Prepend the service information to the conversation
if "service_info" not in st.session_state:
    st.session_state["service_info"] = SERVICE_INFO
    st.session_state["messages"].insert(0, {"role": "system", "content": st.session_state["service_info"]})

def display_chat_history():
    for msg in st.session_state.messages:
        if msg["role"] == "assistant":
            st.chat_message("assistant").write(msg["content"])
        elif msg["role"] == "user":
            st.chat_message("user").write(msg["content"])

def get_assistant_response(messages):
    openai.api_key = openai_api_key
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"Error: {e}"

# Main function
def main():
    st.set_page_config(page_title="Local Butler")

    st.markdown(
        """
        <style>
            .title-container {
                display: flex;
                align-items: center;
            }
            .title-container h1 {
                margin-right: 20px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="title-container">
            <h1 style="margin: 0;">Local Butler</h1>
            <div style="flex-grow: 1;"></div>
            <img src="http://res.cloudinary.com/dwmwpmrpo/image/upload/v1717008483/by8oaqcazjlqverba9r3.png" style="width: 100px;">
        </div>
        """,
        unsafe_allow_html=True
    )

    menu = ["Home", "Menu", "Order", "My Orders", "About Us", "Chat with Butler", "Login", "Logout", "Register"]
    choice = st.sidebar.selectbox("Menu", menu)

    # Add this inside the sidebar for the chatbot's API key
    with st.sidebar:
        openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
        st.markdown("[Get an OpenAI API key](https://platform.openai.com/account/api-keys)")

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
        if st.session_state.get('logged_in', False):
            st.subheader("Order")
            service = st.selectbox("Select a service:", ("Grocery", "Meal Delivery"))
            
            provider_options = list(GROCERY_STORES.keys()) if service == "Grocery" else list(RESTAURANTS.keys())
            provider = st.selectbox("Select a provider:", provider_options)
            
            items = st.text_area("Enter your items:")
            pickup_time = st.datetime_input("Select pickup time:")
            
            if st.button("Place Order"):
                result = place_order(service, provider, items, pickup_time.isoformat())
                st.success(result["result"])
        else:
            st.warning("Please log in to place an order.")

    elif choice == "My Orders":
        if st.session_state.get('logged_in', False):
            st.subheader("My Orders")
            # TODO: Fetch user's orders from Firestore
            st.info("Feature coming soon: View and manage your orders here.")
        else:
            st.warning("Please log in to view your orders.")

    elif choice == "About Us":
        st.subheader("About Us")
        st.write("Local Butler is a dedicated concierge service aimed at providing convenience and peace of mind to residents of Fort Meade, Maryland 20755. Our mission is to simplify everyday tasks and errands, allowing our customers to focus on what matters most.")
        st.write("1. Choose a service category from the menu.")
        st.write("2. Select your desired service.")
        st.write("3. Follow the prompts to complete your order.")
        st.write("4. Sit back and relax while we take care of the rest!")

    elif choice == "Chat with Butler":
        st.title("💬 Chat with Your Local Butler")
        
        if not openai_api_key:
            st.info("Please add your OpenAI API key in the sidebar to continue.")
        else:
            display_chat_history()

            # Handle user input
            if prompt := st.chat_input("Type your message here..."):
                # Append user message to session state
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.chat_message("user").write(prompt)

                # Get assistant's response
                msg = get_assistant_response(st.session_state["messages"])
                st.session_state.messages.append({"role": "assistant", "content": msg})
                st.chat_message("assistant").write(msg)

            if st.button("Clear Chat History"):
                st.session_state.pop("messages", None)
                st.session_state.pop("service_info", None)
                st.experimental_rerun()

    elif choice == "Login":
        if not st.session_state.get('logged_in', False):
            username = st.text_input("Username")
            password = st.text_input("Password", type='password')
            if st.button("Login"):
                if authenticate_user(username, password):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = username
                    st.success("Logged in successfully!")
                else:
                    st.error("Invalid username or password.")
        else:
            st.warning("You are already logged in.")

    elif choice == "Logout":
        if st.session_state.get('logged_in', False):
            if st.button("Logout"):
                st.session_state['logged_in'] = False
                st.session_state['username'] = ''
                st.session_state.pop("chatbot_api_key", None)
                st.session_state.pop("messages", None)
                st.session_state.pop("service_info", None)
                st.success("Logged out successfully!")
        else:
            st.warning("You are not logged in.")

    elif choice == "Register":
        st.subheader("Register")
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type='password')
        confirm_password = st.text_input("Confirm Password", type='password')

        if st.button("Register"):
            if new_password == confirm_password:
                if insert_user(new_username, new_password):
                    st.success("Registration successful! You can now log in.")
                else:
                    st.error("Registration failed. Please try again.")
            else:
                st.error("Passwords do not match. Please try again.")

# Initialize session state for login
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

if __name__ == "__main__":
    main()
