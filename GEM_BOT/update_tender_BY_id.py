from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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


def read_df():
    folder_path = os.path.join(os.getcwd(),'csv_files')
    csv_files = glob.glob(folder_path + '/*.csv')
    dfs = []
    for file in csv_files:
        df = pd.read_csv(file)
        dfs.append(df)
    merged_data = pd.concat(dfs, ignore_index=True, verify_integrity=True)
    merged_data['bid_no_1'] = merged_data['BID NO'].str.replace("/", "_")
    merged_data.to_csv('merged_data.csv', index=False)
    return merged_data


def check_db(data):
    tender_ids = data['bid_no_1'].to_list()
    db_data = pd.DataFrame(columns=['tender_id','submission_date'])
    if tender_ids and len(tender_ids) != 1:
        query = f"""SELECT tender_id, submission_date FROM tender.tender_management WHERE
        verification_1 = 'approved' and tender_id ilike 'GEM%' and tender_id not in {tuple(tender_ids)};"""
        db_data = db.get_row_as_dframe(query)
    db_dict = db_data.to_dict('records')
    return db_dict


def main():
    try:
        tender_dict = {}
        data = read_df()
        to_check = check_db(data)
        driver = webdriver.Chrome(options=chrome_options)
        driver.get('https://bidplus.gem.gov.in/all-bids')
        wi.processing_check_wait(driver, xpath='//*[@id="searchBid"]', time=300)
        for tender in to_check:
            print(tender)
            # if '2023' in tender['submission_date']:
            #     break
            try:
                bid_search = driver.find_element(By.XPATH, '//*[@id="searchBid"]')
                bid_search.click()
                bid_search.clear()
                bid_search.send_keys(tender['tender_id'].replace('_','/'))
                # bid_search.send_keys('GEM_2024_B_5197497'.replace('_','/'))
                bid_search_press = driver.find_element(By.XPATH, '//*[@id="searchBidRA"]')
                bid_search_press.click()
                wi.processing_check_wait(driver, xpath='//*[@id="light-pagination"]/a[6]', time=5)
                try:
                    no_tender = None
                    try:
                        end_dt = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[3]/div/div[3]/div[2]/span').text
                    except:
                        end_dt = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[5]/div[3]/div[1]/div[3]/div[2]/span').text
                except:
                    end_dt = None
                    try:
                        no_tender = driver.find_element(By.XPATH,'//div[text()="No data found"]').text
                        continue
                    except:
                        no_tender = None
                    if not no_tender:
                        raise Exception(f"Unable to locate End date for {tender['tender_id']}")

                if end_dt:
                    formatted_end_dt = datetime.datetime.strptime(end_dt, '%d-%m-%Y %I:%M %p').strftime('%Y-%m-%d %H:%M')
                    if tender['submission_date'] != formatted_end_dt:
                        query = f"""update tender.tender_management set submission_date = '{formatted_end_dt}',
                        done = 'New-Corrigendum', user_id = 'GEM BOT' where tender_id = '{tender['tender_id']}' ;"""
                        db.execute(query)
                        tender_dict[tender['tender_id']] = formatted_end_dt

            except Exception as err:
                sub='Error in Gem Portal'
                to_add=['ramit.shreenath@gmail.com']
                to_cc=[]
                body=f'''Hello Team,\n\nBelow Error found in Portal.\nError: {str(err)}\n\n\nThanks,\nGEM BOT'''
                mail.send_mail(to_add=to_add, to_cc=to_cc, sub=sub, body=body)
        to_add = ['ramit.shreenath@gmail.com']
        to_cc = []
        sub = 'Submission date Updated'
        body = f"""Hello Team,\n\nBelow is the dict of tenders, which have updated submission date,\n\n{tender_dict}\n\nThanks,GEM BOT"""
        mail.send_mail(to_add, to_cc, sub, body)
    except Exception as error:
        print(str(error))
    try:
        driver.close()
    except:
        pass


def job():
    try:
        print('Bot Started')
        main()
    except Exception as e:
        print(str(e))
        pass
    print('BOT executed at 9:30 PM')


if __name__ == '__main__':
    schedule.every().day.at('21:30').do(job)


    while True:
        schedule.run_pending()
        time.sleep(1)


