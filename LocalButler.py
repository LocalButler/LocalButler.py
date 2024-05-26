import streamlit as st

# Function to display grocery services
def display_grocery_services():
    st.write("This section displays grocery services.")

# Function to display laundry services
def display_laundry_services():
    st.write("This section displays laundry services.")

# Function to display meal delivery services
def display_meal_delivery_services():
    st.write("This section displays meal delivery services.")

# Function to display errand services
def display_errand_services():
    st.write("This section displays errand services.")

# Function to display pharmacy services
def display_pharmacy_services():
    st.write("This section displays pharmacy services.")

# Function to display pet care services
def display_pet_care_services():
    st.write("This section displays pet care services.")

# Function to display car wash services
def display_car_wash_services():
    st.write("This section displays car wash services.")

# Main function to run the Local Butler app
def main():
    st.title("Welcome to Local Butler")

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
