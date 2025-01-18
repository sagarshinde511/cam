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
host = "82.180.143.66"
user = "u263681140_students"
passwd = "testStudents@123"
db_name = "u263681140_students"

HOST = "82.180.143.66"
USER = "u263681140_students"
PASSWORD = "testStudents@123"
DATABASE = "u263681140_students"
# Default username and password
USERNAME = "admin"
PASSWORD = "admin"
def get_connection():
    return mysql.connector.connect(
        host="82.180.143.66",
        user="u263681140_students",
        passwd="testStudents@123",
        database="u263681140_students"
    )

def fetch_book_details(book_id):
    query = """
        SELECT 
            BookHistory.date AS BorrowDate,
            BookHistory.RFidNo,
            BookHistory.BookId,
            BookHistory.ReturnDate,
            BookInfo.BookName,
            BookInfo.Author,
            BookStudents.Name AS StudentName,
            BookStudents.Branch,
            BookStudents.Year
        FROM 
            BookHistory
        JOIN 
            BookInfo 
        ON 
            BookHistory.BookId = BookInfo.id
        JOIN 
            BookStudents 
        ON 
            BookHistory.RFidNo = BookStudents.RFidNo
        WHERE 
            BookHistory.BookId = %s
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (book_id,))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return pd.DataFrame(results)
def update_stock(book_id, new_stock):
    """
    Updates the available stock for a book in the database.

    Args:
        book_id (str): The ID of the book to update.
        new_stock (int): The new stock value to set.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    connection = None
    try:
        # Establish a connection to the database
        connection = mysql.connector.connect(
            host=HOST,
            user=USER,
            password=PASSWORD,
            database=DATABASE
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # Update the available stock for the book
            update_query = "UPDATE BookInfo SET AvailableStock = %s WHERE id = %s"
            cursor.execute(update_query, (new_stock, book_id))

            # Commit the transaction
            connection.commit()

            # Check if rows were affected
            if cursor.rowcount > 0:
                print("Stock updated successfully.")
                return True
            else:
                print("Book ID not found. No update made.")
                return False

    except Error as e:
        print(f"Error while connecting to the database: {e}")
        return False

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def fetch_data(book_id):
    try:
        # Establish connection to MySQL database
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=passwd,
            database=db_name
        )
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # Query to fetch book information
            query = "SELECT BookName, Author, InStock, AvailableStock FROM BookInfo WHERE id = %s"
            cursor.execute(query, (book_id,))
            result = cursor.fetchone()
            return result
    except Error as e:
        st.error(f"Error connecting to database: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Function to fetch RFidNo from the BookHistory table
def read_qr_code_from_camera(issue_or_return):
    st.title(f"QR Code Scanner - {issue_or_return.capitalize()} Book")

    # Use Streamlit's camera input
    camera_image = st.camera_input(f"Take a picture to scan for QR codes to {issue_or_return}.")

    if camera_image:
        # Convert the captured image to OpenCV format
        image = Image.open(camera_image)
        frame = np.array(image)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # Decode QR codes in the frame using OpenCV's QRCodeDetector
        qr_detector = cv2.QRCodeDetector()
        value, points, _ = qr_detector.detectAndDecode(frame)

        if value:
            st.success(f"Book ID is: {value}")
            return value
        else:
            st.warning("No QR Code detected.")
            return None

# Function to fetch RFidNo from the BookHistory table
def fetch_rfid(book_id):
    try:
        # Establish connection to MySQL database
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=passwd,
            database=db_name
        )
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # Query to fetch RFidNo from BookHistory where id matches the book_id
            query = "SELECT RFidNo FROM ReadRFID WHERE id = %s"
            cursor.execute(query, (book_id,))
            result = cursor.fetchone()
            return result['RFidNo'] if result else None
    except Error as e:
        st.error(f"Error connecting to database: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def create_history(rfid, book_id):
    try:
        # Connect to the MySQL database
        conn = mysql.connector.connect(
            host="82.180.143.66",
            user="u263681140_students",
            passwd="testStudents@123",
            database="u263681140_students"
        )
        cursor = conn.cursor()

        # Insert data into the BookHistory table
        query = "INSERT INTO BookHistory (RFidNo, BookId) VALUES (%s, %s)"
        cursor.execute(query, (rfid, book_id))
        
        # Commit the transaction
        conn.commit()
        
        # Close the connection
        cursor.close()
        conn.close()
        
        return True  # Success
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
        return False  # Failure
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return False


def update_return_status_and_stock(book_id):
    try:
        # Connect to the MySQL database
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=passwd,
            database=db_name
        )
        cursor = conn.cursor()

        # Get the current date
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Update ReturnStatus to 1 and set the ReturnDate where BookId matches and ReturnStatus is NULL
        query = """
            UPDATE BookHistory 
            SET ReturnStatus = 1, ReturnDate = %s 
            WHERE BookId = %s AND ReturnStatus IS NULL
        """
        cursor.execute(query, (current_date, book_id))
        
        # Increase the available stock by 1 for the book
        stock_query = "UPDATE BookInfo SET AvailableStock = AvailableStock + 1 WHERE id = %s"
        cursor.execute(stock_query, (book_id,))

        # Commit the transaction
        conn.commit()

        # Check if rows were affected
        if cursor.rowcount > 0:
            st.success(f"Return status updated, return date set to {current_date}, and available stock increased for Book ID {book_id}.")
        else:
            st.warning("No matching entry found for return or the book is already returned.")

        # Close the connection
        cursor.close()
        conn.close()
        
        return True  # Success
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
        return False  # Failure
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return False
def fetch_rfid_data():
    """
    Fetch the latest RFidNo from the ReadRFID table.
    """
    try:
        # Establish connection to MySQL database
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=passwd,
            database=db_name
        )
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # Query to fetch the most recent RFidNo from the ReadRFID table
            query = "SELECT RFidNo FROM ReadRFID ORDER BY id DESC LIMIT 1"
            cursor.execute(query)
            result = cursor.fetchone()
            return result['RFidNo'] if result else None
    except Error as e:
        st.error(f"Error connecting to the database: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
def generate_qr_code(url):
    # Create a QR Code instance
    qr = qrcode.QRCode(
        version=5,  # Controls the size of the QR Code
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,  # Size of each box in the QR code grid
        border=4,  # Thickness of the border (in boxes)
    )
    
    # Add the URL to the QR Code
    qr.add_data(url)
    qr.make(fit=True)

    # Create an image from the QR Code instance
    img = qr.make_image(fill_color="black", back_color="white")
    return img

def fetch_all_books():
    query = "SELECT id, BookName, Author, Instock, AvailableStock FROM BookInfo"
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return pd.DataFrame(results)
    
def update_book_info(book_id, book_name, author):
    query = "UPDATE BookInfo SET BookName = %s, Author = %s WHERE id = %s"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, (book_name, author, book_id))
    conn.commit()
    cursor.close()
    conn.close()

# Streamlit app
# Add a new book to the BookInfo table
def add_new_book(book_name, author,Instock, AvailableStock):
    query = "INSERT INTO BookInfo (BookName, Author, Instock, AvailableStock) VALUES (%s, %s, %s, %s)"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, (book_name, author, Instock, AvailableStock))
    conn.commit()
    cursor.close()
    conn.close()

def fetch_book_history(rfid_no):
    """
    Fetch all rows from BookHistory where RFidNo matches the given value.
    """
    try:
        # Establish connection to MySQL database
        connection = mysql.connector.connect(
            host=host,
            user=user,
            password=passwd,
            database=db_name
        )
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)
            # Query to fetch book history for the given RFidNo
            query = """
                SELECT 
                    bh.BookId, 
                    bi.BookName, 
                    bi.Author, 
                    bh.date AS IssueDate, 
                    bh.ReturnStatus, 
                    bh.ReturnDate 
                FROM 
                    BookHistory bh
                INNER JOIN 
                    BookInfo bi ON bh.BookId = bi.id
                WHERE 
                    bh.RFidNo = %s
            """
            cursor.execute(query, (rfid_no,))
            result = cursor.fetchall()
            return result
    except Error as e:
        st.error(f"Error connecting to the database: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
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
