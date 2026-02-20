import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", "30"))

CPU_CRIT = float(os.getenv("CPU_CRIT", "90"))
RAM_CRIT = float(os.getenv("RAM_CRIT", "90"))
DISK_CRIT = float(os.getenv("DISK_CRIT", "90"))
CRIT_CONFIRM_CYCLES = int(os.getenv("CRIT_CONFIRM_CYCLES", "3"))

TOPIC_FILE = "topic.txt"


def get_topic_id() -> int | None:
    if not os.path.exists(TOPIC_FILE):
        return None
    try:
        with open(TOPIC_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return None


def set_topic_id(topic_id: int) -> None:
    with open(TOPIC_FILE, "w") as f:
        f.write(str(topic_id))

STATUS_MESSAGE_ID_FILE = "status_message_id.txt"

def get_status_message_id() -> int | None:
    try:
        with open(STATUS_MESSAGE_ID_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return None

def set_status_message_id(message_id: int):
    with open(STATUS_MESSAGE_ID_FILE, "w") as f:
        f.write(str(message_id))