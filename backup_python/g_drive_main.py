# from selenium import webdriver
# from selenium.webdriver.common.keys import Keys
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options
# import os


# chrome_options = Options()
# chrome_options.add_argument('--no-sandbox')
# chrome_options.add_argument('--disable-dev-shm-usage')

# download_folder = os.path.join(os.getcwd(), 'all_downloads')

# prefs = {
#     'download.default_directory': download_folder,
#     'download.prompt_for_download': False,
#     'download.directory_upgrade': True,
#     'safebrowsing.enabled': True
# }

# chrome_options.add_experimental_option('prefs', prefs)


# # Replace 'your_username' and 'your_password' with your Google account credentials
# username = 'dme@shreenathgroup.in'
# password = 'Blaze@456'

# # Path to the Chrome WebDriver executable (change to the path where you have downloaded the WebDriver)
# webdriver_path = '/path/to/chromedriver'

# # Initialize the Chrome WebDriver
# driver = webdriver.Chrome(options=chrome_options)

# # Open Google Drive login page
# driver.get("https://drive.google.com")

# # Click on the "Go to Google Drive" button
# go_to_drive_button = driver.find_element_by_xpath('//*[@id="hero-cta-wrapper"]/a[2]')
# go_to_drive_button.click()

# driver.switch_to.window(driver.window_handles[1])

# # Fill in the login form
# username_field = driver.find_element_by_xpath('//*[@id="identifierId"]')
# username_field.clear()
# username_field.send_keys(username)
# username_field.send_keys(Keys.RETURN)

# # Wait for the password input field to appear
# password_field = driver.find_element_by_xpath('//*[@id="password"]/div[1]/div/div[1]/input')
# password_field.clear()
# password_field.send_keys(password)
# password_field.send_keys(Keys.RETURN)

# bkp_folder = driver.find_element(By.XPATH, '//*[@id=":j"]/div/c-wiz/div[2]/c-wiz/div[1]/c-wiz/div[2]/c-wiz/div[1]/c-wiz[1]/c-wiz/div/c-wiz[8]/div/div/div/div[2]/div/div')
# bkp_folder.click()