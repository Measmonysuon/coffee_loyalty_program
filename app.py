import telebot
import sqlite3
from datetime import datetime

API_TOKEN = 'YOUR_BOT_API_TOKEN'
bot = telebot.TeleBot(API_TOKEN)

# Connect to the database (create it if it doesn't exist)
conn = sqlite3.connect('loyalty_program.db', check_same_thread=False)
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        join_date TEXT,
        points INTEGER,
        last_point_update TEXT,
        last_reward_date TEXT,
        total_spent REAL,
        last_order_item TEXT
    )
''')
conn.commit()

# Rewards dictionary
rewards = {
    'free_coffee': 100,  # Points needed for a free coffee
}

# Register the user and initialize their data (/start: Initiates the bot, registers the customer for the loyalty program, and explains how it works.)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user is None:
        # Insert new user into the database
        join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('INSERT INTO users (user_id, join_date, points, total_spent) VALUES (?, ?, ?, ?)',
                       (user_id, join_date, 0, 0))
        conn.commit()
        bot.reply_to(message, f"Welcome to the Coffee Shop Loyalty Program! You're now registered and start with 0 points.")
    else:
        bot.reply_to(message, f"Welcome back! You have {user[2]} points.")

# Check current points (/my_points: Allows the customer to check their current points.)
@bot.message_handler(commands=['my_points'])
def check_points(message):
    user_id = message.chat.id
    cursor.execute('SELECT points FROM users WHERE user_id = ?', (user_id,))
    points = cursor.fetchone()
    
    if points:
        bot.reply_to(message, f"You currently have {points[0]} points.")
    else:
        bot.reply_to(message, "You are not registered yet. Use /start to register.")

# Redeem rewards (/redeem: Redeems points if the customer has enough for a reward (e.g., a free coffee).)

@bot.message_handler(commands=['redeem'])
def redeem_points(message):
    user_id = message.chat.id
    cursor.execute('SELECT points FROM users WHERE user_id = ?', (user_id,))
    points = cursor.fetchone()
    
    if points and points[0] >= rewards['free_coffee']:
        new_points = points[0] - rewards['free_coffee']
        last_reward_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('UPDATE users SET points = ?, last_reward_date = ? WHERE user_id = ?',
                       (new_points, last_reward_date, user_id))
        conn.commit()
        bot.reply_to(message, "Congrats! You've redeemed a free coffee.")
    elif points:
        bot.reply_to(message, f"Sorry, you need {rewards['free_coffee'] - points[0]} more points to redeem a free coffee.")
    else:
        bot.reply_to(message, "You are not registered yet. Use /start to register.")

# Admin command to add points and record spent amount and order details (/add_points <user_id> <points>: Admins can add points to a specific user based on their purchase.)
@bot.message_handler(commands=['add_points'])
def add_points(message):
    try:
        admin_id = message.chat.id
        if admin_id == YOUR_ADMIN_ID:  # Replace with the actual admin ID
            command, user_id, points, spent, order_item = message.text.split()
            user_id = int(user_id)
            points = int(points)
            spent = float(spent)
            
            cursor.execute('SELECT points, total_spent FROM users WHERE user_id = ?', (user_id,))
            user_data = cursor.fetchone()
            
            if user_data:
                new_points = user_data[0] + points
                new_spent = user_data[1] + spent
                last_point_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute('''UPDATE users 
                                  SET points = ?, last_point_update = ?, total_spent = ?, last_order_item = ? 
                                  WHERE user_id = ?''',
                               (new_points, last_point_update, new_spent, order_item, user_id))
                conn.commit()
                
                bot.reply_to(message, f"Added {points} points and recorded ${spent} spent for user {user_id}.")
            else:
                bot.reply_to(message, "User not found. Please ensure the user is registered.")
        else:
            bot.reply_to(message, "You are not authorized to perform this action.")
    except:
        bot.reply_to(message, "Invalid command format. Use /add_points <user_id> <points> <spent_amount> <order_item>.")

# Admin command to reset points after redemption (/reset_points <user_id>: Resets a user’s points after redeeming a reward.)
@bot.message_handler(commands=['reset_points'])
def reset_points(message):
    try:
        admin_id = message.chat.id
        if admin_id == YOUR_ADMIN_ID:  # Replace with the actual admin ID
            command, user_id = message.text.split()
            user_id = int(user_id)
            
            cursor.execute('SELECT points FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            
            if user:
                cursor.execute('UPDATE users SET points = ? WHERE user_id = ?', (0, user_id))
                conn.commit()
                bot.reply_to(message, f"Points for user {user_id} have been reset.")
            else:
                bot.reply_to(message, "User not found.")
        else:
            bot.reply_to(message, "You are not authorized to perform this action.")
    except:
        bot.reply_to(message, "Invalid command format. Use /reset_points <user_id>.")

# Start polling
bot.polling()
