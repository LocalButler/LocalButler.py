Local Butler 🚚
Local Butler is a hyperlocal delivery service app designed to connect customers with nearby merchants for convenient pickup and delivery. This Streamlit-based application offers a seamless interface for users to browse local businesses, place orders, and track deliveries.

Features
User Authentication: Register/login as a customer, driver, merchant, or service provider.

Order Placement: Easily place new orders specifying service, date/time, and delivery address.

Order Tracking: Track order status in real-time with interactive progress updates.

Merchant Map: Explore nearby merchants with an interactive map showing locations and details.

Service Listings: Browse available services from grocery stores, restaurants, and more.

Customized User Experience: Personalize your experience based on user type with tailored menus and functionalities.

Technologies Used
Python: Backend logic and integration with SQLAlchemy for database management.

Streamlit: Frontend development for interactive UI and data visualization.

Folium: Integration for interactive maps displaying merchant locations.

SQLite: Database management for storing user, merchant, and order data securely.

Geopy: Geocoding integration for accurate merchant location mapping.

Argon2: Password hashing for secure user authentication.

Pandas, NumPy: Data manipulation and processing within the application.

Installation
Clone the repository:

bash
Copy code
git clone https://github.com/your_username/local-butler.git
cd local-butler
Install dependencies:

bash
Copy code
pip install -r requirements.txt
Set up the SQLite database:

bash
Copy code
python setup_db.py
Run the Streamlit app:

bash
Copy code
streamlit run app.py
Access the app in your browser at http://localhost:8501.

Usage
Login/Register: Choose user type (customer, driver, merchant, service provider) and log in or register.

Explore Services: Navigate through available services (grocery stores, restaurants) and view details.

Place Orders: Select a merchant, specify service details, date/time, and delivery address, then confirm the order.

Track Orders: Monitor order status in real-time, with live updates as the order progresses.

Interactive Map: Use the map feature to explore nearby merchants and their contact details.

Contributors
Alejandro Samid - Founder & Developer

Licensing
Dual Licensing Approach
Proprietary License for Commercial Use:
For commercial purposes, Local Butler is available under a proprietary license. This license requires businesses and entities using Local Butler commercially to obtain a subscription. 
Permissive License for Non-Commercial Use:
For non-commercial use, Local Butler is also available under the MIT License. This allows individuals, open-source projects, and non-profit organizations to use and contribute to Local Butler freely without a subscription. 

Acknowledgments
Inspired by the need for efficient hyperlocal delivery solutions.
Special thanks to the Streamlit and SQLAlchemy communities for their open-source contributions.
