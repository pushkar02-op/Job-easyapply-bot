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
from gemini_helper import configure_api, create_model, answer_question
from dotenv import load_dotenv
import os



class LinkedInBot:
    def __init__(self, headless=False, timeout=10):
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, timeout)
        self.logger = self._setup_logger()
        load_dotenv()
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        configure_api(GEMINI_API_KEY)
        self.gemini_model = create_model("gemini-1.5-flash", "You are a helpful assistant that fills job application fields correctly.")


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
                time.sleep(10)
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
        # filtered_url="https://www.linkedin.com/jobs/search/?alertAction=viewjobs&currentJobId=4193708846&geoId=102713980&keywords=Dexian%20data%20engineer&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true"
        
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
    
    def get_dropdown_options(self, field_element):
        try:
            field_element.click()
            time.sleep(1)
            option_elements = self.driver.find_elements(By.XPATH, "//div[@role='listbox']//li")
            options = [opt.text.strip() for opt in option_elements if opt.text.strip()]
            return options
        except Exception as e:
            self.logger.error(f"❌ Failed to get dropdown options: {e}")
            return []
        
    def ask_ai_to_select_option(self, field_label, options):
        prompt = (
            f"Choose the most appropriate option from the list below for the field/question: "
            f"'{field_label}'. Options: {options}. "
            f"Respond with only one option from the list."
        )
        self.logger.info(f"🧠 AI Prompt: {prompt}")
        ai_response = self.query_gemini(prompt)
        return ai_response.strip()
    
    def select_option_by_text(self, option_text):
        try:
            options = self.driver.find_elements(By.XPATH, "//div[@role='listbox']//li")
            for option in options:
                if option_text.lower() in option.text.strip().lower():
                    option.click()
                    self.logger.info(f"✅ Selected dropdown option: {option.text}")
                    return True
            self.logger.warning(f"⚠️ Option '{option_text}' not found in dropdown.")
        except Exception as e:
            self.logger.error(f"❌ Error selecting dropdown option: {e}")
        return False

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
    def autofill_required_fields(self, missing_fields):
        """
        Autofills missing required fields using Gemini responses based on field prompts.
        """
        for field_info in missing_fields:
            element = field_info["element"]
            prompt = field_info["prompt"]
            tag = field_info["tag"]
            field_type = field_info["type"]
            # Append a note to ask Gemini for a value matching the expected format.
            full_prompt = prompt  # Already includes validation feedback if available.

            try:
                # Get answer from Gemini (this returns the generated text)
                ai_response = answer_question(self.gemini_model, context="", question=full_prompt)
            except Exception as e:
                self.logger.error(f"❌ Gemini API error: {e}")
                ai_response = "Sample Text"

            # Handle dropdown fields separately
            if tag == "select" and field_type == "select-one":
                try:
                    # Wait for the dropdown to become visible and clickable
                    select_elem = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable(element)
                    )
                    # Open the dropdown and select the option based on AI response
                    options = select_elem.find_elements(By.TAG_NAME, "option")
                    selected_option = None
                    for option in options:
                        if ai_response.lower() in option.text.strip().lower():
                            selected_option = option
                            break
                    if selected_option:
                        selected_option.click()
                        self.logger.info(f"✍️ Autofilled dropdown '{field_info['label']}' with '{ai_response}'")
                    else:
                        self.logger.warning(f"❌ No matching option found for dropdown '{field_info['label']}'")
                except Exception as e:
                    self.logger.error(f"❌ Error autofilling dropdown '{field_info['label']}': {e}")
            else:
                # For non-dropdown fields (text inputs, etc.), proceed as before
                try:
                    element.click()
                    element.clear()
                    element.send_keys(ai_response)
                    self.logger.info(f"✍️ Autofilled '{field_info['label']}' with '{ai_response}'")
                    time.sleep(1)
                except Exception as fill_error:
                    self.logger.error(f"❌ Could not fill field '{field_info['label']}': {fill_error}")

    def get_label_from_parent(self, field):
        try:
            # Go up to parent container and find any label or span with question
            container = self.driver.execute_script(
                "return arguments[0].closest('div[id*=\"formElement\"]');", field)
            if container:
                label_elem = container.find_element(By.XPATH, ".//label | .//span")
                label_text = label_elem.text.strip()
                if label_text:
                    return label_text
        except Exception:
            return None

    def check_required_fields(self):
        try:
            self.logger.info("🔍 Checking required fields in modal...")

            # Wait for modal to appear.
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "jobs-easy-apply-modal")))
            time.sleep(1)

            # Find all required input, textarea, and select elements.
            required_fields = self.driver.find_elements(By.CSS_SELECTOR, "input[required], textarea[required], select[required]")
            missing_fields = []
            prompts = []

            for field in required_fields:
                tag = field.tag_name.lower()
                field_type = field.get_attribute("type") or "text"
                # Use a fallback to extract label from attributes or nearby elements.
                # Fallback method to extract label from adjacent elements
                label = (
                    field.get_attribute("aria-label")
                    or field.get_attribute("name")
                    or field.get_attribute("placeholder")
                    or field.find_element(By.XPATH, './preceding-sibling::label').text.strip()  # Check nearby labels
                    or "Unknown field"
                )

                value = field.get_attribute("value") or ""

                # For select elements, consider them filled if a non-default option is selected.
                is_select = (tag == "select")
                is_filled = bool(value.strip()) if not is_select else field.get_attribute("selectedIndex") not in ["", "0", None]

                # For input fields, if empty, trigger validation by typing a test character.
                validation_message = ""
                if not is_filled and tag == "input":
                    try:
                        field.clear()
                        field.send_keys("a")  # Type a test character.
                        time.sleep(1)
                    except Exception:
                        pass

                    # Check if field now has an error by class name.
                    if "fb-dash-form-element__error-field" in field.get_attribute("class"):
                        # Use the aria-describedby to extract the error message.
                        error_id = field.get_attribute("aria-describedby")
                        if error_id:
                            try:
                                error_elem = self.driver.find_element(By.CSS_SELECTOR, f"#{error_id} .artdeco-inline-feedback__message")
                                validation_message = error_elem.text.strip()
                            except Exception:
                                validation_message = ""
                        is_filled = False  # Even if a value is present, error indicates invalid data.

                self.logger.info(f"➡️ Field: {label} | Tag: {tag} | Type: {field_type} | Filled: {is_filled}")

                if not is_filled:
                    # Build Gemini prompt based on error feedback if available.
                    if validation_message:
                        prompt_text = f"Please provide a valid answer for '{label}'. The input must satisfy: {validation_message}"
                    else:
                        prompt_text = f"Please provide an appropriate answer for '{label}' (expected input type: {field_type})."
                    missing_fields.append({
                        "element": field,
                        "label": label,
                        "type": field_type,
                        "tag": tag,
                        "prompt": prompt_text,
                        "validation": validation_message
                    })
                    self.logger.info(f"🧠 Prompt to generate: {prompt_text}")

            if not missing_fields:
                self.logger.info("✅ All required fields are already filled.")
            else:
                self.logger.warning(f"⚠️ {len(missing_fields)} required fields are empty or invalid.")

            prompts = [field["prompt"] for field in missing_fields]
            return missing_fields, prompts

        except Exception as e:
            self.logger.error(f"❌ Error while checking required fields: {e}")
            return [], []



    def handle_easy_apply_modal(self):
        try:
            self.logger.info("📝 Handling Easy Apply modal...")

            # Wait for the Easy Apply modal to appear.
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "jobs-easy-apply-modal")))
            time.sleep(2)  # Allow time for modal contents to render

            # Multi-step modal handling
            max_steps = 4
            for step in range(max_steps):
                self.logger.info(f"🔄 Step {step + 1}: Checking required fields...")
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

                # Try "Continue to next step"
                try:
                    continue_btn = self.driver.find_element(By.XPATH, "//button[@aria-label='Continue to next step']")
                    if continue_btn.is_displayed() and continue_btn.is_enabled():
                        continue_btn.click()
                        self.logger.info("✅ Clicked 'Continue to next step'")
                        time.sleep(2)
                        continue
                except NoSuchElementException:
                    self.logger.debug("➡️ No 'Continue to next step' button on this screen.")

                # Try "Review your application"
                try:
                    review_btn = self.driver.find_element(By.XPATH, "//button[@aria-label='Review your application']")
                    if review_btn.is_displayed() and review_btn.is_enabled():
                        review_btn.click()
                        self.logger.info("✅ Clicked 'Review your application'")
                        time.sleep(2)

                        # ✅ After review, check for validation errors before attempting submission
                        error_elements = self.driver.find_elements(By.CLASS_NAME, "artdeco-inline-feedback")
                        if error_elements:
                            for error in error_elements:
                                self.logger.warning(f"❗ Validation error on review: {error.text}")
                            self.logger.warning("❌ Submission blocked due to validation errors.")
                            return False

                        continue
                except NoSuchElementException:
                    self.logger.debug("➡️ No 'Review your application' button on this screen.")

                # Try unchecking follow company checkbox
                try:
                    follow_checkbox = self.driver.find_element(By.ID, "follow-company-checkbox")
                    if follow_checkbox.is_selected():
                        self.driver.execute_script("arguments[0].click();", follow_checkbox)
                        self.logger.info("☑️ Unchecked 'Follow company' checkbox.")
                except Exception:
                    self.logger.debug("🔍 'Follow company' checkbox not found or already unchecked.")

                # Try "Submit application"
                try:
                    submit_btn = self.driver.find_element(By.XPATH, "//button[@aria-label='Submit application']")
                    if submit_btn.is_displayed() and submit_btn.is_enabled():
                        submit_btn.click()
                        self.logger.info("✅ Clicked 'Submit application'")
                        time.sleep(2)
                        return True
                except NoSuchElementException:
                    self.logger.warning("⚠️ No 'Submit application' button found.")

                # Try generic "Next" or "Submit" button if labeled differently
                try:
                    alt_submit_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
                    if alt_submit_btn.is_displayed() and alt_submit_btn.is_enabled():
                        alt_submit_btn.click()
                        self.logger.info("✅ Clicked alternate 'Submit' button")
                        time.sleep(2)
                        return True
                except NoSuchElementException:
                    self.logger.debug("🔍 No alternate submit button found.")

            # ❌ Final fallback — capture screenshot and HTML for debugging
            self.logger.warning("⚠️ Could not complete submission process after all steps.")
            try:
                self.driver.save_screenshot("modal_debug.png")
                with open("modal_debug.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                self.logger.info("🧾 Saved screenshot and page HTML for debugging.")
            except Exception as e:
                self.logger.error(f"⚠️ Could not save debug files: {e}")

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
