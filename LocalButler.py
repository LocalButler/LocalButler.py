import streamlit as st

# Function to display grocery services
def display_grocery_services():
    st.write("Order fresh groceries from your favorite local stores and have them delivered straight to your doorstep.")
    st.write("Select a grocery store:")
    grocery_store = st.selectbox("Choose a store:", ("Weis Markets", "SafeWay", "Commissary"))
    if grocery_store == "Weis Markets":
        st.write(f"You selected: [Weis Markets](https://www.weismarkets.com/)")
    elif grocery_store == "SafeWay":
        st.write(f"You selected: [SafeWay](https://www.safeway.com/)")
    elif grocery_store == "Commissary":
        st.write(f"You selected: [Commissary](https://www.commissaries.com/)")

# Function to display laundry services
def display_laundry_services():
    st.write("Schedule laundry pickup and delivery services, ensuring your clothes are clean and fresh with minimal effort.")

# Function to display meal delivery services
def display_meal_delivery_services():
    st.write("Enjoy delicious meals from top restaurants in your area delivered to your home or office.")

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
