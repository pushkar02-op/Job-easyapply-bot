from linkedin_bot import LinkedInBot
import os
from dotenv import load_dotenv
import json

load_dotenv()

EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")

with open("config.json") as f:
    config = json.load(f)

bot = LinkedInBot(headless=False, timeout=15)  # Set True if you don't want the browser to pop up

try:
    bot.login(EMAIL, PASSWORD)
    bot.search_jobs(config["job_title"], config["location"])
    jobs = bot.collect_job_cards(max_jobs=1)
    
    if jobs:
        bot.apply_to_jobs(jobs)
    else:
        print("No jobs found to apply.")

finally:
    bot.close()
