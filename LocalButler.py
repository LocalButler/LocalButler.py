import streamlit as st

# Function to display grocery services
def display_grocery_services():
    st.write("Order fresh groceries from your favorite local stores and have them delivered straight to your doorstep.")
    st.write("Select a grocery store:")
    grocery_store = st.selectbox("Choose a store:", ("Weis Markets", "SafeWay", "Commissary"))
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


# Function to display laundry services
def display_laundry_services():
    st.write("Schedule laundry pickup and delivery services, ensuring your clothes are clean and fresh with minimal effort.")

# Function to display meal delivery services
def display_meal_delivery_services():
    st.write("Enjoy delicious meals from top restaurants in your area delivered to your home or office.")
    st.write("Select a restaurant:")
    restaurant = st.selectbox("Choose a restaurant:", ("The Hideaway", "Ruth's Chris Steak House", "Baltimore Coffee & Tea Company", "The All American Steakhouse", "Jersey Mike's Subs", "Bruster's Real Ice Cream", "Luigino's", "PHO 5UP ODENTON", "Dunkin'", "Baskin-Robbins"))
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
        st.write(f"You selected: [The All American Steakhouse](https://www.theallamericansteakhouse.com/)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with The All American Steakhouse by calling their restaurant.")
        st.write("- Specify the items you want to order and the pick-up date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
    elif restaurant == "Jersey Mike's Subs":
        st.write(f"You selected: [Jersey Mike's Subs](https://www.jerseymikes.com/)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with Jersey Mike's Subs by calling their restaurant.")
        st.write("- Specify the items you want to order and the pick-up date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
    elif restaurant == "Bruster's Real Ice Cream":
        st.write(f"You selected: [Bruster's Real Ice Cream](https://brusters.com/)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with Bruster's Real Ice Cream by calling their store.")
        st.write("- Specify the items you want to order and the pick-up date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
    elif restaurant == "Luigino's":
        st.write(f"You selected: [Luigino's](https://www.luiginosrestaurant.com/)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with Luigino's by calling their restaurant.")
        st.write("- Specify the items you want to order and the pick-up date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
    elif restaurant == "PHO 5UP ODENTON":
        st.write(f"You selected: [PHO 5UP ODENTON](https://www.pho5up.com/)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with PHO 5UP ODENTON by calling their restaurant.")
        st.write("- Specify the items you want to order and the pick-up date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
    elif restaurant == "Dunkin":
        st.write(f"You selected: [Dunkin'](https://www.dunkindonuts.com/)")
        st.write("Instructions for placing your order:")
        st.write("- Place your order directly with Dunkin' by calling their store.")
        st.write("- Specify the items you want to order and the pick-up date and time.")
        st.write("- Let your assigned butler know you've placed an order, and we'll take care of the rest!")
 
# Function to display errand services
def display_errand_services():
    st.write("Get help with various errands such as shopping, mailing packages, or picking up prescriptions.")

# Function to display pharmacy services
def display_pharmacy_services():
    st.write("Order prescription medications and over-the-counter products from local pharmacies with convenient delivery options.")

# Function to display pet care services
def display_pet_care_services():
    st.write("Ensure your furry friends receive the care they deserve with pet sitting, grooming, and walking services.")

# Function to display car wash services
def display_car_wash_services():
    st.write("Schedule car wash and detailing services to keep your vehicle clean and looking its best.")

# Function to display about us section
def display_about_us():
    st.write("Local Butler is a dedicated concierge service aimed at providing convenience and peace of mind to residents of Fort Meade. Our mission is to simplify everyday tasks and errands, allowing our customers to focus on what matters most.")

# Function to display how it works section
def display_how_it_works():
    st.write("1. Choose a service category from the menu.")
    st.write("2. Select your desired service.")
    st.write("3. Follow the prompts to complete your order.")
    st.write("4. Sit back and relax while we take care of the rest!")

# Main function to run the Local Butler app
def main():
    # Display "LOCAL BUTLER" at the top in bold
    st.title("**LOCAL BUTLER**")

    # Display menu button for services
    with st.expander("Menu", expanded=False):
        category = st.selectbox("Select a service category:",
                                ("Grocery Services", "Laundry Services", "Meal Delivery Services", "Errand Services",
                                 "Pharmacy Services", "Pet Care Services", "Car Wash Services"))

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

    # Display expander button for About Us section
    with st.expander("About Us", expanded=False):
        display_about_us()

    # Display expander button for How it Works section
    with st.expander("How it Works", expanded=False):
        display_how_it_works()

if __name__ == "__main__":
    main()
