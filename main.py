import time
import random
from selenium.webdriver.common.by import By
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def setup_browser():
    options = Options()
    options.add_argument("--enable-javascript")
    options.add_argument("--enable-cookies")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")
    
    driver = webdriver.Chrome()
    return driver
driver = setup_browser()
# Use webdriver_manager to install and manage ChromeDriver

page_url="https://www.linkedin.com/login"
driver.get(page_url)

driver.find_element(By.ID,"username").send_keys("s.bilal1829@gmail.com")
driver.find_element(By.ID,"password").send_keys("Bilal1874")
driver.find_element(By.CLASS_NAME,"btn__primary--large").click()

driver.get("https://www.linkedin.com/sales/search")