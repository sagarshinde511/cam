import streamlit as st
import cv2
from PIL import Image
import numpy as np
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import pandas as pd
import qrcode
from io import BytesIO

# Default username and password
USERNAME = "admin"
PASSWORD = "admin"

def authenticate(username, password):
    """Authenticate user based on provided username and password."""
    return username == USERNAME and password == PASSWORD

def main():
    # Display login form on the sidebar
    with st.sidebar:
        st.header("Login to Access the App")
        username = st.text_input("Username", "")
        password = st.text_input("Password", "", type="password")
        login_button = st.button("Login")

        # Check if the login button is clicked
        if login_button:
            if authenticate(username, password):
                st.session_state.logged_in = True
                st.sidebar.success("Login successful!")
            else:
                st.sidebar.error("Invalid username or password.")

    # Only show the main content if the user is authenticated
    if "logged_in" in st.session_state and st.session_state.logged_in:
        # Create tabs for the app
        tab1, tab2, tab3, tab4 = st.tabs(["QR Code Scanner", "Book Information Viewer", "Issued Book List", "All Books"])
        
        with tab1:
            issue_or_return = st.radio(
                "What action would you like to perform?",
                ["CheckBooks", "Issue Book", "Return Book"]
            )

            # Only call `read_qr_code_from_camera` if "Issue Book" or "Return Book" is selected
            if issue_or_return in ["Issue Book", "Return Book"]:
                book_id = read_qr_code_from_camera(issue_or_return.lower())
                if book_id:
                    st.session_state["book_id"] = book_id

            elif issue_or_return == "CheckBooks":
                if st.button("Read RFID"):
                    rfid_no = fetch_rfid_data()
                    if rfid_no:
                        st.success(f"RFID Number: {rfid_no}")
                        book_history = fetch_book_history(rfid_no)
                        if book_history:
                            st.subheader("Book History")
                            st.table(book_history)
                        else:
                            st.warning("No book history found for the given RFID.")
                    else:
                        st.error("No RFID data available in the ReadRFID table.")
        with tab2:
            if "book_id" in st.session_state:
                book_id = st.session_state["book_id"]
                book_info = fetch_data(book_id)
                if book_info:
                    st.subheader("Book Information")
                    st.write(f"**Book Name:** {book_info['BookName']}")
                    st.write(f"**Author:** {book_info['Author']}")
                    st.write(f"**In Stock:** {book_info['InStock']}")
                    st.write(f"**Available Stock:** {book_info['AvailableStock']}")

                    if issue_or_return == "Issue" and int(book_info['AvailableStock']) > 0:
                        # Add a button to assign the book
                        if st.button("Assign Book"):
                            rfid = fetch_rfid(book_id)  # Fetch RFID for the book
                            if rfid and int(rfid) != 0:
                                st.success(f"RFID Number: {rfid}")
                                create_history(rfid, book_id)

                                # Update available stock in the database
                                new_stock = int(book_info['AvailableStock']) - 1
                                update_stock(book_id, new_stock)
                                st.info(f"Book assigned successfully. Updated available stock: {new_stock}")
                            else:
                                st.error("RFID Number is either not assigned or invalid.")
                    elif issue_or_return == "Return":
                        # Handle return by updating the return status and increasing stock
                        if st.button("Return Book"):
                            update_return_status_and_stock(book_id)
                    else:
                        st.warning("This book is out of stock.")
                else:
                    st.error("Book information could not be retrieved. Please check the Book ID.")
            else:
                st.info("Please scan a QR code to view book information.")
        with tab3:
                st.subheader("Serch Book Here")
                # Input for BookId
                book_id = st.text_input("Enter BookId to search:")
                
                if st.button("Search"):
                    if book_id.strip():
                        try:
                            data = fetch_book_details(book_id)
                            if not data.empty:
                                st.dataframe(data)
                            else:
                                st.write("No data found for the given BookId.")
                        except Exception as e:
                            st.error(f"An error occurred: {e}")
                    else:
                        st.warning("Please enter a valid BookId.")
        with tab4:
                st.subheader("Serch Book Here")
                # Input for BookId
                # Display all books
                mode = st.radio("Select an Option", ["Fetch All Books", "Add Book Info", "Update Book Info", "Genrate QR Code"])
            
                if mode == "Fetch All Books":
                    st.subheader("Books in Library")
                    try:
                        books = fetch_all_books()
                        if not books.empty:
                            st.dataframe(books)
                        else:
                            st.write("No books found in the library.")
                    except Exception as e:
                        st.error(f"Error fetching books: {e}")
                elif mode == "Genrate QR Code":
                    st.subheader("Genrate QR code for Book")
                    url = st.text_input("Enter BookID to Genrate QR Code:")
                    
                    if st.button("Generate QR Code"):
                        if url.strip():
                            try:
                                # Generate QR code
                                qr_image = generate_qr_code(url)
                                
                                # Convert QR code image to BytesIO for display
                                buffer = BytesIO()
                                qr_image.save(buffer, format="PNG")
                                buffer.seek(0)
                                
                                # Display the QR code
                                st.image(Image.open(buffer), caption="Your QR Code", use_column_width=True)
                                
                                # Provide download option
                                st.download_button(
                                    label="Download QR Code",
                                    data=buffer,
                                    file_name= url + "qrcode.png",
                                    mime="image/png"
                                )
                            except Exception as e:
                                st.error(f"Error generating QR Code: {e}")
                        else:
                            st.warning("Please enter a valid URL or text.")
                
                elif mode == "Add Book Info":
                    st.subheader("Add Book Info")
            
                    # Book addition or update form
                    with st.form("book_form"):
                        #action = st.radio("Select Action", ["Add New Book", "Update Existing Book])
                        #if action == "Update Existing Book":
                        #    book_id = st.text_input("Book ID (for Update)")
                        book_name = st.text_input("Book Name")
                        author = st.text_input("Author")
                        Instock = st.text_input("Instock")
                        AvailableStock = st.text_input("AvailableStock")

                        submit = st.form_submit_button("Submit")
            
                        if submit:
                            if action == "Add New Book":
                                if book_name.strip() and author.strip():
                                    try:
                                        add_new_book(book_name, author,Instock, AvailableStock)
                                        st.success(f"Book '{book_name}' by {author} added successfully!")
                                    except Exception as e:
                                        st.error(f"Error adding book: {e}")
                                else:
                                    st.warning("Please provide both Book Name and Author.")
                            
                            elif action == "Update Existing Book":
                                if book_id.strip() and book_name.strip() and author.strip():
                                    try:
                                        update_book_info(book_id, book_name, author)
                                        st.success(f"Book ID '{book_id}' updated to '{book_name}' by {author} successfully!")
                                    except Exception as e:
                                        st.error(f"Error updating book: {e}")
                                else:
                                    st.warning("Please provide Book ID, Book Name, and Author.")
    else:
        st.warning("Please login to access the application.")
        

if __name__ == "__main__":
    main()
