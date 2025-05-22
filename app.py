import telebot
import sqlite3
from datetime import datetime
import functools # Added for wraps
import os # For environment variables
import sys # For sys.exit

# --- Configuration ---
API_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ADMIN_ID_STR = os.environ.get('TELEGRAM_ADMIN_ID')

# --- Constants ---
# Table Names
TABLE_USERS = 'users'

# Column Names for 'users' table
COLUMN_USER_ID = 'user_id'
COLUMN_JOIN_DATE = 'join_date'
COLUMN_POINTS = 'points'
COLUMN_LAST_POINT_UPDATE = 'last_point_update'
COLUMN_LAST_REWARD_DATE = 'last_reward_date'
COLUMN_TOTAL_SPENT = 'total_spent'
COLUMN_LAST_ORDER_ITEM = 'last_order_item'

# Reward Keys
REWARD_KEY_FREE_COFFEE = 'free_coffee'

# Reward Points
POINTS_FOR_FREE_COFFEE = 100

if API_TOKEN is None:
    print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
    sys.exit(1)

if ADMIN_ID_STR is None:
    print("Error: TELEGRAM_ADMIN_ID environment variable not set.")
    sys.exit(1)

try:
    ADMIN_ID_INT = int(ADMIN_ID_STR)
except ValueError:
    print(f"Error: TELEGRAM_ADMIN_ID ('{ADMIN_ID_STR}') is not a valid integer.")
    sys.exit(1)

bot = telebot.TeleBot(API_TOKEN)

# Connect to the database (create it if it doesn't exist)
conn = sqlite3.connect('loyalty_program.db', check_same_thread=False)
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS {TABLE_USERS} (
        {COLUMN_USER_ID} INTEGER PRIMARY KEY,
        {COLUMN_JOIN_DATE} TEXT,
        {COLUMN_POINTS} INTEGER,
        {COLUMN_LAST_POINT_UPDATE} TEXT,
        {COLUMN_LAST_REWARD_DATE} TEXT,
        {COLUMN_TOTAL_SPENT} REAL,
        {COLUMN_LAST_ORDER_ITEM} TEXT
    )
