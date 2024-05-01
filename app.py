import csv
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters
from config import TOKEN

# import logging
# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO
# )

# Define file paths for CSV files
ADMINS_FILE = 'db_admins.csv'
USER_CAR_DB_FILE = 'db_user_car.csv'
QUEUE_FILE = 'db_queue.csv'

# Define the list of carwash options
CARWASH = ["BestWash", "CleanWash", "Goody"]


# Async function to display buttons
async def show_buttons(update: Update, context: CallbackContext) -> None:
    print("show_buttons")
    buttons = [
        ['CHECK QUEUE LENGTH'],
        ['JOIN QUEUE'],
        ['ADD ANOTHER PLATE NUMBER'],
        ['DELETE PLATE NUMBER']
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
    context.user_data['waiting_for'] = 'option_choice'
    await update.message.reply_text("Choose an option:", reply_markup=reply_markup)


async def enter_leave_buttons(update: Update, context: CallbackContext) -> None:
    print("show_buttons")
    buttons = [
        ["I'm ENTERING"],
        ["I'm LEAVING"]
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
    context.user_data['waiting_for'] = 'enter_leave_choice'
    await update.message.reply_text("If you are entering or leaving please press one of the buttons below:",
                                    reply_markup=reply_markup)


# Function to check if user exists in cars_db
def user_exists(user_id):
    print("user_exists")
    with open(USER_CAR_DB_FILE, 'r') as file:
        reader = csv.reader(file)
        all_rows = [row for row in reader if row]
        print(all_rows)
        for row in all_rows:
            if row[0] == str(user_id) and row[3] == 'ACTIVE':
                return True
    return False


# Async function to handle /start command
async def start(update: Update, context: CallbackContext) -> None:
    print("start")

    user_id = update.message.from_user.id
    if not user_exists(user_id):
        await update.message.reply_text("Welcome! Please provide your car plate number.")
        context.user_data['waiting_for'] = "plate_number"  # Set the flag to indicate awaiting plate number
    else:
        await update.message.reply_text("Welcome back!")
        await show_buttons(update, context)


# Async function to handle receiving plate number with validation and formatting
async def record_plate_num(update: Update, context: CallbackContext) -> None:
    print("record_plate_num")
    user_id = update.message.from_user.id

    plate_number = update.message.text.upper().replace(" ", "")  # Remove spaces and capitalize letters
    if len(plate_number) < 5:
        await update.message.reply_text("Please resend a correct full plate number.")
        # 'waiting_for' remains 'plate_number'
    else:
        registration_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(USER_CAR_DB_FILE, 'a') as file:
            writer = csv.writer(file)
            writer.writerow([user_id, registration_datetime, plate_number, 'ACTIVE'])
        await update.message.reply_text("Plate number received and recorded!")
        await show_buttons(update, context)
        # context.user_data['waiting_for'] = ''


# Function to handle JOIN QUEUE button press
async def app_flow(update: Update, context: CallbackContext) -> int:
    print("app_flow")
    user_id = update.message.from_user.id
    user_text = update.message.text
    print('waiting_for: ', context.user_data.get('waiting_for'))
    waiting_for = context.user_data.get('waiting_for', '')

    if waiting_for == 'plate_number':
        print('waiting for plate_number')
        await record_plate_num(update, context)

    if user_text == 'JOIN QUEUE':
        reply_markup = ReplyKeyboardMarkup([CARWASH], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Please choose a carwash center:", reply_markup=reply_markup)
        context.user_data['waiting_for'] = "carwash"
    elif user_text == 'CHECK QUEUE LENGTH':
        print('CHECK QUEUE LENGTH')
        # Send the list of carwash centers to the user
        reply_markup = ReplyKeyboardMarkup([CARWASH], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Please choose a carwash center to check queue length:",
                                        reply_markup=reply_markup)
        context.user_data['waiting_for'] = 'check_queue_length'

    elif waiting_for == 'check_queue_length':
        # Check if the user's message corresponds to a valid carwash center
        if user_text in CARWASH:
            carwash_name = user_text
            # Count the number of cars in the queue with status "IN QUEUE" for the selected carwash
            with open(QUEUE_FILE, 'r') as file:
                reader = csv.reader(file)
                all_rows = [row for row in reader if row]
                queue_length = sum(1 for row in all_rows if row[1] == carwash_name and row[4] == "IN QUEUE")
            # Reply to the user with the queue length
            await update.message.reply_text(f"The queue length at {carwash_name} is {queue_length}.")
            # context.user_data['waiting_for'] = ''  # Reset the waiting flag
            await show_buttons(update, context)
        else:
            # If the user's message does not correspond to a valid carwash center, prompt them to choose again
            reply_markup = ReplyKeyboardMarkup([CARWASH], one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("Please choose a valid carwash center.", reply_markup=reply_markup)

    elif user_text == 'ADD ANOTHER PLATE NUMBER':
        print('ADD ANOTHER PLATE NUMBER')
        await update.message.reply_text("Please provide another car plate number.")
        context.user_data['waiting_for'] = "plate_number"

    elif user_text == 'DELETE PLATE NUMBER':
        print('DELETE PLATE NUMBER')
        await show_active_plate_numbers(update, context)
        context.user_data['waiting_for'] = 'delete_plate_number'

    elif waiting_for == 'delete_plate_number':
        plate_number_to_delete = update.message.text.upper().replace(" ", "")  # Normalize the input
        user_id = update.message.from_user.id

        # Update the status to 'DELETED' for the selected plate number
        with open(USER_CAR_DB_FILE, 'r+') as file:
            reader = csv.reader(file)
            all_rows = [row for row in reader if row]
            wrong_plate = True  # if loop below is never True, then meaning wrong plate num entered
            for row in all_rows:
                if row[0] == str(user_id) and row[2] == plate_number_to_delete and row[3] == 'ACTIVE':
                    # Update the status to 'DELETED' for the selected plate number
                    row[3] = 'DELETED'
                    file.seek(0)
                    writer = csv.writer(file)
                    writer.writerows(all_rows)
                    await update.message.reply_text(f"Plate number {plate_number_to_delete} has been deleted.")

                    wrong_plate = False
                    break
            if wrong_plate:
                # If the plate number entered is not valid, prompt the user to try again
                await update.message.reply_text("Wrong plate number, try again.")
                await show_active_plate_numbers(update, context)

        if not wrong_plate:
            if user_exists(user_id):
                print('user has cars')
                # Otherwise, show the buttons again
                await show_buttons(update, context)
            else:
                print('no cars')
                # If the user has no more active plate numbers, prompt for a new plate number
                await update.message.reply_text(
                    "Please provide your car plate number to continue using the bot")
                context.user_data['waiting_for'] = "plate_number"

    elif waiting_for == "carwash":
        selection = update.message.text.strip()  # Normalize the input
        if selection in CARWASH:
            context.user_data['carwash_name'] = selection  # Store the valid carwash selection
            with open(USER_CAR_DB_FILE, 'r') as file:
                reader = csv.reader(file)
                all_rows = [row for row in reader if
                            row]  # Important to save the reader as a list, otherwise next use will result in ""
                print(all_rows)
                user_records = [row for row in all_rows if
                                row[0] == str(user_id) and row[3] == 'ACTIVE' and len(row) > 3]
            context.user_data['user_records'] = user_records  # Store user records in context

            if len(user_records) > 1:
                buttons = [[KeyboardButton(record[2])] for record in user_records]  # Create buttons for each car plate
                reply_markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
                await update.message.reply_text("Choose a car plate:", reply_markup=reply_markup)
                context.user_data['waiting_for'] = "add_to_queue"
            else:
                # Directly record if only one plate
                await record_queue_entry(update, user_id, context.user_data['carwash_name'], user_records[0][2], context)
                context.user_data['waiting_for'] = ""
        else:
            # Carwash does not exist
            reply_markup = ReplyKeyboardMarkup([CARWASH], one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("Invalid input. Please choose a valid carwash center:",
                                            reply_markup=reply_markup)
            # we don't change the 'waiting_for' marker, since still expecting valid carwash from user

    elif waiting_for == "add_to_queue":
        plate_number = update.message.text.upper().replace(" ", "")  # Normalize the input for comparison
        user_plate_numbers = context.user_data['user_records']
        user_id = update.message.from_user.id

        # Check if the entered plate number is in the user's records
        if any(record[2] == plate_number for record in user_plate_numbers):
            # If it's a valid plate number, proceed to record the queue entry
            await record_queue_entry(update, user_id, context.user_data['carwash_name'], plate_number)
            context.user_data['waiting_for'] = ""  # Reset the waiting flag
        else:
            # If it's not a valid plate number, prompt the user to choose from their plates
            buttons = [[KeyboardButton(record[2])] for record in user_plate_numbers]
            reply_markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("Please choose a valid plate number from your list:",
                                            reply_markup=reply_markup)

    # when the user sends something instead of pressing a button from show_buttons
    elif waiting_for == 'option_choice':
        await show_buttons(update, context)

    elif user_text == "I'm ENTERING":
        print("I'm ENTERING pressed")
        await update.message.reply_text("Please provide another car plate number.")
        context.user_data['waiting_for'] = "plate_number"

    if waiting_for == '':
        await update.message.reply_text("I don't understand this, please press /start")


async def show_active_plate_numbers(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    with open(USER_CAR_DB_FILE, 'r') as file:
        reader = csv.reader(file)
        all_rows = [row for row in reader if row]
        file.seek(0)
        user_active_plate_numbers = [row[2] for row in all_rows if row[0] == str(user_id) and row[3] == 'ACTIVE']

    # Probably IF is not needed here. DOUBLE CHECK!!!
    if user_active_plate_numbers:
        buttons = [[KeyboardButton(plate_number)] for plate_number in user_active_plate_numbers]
        reply_markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Choose a plate number to delete:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("You have no active plate numbers.")


# Function to handle the user's selection of a plate number
async def record_queue_entry(update: Update, user_id: int, carwash_name: str, plate_number: str, context: CallbackContext) -> None:
    print("record_queue_entry")
    queue_record = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Date and time
        carwash_name,  # Carwash name
        user_id,  # User ID
        plate_number,  # Plate number
        "IN QUEUE"  # Status
    ]
    with open(QUEUE_FILE, 'a') as file:
        writer = csv.writer(file)
        writer.writerow(queue_record)

    # Get all the plate numbers in the queue for the given carwash
    queue_numbers = []
    with open(QUEUE_FILE, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) >= 5 and row[1] == carwash_name and row[4] == "IN QUEUE":
                queue_numbers.append(row[3])

    # Construct the queue message
    queue_message = "\n".join(queue_numbers)

    # Send the queue message to the user
    await update.message.reply_text(
        f"You have joined the queue at {carwash_name} with your plate number {plate_number}. Below is the queue:\n\n{queue_message}")
    await enter_leave_buttons(update, context)


# Function to handle unknown commands
async def unknown(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Sorry, I didn't understand that command. Press /start to start over again")


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Handle the /start command
    application.add_handler(CommandHandler("start", start))

    # Handle cases where the user presses the JOIN QUEUE button
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, app_flow))

    # Handle any unknown commands or messages that don't match any other handlers
    application.add_handler(MessageHandler(filters.ALL, unknown))

    # Start the bot and run it until it is interrupted
    application.run_polling()


if __name__ == '__main__':
    main()
