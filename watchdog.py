"""
Watchdog — keeps bot.py running. If it crashes, restarts it automatically.
Run this instead of bot.py: python watchdog.py
"""

import os
import subprocess
import sys
import time
import logging
from datetime import datetime

logging.basicConfig(
    format="%(asctime)s %(levelname)s watchdog — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

RESTART_DELAY = 5  # seconds to wait before restarting after a crash


def run():
    while True:
        logger.info("Starting bot.py...")
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        process = subprocess.Popen(
            [sys.executable, "-X", "utf8", "bot.py"],
            stdout=sys.stdout,
            stderr=sys.stderr,
            env=env,
        )
        exit_code = process.wait()

        if exit_code == 0:
            logger.info("Bot exited cleanly. Stopping watchdog.")
            break

        logger.warning(f"Bot crashed with exit code {exit_code}. Restarting in {RESTART_DELAY}s...")
        time.sleep(RESTART_DELAY)


if __name__ == "__main__":
    run()
