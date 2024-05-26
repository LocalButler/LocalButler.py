import streamlit as st

# Function to display grocery services
def display_grocery_services():
    st.write("Order fresh groceries from your favorite local stores and have them delivered straight to your doorstep.")

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

# Main function to run the Local Butler app
def main():
    st.title("Welcome to Local Butler")

    # Arrow indicator to show where to click for the menu
    st.write("Click the arrow next to 'Menu' to view available services ➡️")

    # Display menu
    st.sidebar.title("Local Butler Menu")
    category = st.sidebar.radio("Select a service category:",
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

if __name__ == "__main__":
    main()

    main()
