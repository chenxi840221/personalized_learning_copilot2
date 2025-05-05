import asyncio
import aiocron
import logging
from datetime import datetime
import sys
import os
# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scrapers.abc_edu_scraper import run_scraper
from utils.logger import setup_logger
# Setup logger
logger = setup_logger("scheduler")
class SchedulerManager:
    def __init__(self):
        self.jobs = []
    def start(self):
        """Start all scheduled jobs."""
        logger.info("Starting scheduler")
        # Schedule the ABC Education scraper to run daily at 2 AM
        scraper_job = aiocron.crontab('0 2 * * *', func=self._run_scraper, start=True)
        self.jobs.append(scraper_job)
        logger.info(f"Scheduled ABC Education scraper to run daily at 2 AM")
        # Keep the event loop running
        asyncio.get_event_loop().run_forever()
    async def _run_scraper(self):
        """Run the ABC Education scraper."""
        logger.info(f"Starting scheduled ABC Education scraper at {datetime.now()}")
        try:
            await run_scraper()
            logger.info(f"Completed scheduled ABC Education scraper at {datetime.now()}")
        except Exception as e:
            logger.error(f"Error running scheduled ABC Education scraper: {e}")
def run_scheduler():
    """Run the scheduler."""
    scheduler = SchedulerManager()
    scheduler.start()
if __name__ == "__main__":
    run_scheduler()