''')
conn.commit()

# Rewards dictionary
rewards = {
    REWARD_KEY_FREE_COFFEE: POINTS_FOR_FREE_COFFEE,
}

# Decorators

def ensure_registered(func):
    @functools.wraps(func)
    def wrapper(message):
        user_id = message.chat.id
        try:
            cursor.execute(f'SELECT {COLUMN_USER_ID} FROM {TABLE_USERS} WHERE {COLUMN_USER_ID} = ?', (user_id,))
            user = cursor.fetchone()
            if user is None:
                bot.reply_to(message, "You are not registered yet. Use /start to register.")
                return None # Explicitly return None
            return func(message)
        except sqlite3.Error as e:
            print(f"Database error in ensure_registered for user {user_id}: {e}")
            bot.reply_to(message, "A database error occurred while checking your registration. Please try again later.")
            return None # Explicitly return None
        except Exception as e:
            print(f"Unexpected error in ensure_registered for user {user_id}: {e}")
            bot.reply_to(message, "An unexpected error occurred. Please try again later.")
            return None # Explicitly return None
    return wrapper

def admin_required(func):
    @functools.wraps(func)
    def wrapper(message):
        user_chat_id = message.chat.id
        if user_chat_id != ADMIN_ID_INT:
            bot.reply_to(message, "You are not authorized to perform this action.")
            return
        return func(message)
    return wrapper

# Register the user and initialize their data (/start: Initiates the bot, registers the customer for the loyalty program, and explains how it works.)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    # Selecting specific columns for clarity, even if '*' was used before.
    # User[0] = user_id, User[1] = points (based on the order in SELECT)
    cursor.execute(f'SELECT {COLUMN_USER_ID}, {COLUMN_POINTS} FROM {TABLE_USERS} WHERE {COLUMN_USER_ID} = ?', (user_id,))
    user = cursor.fetchone() 
    
    if user is None:
        try:
            # Insert new user into the database
            join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(f'''INSERT INTO {TABLE_USERS} 
                               ({COLUMN_USER_ID}, {COLUMN_JOIN_DATE}, {COLUMN_POINTS}, {COLUMN_TOTAL_SPENT}) 
                               VALUES (?, ?, ?, ?)''',
                           (user_id, join_date, 0, 0))
            conn.commit()
            bot.reply_to(message, f"Welcome to the Coffee Shop Loyalty Program! You're now registered and start with 0 points.")
        except sqlite3.Error as e:
            print(f"Database error in send_welcome for new user {user_id}: {e}")
            bot.reply_to(message, "A database error occurred while registering you. Please try /start again later.")
        except Exception as e:
            print(f"Unexpected error in send_welcome for new user {user_id}: {e}")
            bot.reply_to(message, "An unexpected error occurred while registering you. Please try /start again.")
    else:
        # user[1] is points based on 'SELECT user_id, points ...'
        bot.reply_to(message, f"Welcome back! You have {user[1]} points.")

# Check current points (/my_points: Allows the customer to check their current points.)
@bot.message_handler(commands=['my_points'])
@ensure_registered
def check_points(message):
    user_id = message.chat.id
    try:
        # User existence is already checked by the decorator.
        cursor.execute(f'SELECT {COLUMN_POINTS} FROM {TABLE_USERS} WHERE {COLUMN_USER_ID} = ?', (user_id,))
        points_data = cursor.fetchone()
        
        if points_data:
            bot.reply_to(message, f"You currently have {points_data[0]} points.")
        else:
            bot.reply_to(message, "Could not retrieve your points. You might have been unregistered.")
    except sqlite3.Error as e:
        print(f"Database error in check_points for user {user_id}: {e}")
        bot.reply_to(message, "A database error occurred while checking your points. Please try again later.")
    except Exception as e:
        print(f"Unexpected error in check_points for user {user_id}: {e}")
        bot.reply_to(message, "An unexpected error occurred while checking your points.")

# Redeem rewards (/redeem: Redeems points if the customer has enough for a reward (e.g., a free coffee).)
@bot.message_handler(commands=['redeem'])
@ensure_registered
def redeem_points(message):
    user_id = message.chat.id
    try:
        # User existence is already checked by the decorator.
        cursor.execute(f'SELECT {COLUMN_POINTS} FROM {TABLE_USERS} WHERE {COLUMN_USER_ID} = ?', (user_id,))
        points_data = cursor.fetchone()
        
        if points_data is None:
            bot.reply_to(message, "Could not retrieve your points details. You might have been unregistered.")
            return

        current_points_value = points_data[0]
        if current_points_value >= rewards[REWARD_KEY_FREE_COFFEE]:
            new_points = current_points_value - rewards[REWARD_KEY_FREE_COFFEE]
            last_reward_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(f'''UPDATE {TABLE_USERS} 
                               SET {COLUMN_POINTS} = ?, {COLUMN_LAST_REWARD_DATE} = ? 
                               WHERE {COLUMN_USER_ID} = ?''',
                           (new_points, last_reward_date, user_id))
            conn.commit()
            bot.reply_to(message, "Congrats! You've redeemed a free coffee.")
        else: # User exists but not enough points
            bot.reply_to(message, f"Sorry, you need {rewards[REWARD_KEY_FREE_COFFEE] - current_points_value} more points to redeem a free coffee.")
    except sqlite3.Error as e:
        print(f"Database error in redeem_points for user {user_id}: {e}")
        bot.reply_to(message, "A database error occurred while redeeming points. Please try again later.")
        # Optionally, consider if a transaction rollback is needed if multiple DB ops were involved. Here, it's one select then one update.
        # If update fails, points are not deducted, which is acceptable.
    except Exception as e:
        print(f"Unexpected error in redeem_points for user {user_id}: {e}")
        bot.reply_to(message, "An unexpected error occurred while redeeming points.")

# Admin command to add points and record spent amount and order details (/add_points <user_id> <points>: Admins can add points to a specific user based on their purchase.)
@bot.message_handler(commands=['add_points'])
@admin_required
def add_points(message):
    try:
        # Admin authorization is checked by decorator. If it failed, this won't run.
        parts = message.text.split(maxsplit=4) # command, user_id, points, spent, order_item (order_item can have spaces)
        if len(parts) != 5:
            bot.reply_to(message, "Invalid command format. Use /add_points <user_id> <points> <spent_amount> <order_item>.")
            return

        command, user_id_str, points_str, spent_str, order_item = parts
        
        user_id = int(user_id_str)
        points_to_add = int(points_str)
        spent = float(spent_str)
        
        # Fetch current user data
        # user_data[0] = points, user_data[1] = total_spent
        cursor.execute(f'SELECT {COLUMN_POINTS}, {COLUMN_TOTAL_SPENT} FROM {TABLE_USERS} WHERE {COLUMN_USER_ID} = ?', (user_id,))
        user_data = cursor.fetchone()
        
        if user_data:
            current_db_points = user_data[0]
            current_db_total_spent = user_data[1]
            new_total_points = current_db_points + points_to_add
            new_total_spent = current_db_total_spent + spent
            last_point_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Update user data
            cursor.execute(f'''UPDATE {TABLE_USERS} 
                              SET {COLUMN_POINTS} = ?, {COLUMN_LAST_POINT_UPDATE} = ?, 
                                  {COLUMN_TOTAL_SPENT} = ?, {COLUMN_LAST_ORDER_ITEM} = ? 
                              WHERE {COLUMN_USER_ID} = ?''',
                           (new_total_points, last_point_update, new_total_spent, order_item, user_id))
            conn.commit()
            
            bot.reply_to(message, f"Added {points_to_add} points and recorded ${spent:.2f} spent for user {user_id}.")
        else:
            bot.reply_to(message, f"User {user_id} not found. Please ensure the user is registered.")
            
    except ValueError:
        bot.reply_to(message, "Invalid command format or data type. Expected: /add_points <user_id:integer> <points:integer> <spent:number> <order_item:text>.")
    except sqlite3.Error as e:
        print(f"Database error in add_points: {e}")
        bot.reply_to(message, "A database error occurred while adding points. Please try again later.")
    except Exception as e:
        print(f"Unexpected error in add_points: {e}")
        bot.reply_to(message, "An unexpected error occurred while adding points.")


# Admin command to reset points after redemption (/reset_points <user_id>: Resets a user’s points after redeeming a reward.)
@bot.message_handler(commands=['reset_points'])
@admin_required
def reset_points(message):
    try:
        # Admin authorization is checked by decorator.
        parts = message.text.split()
        if len(parts) != 2: # command, user_id
            bot.reply_to(message, "Invalid command format. Use /reset_points <user_id>.")
            return

        command, user_id_str = parts
        user_id = int(user_id_str)
        
        # Check if user exists before attempting update
        cursor.execute(f'SELECT {COLUMN_USER_ID} FROM {TABLE_USERS} WHERE {COLUMN_USER_ID} = ?', (user_id,))
        user = cursor.fetchone()
        
        if user:
            cursor.execute(f'UPDATE {TABLE_USERS} SET {COLUMN_POINTS} = ? WHERE {COLUMN_USER_ID} = ?', (0, user_id))
            conn.commit()
            bot.reply_to(message, f"Points for user {user_id} have been reset to 0.")
        else:
            bot.reply_to(message, f"User {user_id} not found.")
            
    except ValueError:
        bot.reply_to(message, "Invalid command format or user_id. Expected: /reset_points <user_id:integer>.")
    except sqlite3.Error as e:
        print(f"Database error in reset_points for user {user_id_str if 'user_id_str' in locals() else 'unknown'}: {e}")
        bot.reply_to(message, "A database error occurred while resetting points. Please try again later.")
    except Exception as e:
        print(f"Unexpected error in reset_points for user {user_id_str if 'user_id_str' in locals() else 'unknown'}: {e}")
        bot.reply_to(message, "An unexpected error occurred while resetting points.")

# Start polling
if __name__ == '__main__':
    try:
        print("Bot is starting...")
        bot.polling(none_stop=True) # none_stop=True to keep polling
    except Exception as e:
        print(f"Bot polling error: {e}")
    finally:
        if 'conn' in globals() and conn:
            conn.close()
            print("Database connection closed.")
        print("Bot has stopped.")
