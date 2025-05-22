# Coffee Shop Loyalty Program (Telegram Bot)

A simple loyalty program where customers collect points for each purchase. Once they accumulate enough points, they can redeem them for a free coffee or other rewards. The program allows customers to check their points, redeem rewards, and receive special offers directly through a Telegram bot interface.

## Concept

This loyalty program allows a small coffee shop to engage with customers through a Telegram bot, offering a seamless way to collect and redeem points for purchases. Customers can easily check their points and be notified of special offers or promotions.

## Features

1. **Register**: Customers can register for the loyalty program.
2. **Track Points**: Customers earn points for every purchase.
3. **Check Points**: Customers can check their current points using the bot.
4. **Redeem Rewards**: Customers can redeem points for rewards once they have collected enough.
5. **Notify**: The bot can send special offers and reward notifications to customers.
6. **Admin Panel**: Admins can add or reset points for users and manage the loyalty program.

## Flow

### Customer Interaction

- `/start`: Initiates the bot, registers the customer for the loyalty program, and explains how it works.
- `/my_points`: Allows the customer to check their current points.
- `/redeem`: Redeems points if the customer has enough for a reward (e.g., a free coffee).
- `/offers`: Displays any special offers or promotions available to the customer.

### Admin Interaction

- `/add_points <user_id> <points>`: Admins can add points to a specific user based on their purchase.
- `/reset_points <user_id>`: Resets a user’s points after redeeming a reward.

## How to Run

1. Clone the repository:
   ```bash
   git clone https://github.com/Measmonysuon/coffee_loyalty_program.git
   cd coffee_loyalty_program
   ```

2. **Set up Environment Variables:**

   Before running the bot, you need to set the following environment variables:

   *   `TELEGRAM_BOT_TOKEN`: Your Telegram Bot API token. You can get this from BotFather on Telegram.
   *   `TELEGRAM_ADMIN_ID`: The Telegram User ID of the administrator for this bot. This user ID will grant access to admin commands like `/add_points` and `/reset_points`. You can find your User ID by messaging a bot like `@userinfobot` on Telegram and retrieving your "Id".

   **On Linux/macOS:**
   ```bash
   export TELEGRAM_BOT_TOKEN="your_actual_bot_token_here"
   export TELEGRAM_ADMIN_ID="your_telegram_user_id_here"
   ```

   **On Windows (Command Prompt):**
   ```cmd
   set TELEGRAM_BOT_TOKEN="your_actual_bot_token_here"
   set TELEGRAM_ADMIN_ID="your_telegram_user_id_here"
   ```

   **On Windows (PowerShell):**
   ```powershell
   $env:TELEGRAM_BOT_TOKEN="your_actual_bot_token_here"
   $env:TELEGRAM_ADMIN_ID="your_telegram_user_id_here"
   ```
   *Note: For persistent storage of environment variables, you might need to add them to your shell's profile file (e.g., `.bashrc`, `.zshrc`, `config.fish`) or system environment settings.*

3. **Install Dependencies:**
   Make sure you have Python 3 installed. Then install the required Python library:
   ```bash
   pip install pyTelegramBotAPI
   ```

4. **Run the Bot:**
   ```bash
   python app.py
   ```
