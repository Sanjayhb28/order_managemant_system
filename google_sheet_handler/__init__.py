

def get_menu_from_sheet():
    """Retrieve menu from Google Sheets"""
    if not client:
        return "Unable to fetch menu. Please contact support."

    try:
        sheet = client.open(MENU_SHEET_NAME).sheet1
        menu_data = sheet.get_all_records()

        menu_text = "🍽️ **HOTEL MENU** 🍽️\n\n"
        for item in menu_data:
            menu_text += f"📌 *{item['Item']}*\n"
            menu_text += f"   ₹{item['Price']} | {item['Category']}\n"
            if 'Description' in item and item['Description']:
                menu_text += f"   {item['Description']}\n"
            menu_text += "\n"

        return menu_text
    except Exception as e:
        return f"Error fetching menu: {str(e)}"