
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


def processing_check_wait(driver, xpath=None, cls=None, time=10):
    try:
        wait = WebDriverWait(driver, time)
        if xpath:
            element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        elif cls:
            element = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, cls)))
        if element:
            return True
        return False
    except:
        return False