from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pandas as pd
import os
import time
import glob
import web_interface as wi
import datetime
import db_connect as db
import schedule
import mail

download_folder = os.path.join(os.getcwd(), 'downloads')

chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')

prefs = {
    'download.default_directory': download_folder,
    'download.prompt_for_download': False,
    'download.directory_upgrade': True,
    'safebrowsing.enabled': True
}

chrome_options.add_experimental_option('prefs', prefs)


def create_dataframe(data_string):
    line_data = data_string.split('\n')
    lines = [av.strip() for av in line_data if 'RA NO' not in av]
    department_details = lines[3] + ' ' + lines[4] + ' '
    if ':' not in lines[5]:
        department_details += lines[5]

    new_av = [item for item in lines if ':' in item]

    new_av.remove('Department Name And Address:')
    new_av.append(department_details)
    data = {}
    for line in new_av:
        key, value = line.split(':', maxsplit=1)
        key = key.strip()
        value = value.strip()
        if key == 'End Date':
            value = datetime.datetime.strptime(value, '%d-%m-%Y %I:%M %p').strftime('%Y-%m-%d %H:%M')
        if key == 'Start Date':
            value = datetime.datetime.strptime(value, '%d-%m-%Y %I:%M %p').strftime('%Y-%m-%d %H:%M')
        data[key] = [value]
    df = pd.DataFrame(data)
    return df, data['BID NO']


def main():
    print('Starting the bot')
    driver = webdriver.Chrome(options=chrome_options)
    driver.get('https://bidplus.gem.gov.in/all-bids')
    wi.processing_check_wait(driver, xpath='//*[@id="searchBid"]', time=300)
    bid_search = driver.find_element(By.XPATH, '//*[@id="searchBid"]')
    bid_search.click()
    bid_search.send_keys('Audio Video Equipment/conferencing system')
    bid_search_press = driver.find_element(By.XPATH, '//*[@id="searchBidRA"]')
    bid_search_press.click()
    wi.processing_check_wait(driver, xpath='//*[@id="light-pagination"]/a[6]', time=5)
    try:
        total_pages = driver.find_element(By.XPATH, '//*[@id="light-pagination"]/a[6]')
        tp = total_pages.text
       # print(f"Total pages: {total_pages}")
        tp = 50
    except:
        tp = 1

    result_df = pd.DataFrame()
    for k in range(int(tp)):
    # for k in range(1):
        print(k)
        try:
            print(f'Page {k+1}')
            wi.processing_check_wait(driver, cls='card', time=10)
            bids_page_data = driver.find_elements(By.CLASS_NAME, "card")
            try:
                xpath_corr = '//*[contains(text(), "View Corrigendum/Representation")]'
                css_selector_corr = ':contains("View Corrigendum/Representation")'

                js_script = f"""document.querySelectorAll('{xpath_corr}').forEach(element => element.click())"""
                driver.execute_script(js_script)

            except:
                pass
            c = 1
            for i in bids_page_data:
                bid_data = i.text.replace("View Corrigendum/Representation\n", "").replace("Bid No.:", "BID NO:")
                c += 1
                bid_df, bid = create_dataframe(bid_data)
                print(str(bid).replace("['", "").replace("']", ""))
                time.sleep(2)
                try:
                    a = driver.find_element(By.XPATH,f'//*[@id="bidCard"]/div[{c}]/div[3]/div/div[1]/div[1]/a')
                    atb = a.get_attribute('data-content')
                    bid_df['new_itm'] = atb
                except:
                    bid_df['new_itm'] = bid_df['Items']

                result_df = pd.concat([result_df, bid_df], ignore_index=True)

            try:
                time.sleep(2)
                next_btn = driver.find_element(By.XPATH, '//*[text()="Next"]')
                next_btn.click()
            except:
                continue
        except Exception as err:
            print(str(err))
            body=f''' Hello Team,\n\nBelow Error found in Portal loading.\nError: {str(err)}\n\n\nThanks,\nGEM BOT'''
            mail.send_mail(to_add=['ramit.shreenath@gmail.com'], to_cc=[], sub='Portal Error in GEM Portal', body=body)

    try:
        driver.close()
    except:
        pass
    # filtered_df = result_df[result_df['new_itm'].str.contains('camera', case=False, regex=False)]
    # filtered_df = result_df[~result_df['new_itm'].str.contains('DSLR', case=False, regex=False)]
    filtered_df = result_df
    filtered_df.to_csv(os.path.join(os.getcwd(),'csv_files','bid_data_Audio_Video_Equipment.csv'))



def job():
    try:
        main()
    except Exception as err:
        sub='Gem Portal Error in main fun'
        body=f'''Hello Ramit,\n\nThere is an error in GEM BOT\nError: {str(err)}\n\n\nthanks,\nGEM BOT'''
        mail.send_mail(to_add=['ramit.shreenath@gmail.com'], to_cc=[],sub=sub,body=body)
    print('BOT executed at 10:00 & 1:00 AM')



if __name__ == '__main__':
    schedule.every().day.at('11:15').do(job)
    # schedule.every().day.at('10:00').do(job)
    # schedule.every().day.at('13:00').do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)
