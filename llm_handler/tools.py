from google_sheet_handler import save_order_to_sheet, get_menu_text_from_sheet, get_menu_from_sheet
from langchain_core.tools import tool
import json

@tool
def get_menu() -> str:
    """Retrieve the hotel menu with items, prices, and descriptions."""
    return get_menu_text_from_sheet()

@tool
def place_order(customer_name: str, phone_number: str, room_number: str,
                items: str, special_instructions: str = "") -> str:
    """
    Place an order for the customer.

    Args:
        customer_name: Customer's name
        phone_number: Customer's phone number
        room_number: Hotel room number
        items: JSON string of ordered items with quantities
        special_instructions: Any special requests
    """
    try:
        print(customer_name, phone_number, room_number, items, special_instructions)
        items_list = json.loads(items)
        print(items_list)

        # Calculate total (in production, fetch prices from sheet)
        total = 0
        menu_data = get_menu_from_sheet()
        menu_dict = {item['Item'].lower(): item['Price'] for item in menu_data}
        print("menu_dict:")
        print(menu_dict)
        for item in items_list:
            item_name = item['item'].lower()
            quantity = item['quantity']
            if item_name in menu_dict:
                total += menu_dict[item_name] * quantity


        order_details = {
            "customer_name": customer_name,
            "phone_number": phone_number,
            "room_number": room_number,
            "items": items_list,
            "total_amount": total,
            "special_instructions": special_instructions
        }

        success = save_order_to_sheet(order_details)

        if success:
            order_summary = f"✅ Order placed successfully!\n\n"
            order_summary += f"Customer: {customer_name}\n"
            order_summary += f"Room: {room_number}\n"
            order_summary += f"Items:\n"
            for item in items_list:
                order_summary += f"  - {item['quantity']}x {item['item']}\n"
            if total > 0:
                order_summary += f"\nTotal: ₹{total}\n"
            if special_instructions:
                order_summary += f"Special Instructions: {special_instructions}\n"
            order_summary += f"\nYour order will be delivered shortly!"
            return order_summary
        else:
            return "❌ Failed to place order. Please try again or contact support."

    except Exception as e:
        return f"Error placing order: {str(e)}"

@tool
def get_item_details(item_name: str) -> str:
    """Get detailed information about a specific menu item."""
    try:
        menu_data = get_menu_from_sheet()

        for item in menu_data:
            if item_name.lower() in item['Item'].lower():
                details = f"*{item['Item']}*\n"
                details += f"Price: ₹{item['Price']}\n"
                return details

        return f"Item '{item_name}' not found in menu."
    except Exception as e:
        return f"Error: {str(e)}"