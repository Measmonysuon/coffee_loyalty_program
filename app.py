import telebot

API_TOKEN = 'YOUR_BOT_API_TOKEN'

bot = telebot.TeleBot(API_TOKEN)

# Database placeholder (use real DB for production)
users = {}
rewards = {
    'free_coffee': 100,  # Points needed for a free coffee
}

# Command to start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    if user_id not in users:
        users[user_id] = 0  # Initialize user with 0 points
        bot.reply_to(message, f"Welcome to the Coffee Shop Loyalty Program! You're now registered and start with 0 points.")
    else:
        bot.reply_to(message, f"Welcome back! You have {users[user_id]} points.")

# Command to check points
@bot.message_handler(commands=['my_points'])
def check_points(message):
    user_id = message.chat.id
    points = users.get(user_id, 0)
    bot.reply_to(message, f"You currently have {points} points.")

# Command to redeem points
@bot.message_handler(commands=['redeem'])
def redeem_points(message):
    user_id = message.chat.id
    points = users.get(user_id, 0)

    if points >= rewards['free_coffee']:
        users[user_id] -= rewards['free_coffee']
        bot.reply_to(message, "Congrats! You've redeemed a free coffee.")
    else:
        bot.reply_to(message, f"Sorry, you need {rewards['free_coffee'] - points} more points to redeem a free coffee.")

# Admin command to add points
@bot.message_handler(commands=['add_points'])
def add_points(message):
    try:
        admin_id = message.chat.id
        if admin_id == YOUR_ADMIN_ID:  # Add admin check
            command, user_id, points = message.text.split()
            user_id = int(user_id)
            points = int(points)
            users[user_id] = users.get(user_id, 0) + points
            bot.reply_to(message, f"Added {points} points to user {user_id}.")
        else:
            bot.reply_to(message, "You are not authorized to perform this action.")
    except:
        bot.reply_to(message, "Invalid command format. Use /add_points <user_id> <points>.")

# Admin command to reset points after redemption
@bot.message_handler(commands=['reset_points'])
def reset_points(message):
    try:
        admin_id = message.chat.id
        if admin_id == YOUR_ADMIN_ID:
            command, user_id = message.text.split()
            user_id = int(user_id)
            users[user_id] = 0
            bot.reply_to(message, f"Points for user {user_id} have been reset.")
        else:
            bot.reply_to(message, "You are not authorized to perform this action.")
    except:
        bot.reply_to(message, "Invalid command format. Use /reset_points <user_id>.")

# Start polling
bot.polling()
