from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging


class LinkedInBot:
    def __init__(self, headless=False, timeout=10):
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, timeout)
        self.logger = self._setup_logger()

    def _setup_logger(self):
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _setup_driver(self, headless: bool = False):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    def login(self, email: str, password: str):
        self.logger.info("Navigating to LinkedIn login page...")
        self.driver.get("https://www.linkedin.com/login")
        time.sleep(2)

        try:
            if "feed" in self.driver.current_url or "jobs" in self.driver.current_url:
                self.logger.info("✅ Already logged in. Skipping login.")
                return

            username_input = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            self.logger.info("🔐 Logging into LinkedIn...")

            username_input.send_keys(email)
            self.driver.find_element(By.ID, "password").send_keys(password)

            # ⛔ Uncheck 'Keep me signed in' checkbox if it's selected
            try:
                remember_checkbox = self.driver.find_element(By.ID, "rememberMeOptIn-checkbox")
                if remember_checkbox.is_selected():
                    self.driver.execute_script("arguments[0].click();", remember_checkbox)
                    self.logger.info("☑️ Unchecked 'Keep me signed in' option.")
            except Exception as e:
                self.logger.warning(f"⚠️ Could not handle 'Keep me signed in' checkbox: {e}")

            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            time.sleep(3)

            if "feed" in self.driver.current_url or "jobs" in self.driver.current_url:
                self.logger.info("✅ Login successful.")
            else:
                self.logger.warning("⚠️ Login may have failed. Please verify.")
        except TimeoutException:
            self.logger.warning("⚠️ Login fields not found. Possibly already logged in.")

    def search_jobs(self, job_title: str, location: str):
        self.logger.info(f"Searching for jobs: {job_title} in {location}")

        base_url = "https://www.linkedin.com/jobs/search/"
        job_param = job_title.replace(" ", "%20")
        location_param = location.replace(" ", "%20")

        filtered_url = (
            f"{base_url}?keywords={job_param}"
            f"&location={location_param}"
            f"&f_AL=true"            # Easy Apply
            f"&geoId=102713980"      # India geoId (adjust as needed)
        )

        self.driver.get(filtered_url)
        time.sleep(5)
        self.logger.info("✅ Search page with filters loaded.")

    def collect_job_cards(self, max_jobs=10):
        self.logger.info("Collecting job cards...")
        job_cards = []

        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

            listings = []
            for attempt in range(3):
                listings = self.driver.find_elements(By.CLASS_NAME, "job-card-container")
                if listings:
                    break
                self.logger.info(f"Retrying job load... ({attempt + 1})")
                time.sleep(2)

            self.logger.info(f"Found {len(listings)} job cards")
            if not listings:
                self.logger.error("No job listings found after retries.")
                return []

            for idx, job in enumerate(listings[:max_jobs]):
                try:
                    title = job.find_element(By.CSS_SELECTOR, "a.job-card-container__link span strong").text.strip()
                    company = job.find_element(By.CSS_SELECTOR, "div.artdeco-entity-lockup__subtitle span").text.strip()
                    location = job.find_element(By.CSS_SELECTOR, "ul.job-card-container__metadata-wrapper li").text.strip()
                    link = job.find_element(By.TAG_NAME, "a").get_attribute("href")

                    job_cards.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "link": link
                    })

                    self.logger.info(f"[{idx+1}] {title} at {company} — {location}")
                except Exception as e:
                    self.logger.warning(f"Skipping job #{idx+1} due to error: {e}")

        except Exception as e:
            self.logger.error(f"Error during job collection: {e}")

        self.logger.info(f"Collected {len(job_cards)} job cards.")
        return job_cards
    
    def get_field_prompt(self, input_element):
        """Extracts the most relevant question or label for a given input element."""
        try:
            # 1. Check aria-label
            aria_label = input_element.get_attribute("aria-label")
            if aria_label:
                return aria_label.strip()

            # 2. Check placeholder
            placeholder = input_element.get_attribute("placeholder")
            if placeholder:
                return placeholder.strip()

            # 3. Check associated <label for="input_id">
            input_id = input_element.get_attribute("id")
            if input_id:
                label = self.driver.find_elements(By.XPATH, f"//label[@for='{input_id}']")
                if label:
                    return label[0].text.strip()

            # 4. Check previous sibling text (less reliable fallback)
            parent = input_element.find_element(By.XPATH, "..")
            try:
                preceding = parent.find_element(By.XPATH, "./preceding-sibling::*[1]")
                if preceding.text:
                    return preceding.text.strip()
            except:
                pass

        except Exception as e:
            self.logger.warning(f"❌ Error extracting field prompt: {e}")

        return "Field information not found"
    def autofill_required_fields(self, missing_fields: list):
        for field in missing_fields:
            tag = field["tag"]
            prompt = field["prompt"]
            elem = field["element"]

            # Placeholder: Use a dummy value or integrate Gemini API later.
            fake_value = "8210301136" if "phone" in prompt.lower() else "Test Answer"

            try:
                if tag in ["input", "textarea"]:
                    elem.clear()
                    elem.send_keys(fake_value)
                elif tag == "select":
                    Select(elem).select_by_index(1)  # Select first available option
                self.logger.info(f"✍️ Autofilled field '{prompt}' with '{fake_value}'")
            except Exception as e:
                self.logger.warning(f"⚠️ Could not autofill field '{prompt}': {e}")
                
    def check_required_fields(self):
        try:
            self.logger.info("🔍 Checking required fields in modal...")

            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "jobs-easy-apply-modal")))

            required_fields = self.driver.find_elements(By.CSS_SELECTOR, "input[required], textarea[required], select[required]")

            missing_fields = []
            prompts = []

            for field in required_fields:
                tag = field.tag_name
                field_type = field.get_attribute("type") or tag
                value = field.get_attribute("value") or ""

                prompt = self.get_field_prompt(field)  # ← assumes you’ve defined this method

                # Handle select separately
                is_filled = (
                    bool(value.strip())
                    if tag != "select"
                    else field.get_attribute("selectedIndex") != "0"
                )

                self.logger.info(f"➡️ Field: {prompt} | Tag: {tag} | Type: {field_type} | Filled: {is_filled}")

                if not is_filled:
                    missing_fields.append({
                        "element": field,
                        "prompt": prompt,
                        "tag": tag,
                        "type": field_type
                    })
                    question = f"Please provide an answer for the following required field: {prompt}"
                    prompts.append(question)
                    self.logger.info(f"🧠 Prompt to generate: {question}")

            if not missing_fields:
                self.logger.info("✅ All required fields are already filled.")
            else:
                self.logger.warning(f"⚠️ {len(missing_fields)} required fields are empty.")

            return missing_fields, prompts

        except Exception as e:
            self.logger.error(f"❌ Error while checking required fields: {e}")
            return [], []



    def handle_easy_apply_modal(self):
        try:
            self.logger.info("📝 Handling Easy Apply modal...")

            # Wait for the Easy Apply modal to appear.
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "jobs-easy-apply-modal")))
            time.sleep(3)  # Allow time for modal contents to render

            # Check for required fields and autofill if needed.
            missing_fields, prompts = self.check_required_fields()
            if missing_fields:
                self.logger.warning("❌ Required fields are empty; attempting to autofill them.")
                self.autofill_required_fields(missing_fields)

                # Re-check after autofill
                missing_fields, prompts = self.check_required_fields()
                if missing_fields:
                    for p in prompts:
                        self.logger.info(f"❓ Gemini Prompt: {p}")
                    self.logger.warning("❌ Still missing required field values. Skipping job.")
                    return False

            # Step-through modal process
            max_steps = 5
            for step in range(max_steps):
                try:
                    # Click "Continue to next step" if available
                    continue_btn = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Continue to next step']"))
                    )
                    continue_btn.click()
                    self.logger.info(f"✅ Clicked 'Continue to next step' (Step {step+1})")
                    time.sleep(2)
                    continue  # Proceed to next iteration
                except TimeoutException:
                    self.logger.info("ℹ️ No 'Continue to next step' button found, checking for review/submit.")

                # Try "Review your application"
                try:
                    review_btn = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Review your application']"))
                    )
                    review_btn.click()
                    self.logger.info("✅ Clicked 'Review your application'")
                    time.sleep(2)
                    continue  # Proceed to find submit next
                except TimeoutException:
                    self.logger.debug("ℹ️ 'Review your application' button not found.")
            
                # Try unchecking follow-company-checkbox if present
                try:
                    follow_checkbox = self.driver.find_element(By.ID, "follow-company-checkbox")
                    if follow_checkbox.is_selected():
                        self.driver.execute_script("arguments[0].click();", follow_checkbox)
                        self.logger.info("☑️ Unchecked 'Follow company' checkbox.")
                except Exception:
                    self.logger.debug("🔍 'Follow company' checkbox not found or not interactable.")


                # Try final "Submit application"
                try:
                    submit_btn = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Submit application']"))
                    )
                    submit_btn.click()
                    self.logger.info("✅ Clicked 'Submit application'")
                    time.sleep(2)
                    return True  # Success
                except TimeoutException:
                    self.logger.warning("⚠️ No 'Submit application' button found.")
                    break  # Exit if none found

            self.logger.warning("⚠️ Could not complete submission process after all steps.")
            return False

        except TimeoutException:
            self.logger.warning("❌ No Easy Apply modal detected.")
        except Exception as e:
            self.logger.error(f"⚠️ Could not complete modal handling: {e}")

        return False




    def apply_to_jobs(self, job_cards: list):
        self.logger.info("Starting Easy Apply process...")

        for idx, job in enumerate(job_cards):
            try:
                self.logger.info(f"Opening job #{idx+1}: {job['title']} at {job['company']}")
                self.driver.get(job['link'])
                time.sleep(4)

                # Find all Easy Apply buttons (yes, there can be multiple with same ID!)
                all_buttons = self.driver.find_elements(By.XPATH, "//button[@id='jobs-apply-button-id']")

                # Filter only the visible one
                visible_buttons = [btn for btn in all_buttons if btn.is_displayed()]
                if not visible_buttons:
                    self.logger.warning(f"⚠️ No visible Easy Apply button found for: {job['title']}")
                    continue
                
                

                easy_apply_btn = visible_buttons[0]
                
                try:
                    easy_apply_btn.click()
                    # NEW: Handle modal
                    if not self.handle_easy_apply_modal():
                        self.logger.warning(f"⚠️ Skipped job (modal handling failed): {job['title']}")
                except Exception as click_error:
                    self.logger.warning("Standard click failed, trying JavaScript click. Error: " + str(click_error))
                    self.driver.execute_script("arguments[0].click();", easy_apply_btn)

            except TimeoutException:
                self.logger.warning(f"⚠️ Timeout waiting for Easy Apply button on: {job['title']}")
            except Exception as e:
                self.logger.error(f"❌ Error applying to job #{idx+1}: {e}")

    def close(self):
        self.logger.info("Closing browser session.")
        self.driver.quit()
