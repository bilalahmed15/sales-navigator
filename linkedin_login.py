from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

class LinkedInLogin:
    def __init__(self):
        self.driver = None

    def setup_browser(self):
        if self.driver is None:
            options = Options()
            options.add_argument("--enable-javascript")
            options.add_argument("--enable-cookies")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")
            
            self.driver = webdriver.Chrome()
        return self.driver

    def wait_and_find_element(self, by, value, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def login(self, email, password):
        try:
            # Get or create driver instance
            self.driver = self.setup_browser()
            self.driver.get("https://www.linkedin.com/login")
            username_field = self.wait_and_find_element(By.ID, "username")
            password_field = self.wait_and_find_element(By.ID, "password")
            username_field.send_keys(email)
            password_field.send_keys(password)
            self.driver.find_element(By.CLASS_NAME, "btn__primary--large").click()
            time.sleep(3)

            # Check for two-step challenge
            try:
                two_step_div = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "two-step-challenge"))
                )
                print("Two-step challenge detected. Waiting for code input.")
                return '2fa', "Two-step authentication required. Please enter the code."
            except Exception:
                time.sleep(5)
                pass  # No 2FA, continue

            # Check if we need to login to Sales Navigator
            try:
                sales_nav_email = self.wait_and_find_element(By.CSS_SELECTOR, "input[type='email']", timeout=5)
                sales_nav_password = self.wait_and_find_element(By.CSS_SELECTOR, "input[type='password']", timeout=5)
                sales_nav_email.send_keys(email)
                sales_nav_password.send_keys(password)
                login_button = self.wait_and_find_element(By.CSS_SELECTOR, "button[type='submit']", timeout=5)
                login_button.click()
                time.sleep(8)
            except Exception as e:
                print("No Sales Navigator login required or error:", str(e))

            time.sleep(3)
            return True, "Successfully logged in"
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False, str(e)

    def submit_2fa_code(self, code):
        try:
            code_input = self.wait_and_find_element(By.CLASS_NAME, "form__input--text")
            code_input.clear()
            code_input.send_keys(code)
            submit_btn = self.driver.find_element(By.CLASS_NAME, "form__submit")
            submit_btn.click()
            time.sleep(3)
            return True, "2FA code submitted. Login should continue."
        except Exception as e:
            print(f"2FA submission error: {str(e)}")
            return False, str(e)

    def quit(self):
        if self.driver:
            self.driver.quit()
            self.driver = None 