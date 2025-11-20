import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

GOOGLE_SHEETS_CREDS_FILE = "credentials.json"  # Path to your Google service account JSON
MENU_SHEET_NAME = "order_management_system"  # Name of your Google Sheet for menu
# ORDERS_SHEET_NAME = "Hotel Orders"

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_CREDS_FILE, scope)
    client = gspread.authorize(creds)
except:
    print("Warning: Google Sheets credentials not found. Please add credentials.json")
    client = None

def get_menu():
    if not client:
        return "Unable to fetch menu. Please contact support."

    try:
        sheet = client.open(MENU_SHEET_NAME).sheet1
        menu_data = sheet.get_all_records()
        return menu_data
    except Exception as e:
        return f"Error fetching menu: {str(e)}"

def get_menu_text_from_sheet():
    """Retrieve menu from Google Sheets"""
    if not client:
        return "Unable to fetch menu. Please contact support."

    try:
        menu_data = get_menu()

        menu_text = "🍽️ **HOTEL MENU** 🍽️\n\n"
        for item in menu_data:
            menu_text += f"📌 *{item['Item']}*\n"
            menu_text += f"   ₹{item['Price']} \n"

        return menu_text
    except Exception as e:
        return f"Error fetching menu: {str(e)}"

def save_order_to_sheet():
    """Save order to Google Sheets"""
    if not client:
        return False

    try:
        sheet = client.open(MENU_SHEET_NAME).get_worksheet(1)

        # Prepare order row
        # order_row = [
        #     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        #     order_details.get("customer_name", ""),
        #     order_details.get("phone_number", ""),
        #     order_details.get("room_number", ""),
        #     json.dumps(order_details.get("items", [])),
        #     order_details.get("total_amount", 0),
        #     order_details.get("special_instructions", ""),
        #     "Pending"
        # ]

        sheet.append_row([1,2,3,4])
        return True
    except Exception as e:
        print(f"Error saving order: {str(e)}")
        return False

if __name__ == "__main__":
    print(save_order_to_sheet())