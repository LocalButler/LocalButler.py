import streamlit as st

# Function to display grocery services
def display_grocery_services():
    selected_store = st.selectbox("Select a grocery store:",
                                ("Weis Markets", "SafeWay", "Commissary"))
    
    if selected_store == "Weis Markets":
        st.write("Order fresh groceries from Weis Markets and have them delivered straight to your doorstep.")
    elif selected_store == "SafeWay":
        st.write("Order fresh groceries from SafeWay and have them delivered straight to your doorstep.")
    elif selected_store == "Commissary":
        st.write("Order fresh groceries from the Commissary and have them ready for pickup.")

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
        # Add other categories here...

if __name__ == "__main__":
    main()
