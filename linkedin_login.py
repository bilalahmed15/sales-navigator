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
            
            # Login to LinkedIn
            self.driver.get("https://www.linkedin.com/login")
            
            # Wait for and fill in login form
            username_field = self.wait_and_find_element(By.ID, "username")
            password_field = self.wait_and_find_element(By.ID, "password")
            
            username_field.send_keys(email)
            password_field.send_keys(password)
            self.driver.find_element(By.CLASS_NAME, "btn__primary--large").click()
            
            # Wait for login to complete and handle Sales Navigator login if needed
            time.sleep(5)  # Wait for initial login to complete
            
            # Check if we need to login to Sales Navigator
            try:
                # Look for Sales Navigator login elements
                sales_nav_email = self.wait_and_find_element(By.CSS_SELECTOR, "input[type='email']", timeout=5)
                sales_nav_password = self.wait_and_find_element(By.CSS_SELECTOR, "input[type='password']", timeout=5)
                
                # If we found the fields, we need to login to Sales Navigator
                sales_nav_email.send_keys(email)
                sales_nav_password.send_keys(password)
                
                # Find and click the Sales Navigator login button
                login_button = self.wait_and_find_element(By.CSS_SELECTOR, "button[type='submit']", timeout=5)
                login_button.click()
                
                # Wait for Sales Navigator login to complete
                time.sleep(5)
            except Exception as e:
                print("No Sales Navigator login required or error:", str(e))
            
            # Navigate to the search page
            search_url = "https://www.linkedin.com/sales/search/people?query=(spellCorrectionEnabled%3Atrue%2CrecentSearchParam%3A(id%3A3756865305%2CdoLogHistory%3Atrue)%2Ckeywords%3AAnti-corrosion)&sessionId=p7n9oaNfRVOWg9ReV5K7GA%3D%3D"
            self.driver.get(search_url)
            
            # Wait for search results to load
            time.sleep(5)
            
            return True, "Successfully logged in"
            
        except Exception as e:
            print(f"Login error: {str(e)}")
            return False, str(e)

    def quit(self):
        if self.driver:
            self.driver.quit()
            self.driver = None 