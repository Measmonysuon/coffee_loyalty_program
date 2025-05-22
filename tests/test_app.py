import unittest
from unittest.mock import patch, MagicMock, ANY
import os
import sys

# Ensure the app directory is in the Python path
# This allows importing 'app' from the 'tests' directory
# Adjust the path .. as per your project structure
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Mock environment variables before importing app ---
# These must be set before 'app.py' is imported because it reads them at load time.
MOCKED_ADMIN_ID = '123456789'
MOCKED_BOT_TOKEN = 'fake_token'

# Use a dictionary for os.environ patching
mock_env = {
    'TELEGRAM_ADMIN_ID': MOCKED_ADMIN_ID,
    'TELEGRAM_BOT_TOKEN': MOCKED_BOT_TOKEN
}

@patch.dict(os.environ, mock_env, clear=True)
class TestAppLogic(unittest.TestCase):

    @classmethod
    @patch.dict(os.environ, mock_env, clear=True)
    def setUpClass(cls):
        # Ensure app is imported *after* os.environ is patched for all tests in this class
        # and also after sys.path is manipulated.
        global app
        import app
        # Now app.ADMIN_ID_INT and app.API_TOKEN are set based on our mocks

    def setUp(self):
        """Set up mocks for each test method."""
        # Patch app.bot, app.conn, and app.cursor
        # These are module-level attributes in app.py
        
        # Patch for app.bot (TeleBot instance)
        self.bot_patcher = patch('app.bot', spec=True)
        self.mock_bot = self.bot_patcher.start()
        self.addCleanup(self.bot_patcher.stop)

        # Patch for app.conn (sqlite3 connection)
        # We don't need to mock conn itself usually, but the cursor it produces.
        # However, if app.conn.commit or app.conn.close are called directly, mock them.
        self.conn_patcher = patch('app.conn')
        self.mock_conn = self.conn_patcher.start()
        self.addCleanup(self.conn_patcher.stop)

        # Patch for app.cursor (sqlite3 cursor)
        self.cursor_patcher = patch('app.cursor')
        self.mock_cursor = self.cursor_patcher.start()
        self.addCleanup(self.cursor_patcher.stop)
        
        # Configure mock_conn to return mock_cursor when cursor() is called
        self.mock_conn.cursor.return_value = self.mock_cursor

        # Common mock for message object
        self.mock_message = MagicMock()
        self.mock_message.chat.id = int(MOCKED_ADMIN_ID) # Default to admin for admin commands

    # --- Test Cases ---

    def test_send_welcome_new_user(self):
        """Test send_welcome for a new user."""
        self.mock_message.chat.id = 999 # Non-admin, new user
        # Simulate user not found by the first SELECT in send_welcome
        self.mock_cursor.fetchone.return_value = None 

        app.send_welcome(self.mock_message)

        # Check if INSERT query was called for the new user
        # The first call to execute is 'SELECT * FROM users...'
        # The second call should be 'INSERT INTO users...'
        insert_query_found = False
        for call_args in self.mock_cursor.execute.call_args_list:
            query = call_args[0][0] # First argument of the first positional argument
            if "INSERT INTO users" in query or f"INSERT INTO {app.TABLE_USERS}" in query :
                insert_query_found = True
                # Check that initial points and total_spent are 0
                args = call_args[0][1] # Second argument of the first positional argument (the tuple of values)
                self.assertEqual(args[1], 0) # points at index 2 in DB schema, but 1 in (user_id, join_date, points, total_spent) if join_date is made by strftime
                                             # Based on current app.py: (user_id, join_date, 0, 0) -> points is args[2], spent is args[3]
                                             # Query: INSERT INTO users (user_id, join_date, points, total_spent) VALUES (?, ?, ?, ?)
                                             # args = (user_id, join_date_str, 0, 0) -> points = args[2], total_spent = args[3]
                self.assertEqual(args[2], 0) # points
                self.assertEqual(args[3], 0) # total_spent
                break
        self.assertTrue(insert_query_found, "INSERT query not found for new user.")
        
        self.mock_conn.commit.assert_called_once()
        self.mock_bot.reply_to.assert_called_once_with(
            self.mock_message,
            f"Welcome to the Coffee Shop Loyalty Program! You're now registered and start with 0 points."
        )

    def test_send_welcome_existing_user(self):
        """Test send_welcome for an existing user."""
        user_chat_id = 888
        existing_points = 50
        self.mock_message.chat.id = user_chat_id
        # Simulate user found: (user_id, points) - based on app.py's SELECT query in send_welcome
        self.mock_cursor.fetchone.return_value = (user_chat_id, existing_points) 

        app.send_welcome(self.mock_message)

        # Check that INSERT query was NOT called
        insert_query_found = False
        for call_args in self.mock_cursor.execute.call_args_list:
            query = call_args[0][0]
            if "INSERT INTO users" in query or f"INSERT INTO {app.TABLE_USERS}" in query:
                insert_query_found = True
                break
        self.assertFalse(insert_query_found, "INSERT query should not be called for existing user.")
        
        self.mock_conn.commit.assert_not_called() # No commit if no insert
        self.mock_bot.reply_to.assert_called_once_with(
            self.mock_message,
            f"Welcome back! You have {existing_points} points."
        )

    def test_add_points_logic(self):
        """Test the core logic of adding points."""
        admin_chat_id = int(MOCKED_ADMIN_ID)
        target_user_id = 777
        initial_points = 10
        initial_spent = 50.0
        points_to_add = 5
        spent_amount = 25.5
        order_item = "Latte"

        self.mock_message.chat.id = admin_chat_id # Message from admin
        self.mock_message.text = f"/add_points {target_user_id} {points_to_add} {spent_amount} {order_item}"

        # Decorator admin_required passes.
        # First DB call in add_points: SELECT points, total_spent FROM users...
        self.mock_cursor.fetchone.return_value = (initial_points, initial_spent)

        app.add_points(self.mock_message)
        
        # Check the UPDATE query
        # Expected new_total_points = initial_points + points_to_add = 15
        # Expected new_total_spent = initial_spent + spent_amount = 75.5
        expected_new_points = initial_points + points_to_add
        expected_new_spent = initial_spent + spent_amount

        update_query_found = False
        for call_args in self.mock_cursor.execute.call_args_list:
            query = call_args[0][0]
            if "UPDATE users SET" in query or f"UPDATE {app.TABLE_USERS} SET" in query:
                update_query_found = True
                args = call_args[0][1] # Tuple of values for the UPDATE query
                # Query: UPDATE users SET points = ?, last_point_update = ?, total_spent = ?, last_order_item = ? WHERE user_id = ?
                # args = (new_total_points, last_point_update_str, new_total_spent, order_item, target_user_id)
                self.assertEqual(args[0], expected_new_points)  # New points
                self.assertIsInstance(args[1], str)            # last_point_update (date string)
                self.assertEqual(args[2], expected_new_spent) # New total_spent
                self.assertEqual(args[3], order_item)         # order_item
                self.assertEqual(args[4], target_user_id)     # user_id for WHERE clause
                break
        self.assertTrue(update_query_found, "UPDATE query not found in add_points.")

        self.mock_conn.commit.assert_called_once()
        self.mock_bot.reply_to.assert_called_once_with(
            self.mock_message,
            f"Added {points_to_add} points and recorded ${spent_amount:.2f} spent for user {target_user_id}."
        )

    def test_redeem_points_sufficient(self):
        """Test redeem_points when user has sufficient points."""
        user_chat_id = 666
        self.mock_message.chat.id = user_chat_id
        
        # ensure_registered decorator's DB call:
        # First fetchone is for the decorator to confirm user exists.
        # Second fetchone is for the redeem_points function itself.
        self.mock_cursor.fetchone.side_effect = [
            (user_chat_id,),  # Decorator: user exists
            (app.POINTS_FOR_FREE_COFFEE + 50,) # redeem_points: user has enough points
        ]

        app.redeem_points(self.mock_message)

        # Check the UPDATE query for point deduction
        expected_new_points = 50 # (POINTS_FOR_FREE_COFFEE + 50) - POINTS_FOR_FREE_COFFEE
        update_query_found = False
        for call_args in self.mock_cursor.execute.call_args_list:
            query = call_args[0][0]
            # Query from ensure_registered: SELECT user_id FROM users WHERE user_id = ?
            # Query from redeem_points: SELECT points FROM users WHERE user_id = ?
            # Query from redeem_points (update): UPDATE users SET points = ?, last_reward_date = ? WHERE user_id = ?
            if f"UPDATE {app.TABLE_USERS} SET {app.COLUMN_POINTS}" in query:
                update_query_found = True
                args = call_args[0][1]
                self.assertEqual(args[0], expected_new_points) # New points
                self.assertIsInstance(args[1], str)           # last_reward_date
                self.assertEqual(args[2], user_chat_id)       # user_id for WHERE
                break
        self.assertTrue(update_query_found, "UPDATE query not found in redeem_points (sufficient).")
        
        self.mock_conn.commit.assert_called_once()
        self.mock_bot.reply_to.assert_called_once_with(
            self.mock_message,
            "Congrats! You've redeemed a free coffee."
        )

    def test_redeem_points_insufficient(self):
        """Test redeem_points when user has insufficient points."""
        user_chat_id = 555
        self.mock_message.chat.id = user_chat_id
        insufficient_points = app.POINTS_FOR_FREE_COFFEE - 10

        # ensure_registered decorator's DB call:
        self.mock_cursor.fetchone.side_effect = [
            (user_chat_id,),      # Decorator: user exists
            (insufficient_points,) # redeem_points: user has insufficient points
        ]

        app.redeem_points(self.mock_message)

        # Check that UPDATE query for point deduction was NOT called
        update_query_found = False
        for call_args in self.mock_cursor.execute.call_args_list:
            query = call_args[0][0]
            if f"UPDATE {app.TABLE_USERS} SET {app.COLUMN_POINTS}" in query:
                update_query_found = True
                break
        self.assertFalse(update_query_found, "UPDATE query should not be called for insufficient points.")
        
        self.mock_conn.commit.assert_not_called() # No commit if no update
        self.mock_bot.reply_to.assert_called_once_with(
            self.mock_message,
            f"Sorry, you need {app.POINTS_FOR_FREE_COFFEE - insufficient_points} more points to redeem a free coffee."
        )

if __name__ == '__main__':
    unittest.main()
