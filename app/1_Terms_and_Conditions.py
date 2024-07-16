
import streamlit as st

def main():
    st.title("Terms and Conditions")

    st.write("""
    Welcome to the Terms and Conditions page for Local Butler.

Acceptance of Terms
By using the Local Butler app, you agree to be bound by these Terms and Conditions. If you do not agree to these terms, please do not use the app.
User Registration

2.1 You must register for an account to use the full features of the app.
2.2 You agree to provide accurate and complete information during the registration process.
2.3 You are responsible for maintaining the confidentiality of your account information.
Services
3.1 Local Butler provides a platform for ordering groceries and food from local merchants.
3.2 We do not guarantee the availability of any particular merchant or product.
3.3 Prices and availability of products are subject to change without notice.
Orders
4.1 By placing an order, you agree to pay the full amount for the items ordered plus any applicable fees.
4.2 Once an order is placed, it cannot be cancelled or modified.
4.3 Delivery times are estimates and not guaranteed.
User Conduct
5.1 You agree not to use the app for any unlawful purpose or in any way that could damage or impair the app's functionality.
5.2 You agree not to attempt to gain unauthorized access to any part of the app or its systems.
Privacy
6.1 Your use of the app is subject to our Privacy Policy, which is incorporated into these Terms and Conditions.
Intellectual Property
7.1 All content and functionality of the app are the property of Local Butler or its licensors and are protected by copyright and other intellectual property laws.
Disclaimer of Warranties
8.1 The app is provided "as is" without any warranties, express or implied.
8.2 We do not guarantee that the app will be error-free or uninterrupted.
Limitation of Liability
9.1 Local Butler shall not be liable for any indirect, incidental, special, consequential, or punitive damages resulting from your use of the app.
Amendments
10.1 We reserve the right to modify these Terms and Conditions at any time. Continued use of the app after any changes constitutes acceptance of the new Terms and Conditions.
Governing Law
11.1 These Terms and Conditions shall be governed by and construed in accordance with the laws of Anne Arundel County, Maryland.

    By using Local Butler, you acknowledge that you have read, understood, and agree to be bound by these Terms and Conditions.
    """)

    st.write("Last updated: July 16, 2024")

    if st.button("Return to Home"):
        st.switch_page("Home.py")

if __name__ == "__main__":
    main()
