from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TOKEN")
DB_PATH = os.getenv("DB_PATH")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))

TOKEN2 = os.getenv("TOKEN2")
GROUP_CHAT_ID_FOR_REGION = int(os.getenv("GROUP_CHAT_ID_FOR_REGION"))


