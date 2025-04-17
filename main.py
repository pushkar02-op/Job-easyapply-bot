from linkedin_bot import LinkedInBot
import os
from dotenv import load_dotenv
import json

# Load LinkedIn credentials
load_dotenv()
EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# Load config (job title, location, etc.)
with open("config.json") as f:
    config = json.load(f)


# Step 2: Pass resume_text into the bot
# bot = LinkedInBot(headless=False, timeout=15, resume_text=resume_text)

# Step 3: Run the bot
# try:
#     bot.login(EMAIL, PASSWORD)
#     bot.search_jobs(config["job_title"], config["location"])
#     jobs = bot.collect_job_cards(max_jobs=10)

#     if jobs:
#         bot.apply_to_jobs(jobs)
#     else:
#         print("No jobs found to apply.")
# finally:
#     bot.close()
