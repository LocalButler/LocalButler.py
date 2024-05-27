import streamlit as st
import sqlite3

# Authentication functions
def authenticate_user(username, password):
    # For simplicity, we use a hardcoded username and password
    if username == "admin" and password == "password":
        return True
    return False

def login(username, password):
    if authenticate_user(username, password):
        st.session_state['logged_in'] = True
        st.session_state['username'] = username
        return True
    return False

def logout():
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

# Database functions
def create_connection():
    conn = None
    try:
        conn = sqlite3.connect('users.db')
    except sqlite3.Error as e:
        print(e)
    return conn

def create_table(conn):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                password TEXT
            )
        ''')
        conn.commit()
    except sqlite3.Error as e:
        print(e)

def insert_user(conn, username, password):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, password) VALUES (?, ?)
        ''', (username, password))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print(e)
        return None

def get_user_by_username(conn, username):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM users WHERE username = ?
        ''', (username,))
        return cursor.fetchone()
    except sqlite3.Error as e:
        print(e)
        return None

# Service functions
def display_grocery_services():
    st.write("Order fresh groceries from your favorite local stores and have them delivered straight to your doorstep.")
    st.write("Select a grocery store:")
    grocery_store = st.selectbox("Choose a store:", ("Weis Markets", "SafeWay", "Commissary", "Food Lion"))
    if grocery_store == "Weis Markets":
        st.write(f"You selected: [Weis Markets](https://www.weismarkets.com/)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with Weis Markets using your own account to accumulate grocery store points and clip your favorite coupons.")
        st.write("- Select store pick-up and specify the date and time.")
        st.write("- Let your assigned butler know you've placed a pick-up order, and we'll take care of the rest!")
    elif grocery_store == "SafeWay":
        st.write(f"You selected: [SafeWay](https://www.safeway.com/)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with Safeway using your own account to accumulate grocery store points and clip your favorite coupons.")
        st.write("- Select store pick-up and specify the date and time.")
        st.write("- Let your assigned butler know you've placed a pick-up order, and we'll take care of the rest!")
    elif grocery_store == "Commissary":
        st.write(f"You selected: [Commissary](https://shop.commissaries.com/)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with the Commissary using your own account.")
        st.write("- Select store pick-up and specify the date and time.")
        st.write("- Let your assigned butler know you've placed a pick-up order, and we'll take care of the rest!")
    elif grocery_store == "Food Lion":
        st.write(f"You selected: [Food Lion](https://shop.foodlion.com/?shopping_context=pickup&store=2517)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with Food Lion using your own account.")
        st.write("- Select store pick-up and specify the date and time.")
        st.write("- Let your assigned butler know you've placed a pick-up order, and we'll take care of the rest!")

def display_laundry_services():
    st.write("Schedule laundry pickup and delivery services, ensuring your clothes are clean and fresh with minimal effort.")

def display_meal_delivery_services():
    st.write("Enjoy delicious meals from top restaurants in your area delivered to your home or office.")
    st.write("Select a restaurant:")
    restaurant = st.selectbox("Choose a restaurant:", ("The Hideaway", "Ruth's Chris Steak House", "Baltimore Coffee & Tea Company", "The All American Steakhouse", "Jersey Mike's Subs", "Bruster's Real Ice Cream", "Luigino's", "PHO 5UP ODENTON", "Dunkin", "Baskin-Robbins"))
    if restaurant == "The Hideaway":
        st.write(f"You selected: [The Hideaway](https://order.toasttab.com/online/hideawayodenton)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with The Hideaway using their website or app.")
        st.write("- Select pick-up and specify the date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
    elif restaurant == "Ruth's Chris Steak House":
        st.write(f"You selected: [Ruth's Chris Steak House](https://order.ruthschris.com/)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with Ruth's Chris Steak House using their website or app.")
        st.write("- Select pick-up and specify the date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
    elif restaurant == "Baltimore Coffee & Tea Company":
        st.write(f"You selected: [Baltimore Coffee & Tea Company](https://www.baltcoffee.com/sites/default/files/pdf/2023WebMenu_1.pdf)")
        st.write("Instructions for placing your order:")
        st.write("- Review the menu and decide on your order.")
        st.write("- Call Baltimore Coffee & Tea Company to place your order.")
        st.write("- Specify that you'll be using Local Butler for pick-up and delivery.")
        st.write("- Let your assigned butler know the order you've placed, and we'll take care of the rest!")
        st.write("We apologize for any inconvenience, but Baltimore Coffee & Tea Company does not currently offer online ordering.")
    elif restaurant == "The All American Steakhouse":
        st.write(f"You selected: [The All American Steakhouse](https://order.theallamericansteakhouse.com/menu/odenton)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with The All American Steakhouse by using their website or app.")
        st.write("- Specify the items you want to order and the pick-up date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
    elif restaurant == "Jersey Mike's Subs":
        st.write(f"You selected: [Jersey Mike's Subs](https://www.jerseymikes.com/menu)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with Jersey Mike's Subs using their website or app.")
        st.write("- Specify the items you want to order and the pick-up date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
    elif restaurant == "Bruster's Real Ice Cream":
        st.write(f"You selected: [Bruster's Real Ice Cream](https://brustersonline.com/brusterscom/shoppingcart.aspx?number=415&source=homepage)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with Bruster's Real Ice Cream using their website or app.")
        st.write("- Specify the items you want to order and the pick-up date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
    elif restaurant == "Luigino's":
        st.write(f"You selected: [Luigino's](https://order.yourmenu.com/luiginos)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with Luigino's by using their website or app.")
        st.write("- Specify the items you want to order and the pick-up date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
    elif restaurant == "PHO 5UP ODENTON":
        st.write(f"You selected: [PHO 5UP ODENTON](https://www.clover.com/online-ordering/pho-5up-odenton)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with PHO 5UP ODENTON by using their website or app.")
        st.write("- Specify the items you want to order and the pick-up date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
    elif restaurant == "Dunkin":
        st.write(f"You selected: [Dunkin](https://www.dunkindonuts.com/en/mobile-app)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with Dunkin' by using their APP.")
        st.write("- Specify the items you want to order and the pick-up date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
    elif restaurant == "Baskin-Robbins":
        st.write(f"You selected: [Baskin-Robbins](https://order.baskinrobbins.com/categories?storeId=BR-339568)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with Baskin-Robbins by using their website or app.")
        st.write("- Specify the items you want to order and the pick-up date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")

def display_errand_services():
    st.write("Get help with various errands such as shopping, mailing packages, or picking up prescriptions.")

def display_pharmacy_services():
    st.write("Order prescription medications and over-the-counter products from local pharmacies with convenient delivery options.")

def display_pet_care_services():
    st.write("Ensure your furry friends receive the care they deserve with pet sitting, grooming, and walking services.")

def display_car_wash_services():
    st.write("Schedule car wash and detailing services to keep your vehicle clean and looking its best.")

def display_about_us():
    st.write("Local Butler is a dedicated concierge service aimed at providing convenience and peace of mind to residents of Fort Meade, Maryland 20755. Our mission is to simplify everyday tasks and errands, allowing our customers to focus on what matters most.")

def display_how_it_works():
    st.write("1. Choose a service category from the menu.")
    st.write("2. Select your desired service.")
    st.write("3. Follow the prompts to complete your order.")
    st.write("4. Sit back and relax while we take care of the rest!")

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''

def main():
    st.title("Local Butler")
    
    menu = ["Home", "Menu", "Order", "About Us", "Login", "Logout"]
    choice = st.sidebar.selectbox("Menu", menu)
    
    if choice == "Home":
        st.subheader("Welcome to Local Butler!")
        st.write("Please navigate through the sidebar to explore our app.")
    
    elif choice == "Menu":
        st.subheader("Menu")
        with st.expander("Service Categories", expanded=False):
            category = st.selectbox("Select a service category:", ("Grocery Services", "Laundry Services", "Meal Delivery Services", "Errand Services", "Pharmacy Services", "Pet Care Services", "Car Wash Services"))
            if category == "Grocery Services":
                display_grocery_services()
            elif category == "Laundry Services":
                display_laundry_services()
            elif category == "Meal Delivery Services":
                display_meal_delivery_services()
            elif category == "Errand Services":
                display_errand_services()
            elif category == "Pharmacy Services":
                display_pharmacy_services()
            elif category == "Pet Care Services":
                display_pet_care_services()
            elif category == "Car Wash Services":
                display_car_wash_services()
    
    elif choice == "Order":
    if st.session_state['logged_in']:
        st.subheader("Order")
        menu_items = get_menu_items()
        item_name = st.selectbox("Select an item", [item['name'] for item in menu_items])
        quantity = st.number_input("Quantity", min_value=1, max_value=10, step=1)
        if st.button("Place Order"):
            add_order(st.session_state['username'], item_name, quantity)
            st.success("Order placed successfully!")
    else:
        st.warning("Please log in to place an order.")
    
    elif choice == "About Us":
        st.subheader("About Us")
        display_about_us()
    
    elif choice == "Login":
        if not st.session_state['logged_in']:
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
        if st.session_state['logged_in']:
            if st.button("Logout"):
                logout()
                st.session_state['logged_in'] = False
                st.session_state['username'] = ''
                st.success("Logged out successfully!")
        else:
            st.warning("You are not logged in.")

if __name__ == "__main__":
    conn = create_connection()
    if conn is not None:
        create_table(conn)
    main()
