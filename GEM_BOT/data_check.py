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
import shutil
import schedule
import mail
import re
import fitz
import requests
import pdfplumber

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


def get_latest_downloaded_file(type):
    list_of_files = glob.glob(os.path.join(download_folder, '*'))
    if type == 'pdf':
        filtered_files = [
            file for file in list_of_files
            if ".pdf" in file.lower()
        ]
    if filtered_files:
        latest_file = max(filtered_files, key=os.path.getctime)
        return latest_file
    else:
        return None


def extract_links_from_pdf(pdf_path):
    links = []
    doc = fitz.open(pdf_path)
    for i in range(doc.page_count):
        page = doc.load_page(i)
        links_on_page = page.get_links()
        links.extend(links_on_page)
    return links


def download_files(urls, download_path, nas_path):
    new_path = []
    os.makedirs(download_path, exist_ok=True)
    for url in urls:
        # print(url)
        try:
            filename = os.path.join(download_folder, url.split('/')[-1])
            print(filename)
            response = requests.get(url, timeout=300, verify=False)
            with open(filename, 'wb') as file:
                file.write(response.content)
            new_file_path = os.path.join(nas_path, url.split('/')[-1])
            shutil.move(filename, new_file_path)
            print(new_file_path)
            new_path.append(new_file_path)
        except:
            continue
    return new_path

def read_df():
    # Define the path to the folder containing the CSV files
    folder_path = os.path.join(os.getcwd(),'csv_files')
    # Get a list of all CSV file paths in the folder
    csv_files = glob.glob(folder_path + '/*.csv')
    # Initialize an empty list to store the individual DataFrames
    dfs = []
    # Iterate over each CSV file 
    for file in csv_files:
        try:
            # Read the CSV file into a DataFrame
            df = pd.read_csv(file)
            # Append the DataFrame to the list
            dfs.append(df)
        except:
            continue
    # Concatenate the list of DataFrames into a single DataFrame, considering duplicates for 'bid_no'
    merged_data = pd.concat(dfs, ignore_index=True, verify_integrity=True)
    merged_data['bid_no_1'] = merged_data['BID NO'].str.replace("/", "_")
    # filtered_df = merged_data[~merged_data['new_itm'].str.contains('DSLR', case=False, regex=False)]
    # Write the merged data to a new CSV file
    merged_data.to_csv('merged_data.csv', index=False)
    return merged_data


def extract_tables_from_pdf(pdf_path):
    d = {
        'Bid End Date': None,
        'Department Name': None,
        'Item Category': None,
        'Estimated Bid Value': None,
        'EMD Amount': None,
        'Pre-Bid Date': None,
        'location': None
    }
    # l = []
    with pdfplumber.open(pdf_path) as pdf:
        # Iterate over all pages in the PDF
        for page_number in range(len(pdf.pages)):
            page = pdf.pages[page_number]
            # Extract tables from the page
            tables = page.extract_tables()
            # Iterate over extracted tables
            for table_number, table in enumerate(tables):
                # print(f"Page {page_number + 1}, Table {table_number + 1}:")
                if table is not None:
                    # Iterate over rows in the table
                    for row in table:
                        try:
                            if "Bid End Date" in row[0]:
                                print(row)
                                d['Bid End Date'] = row[1]
                            elif 'Department Name' in row[0]:
                                print(row)
                                d['Department Name'] = str(row[1]).replace('\n',' ')
                            elif 'Item Category' in row[0]:
                                print(row)
                                d['Item Category'] = str(row[1]).replace('\n',' ')
                            elif 'Estimated Bid Value' in row[0]:
                                print(row)
                                d['Estimated Bid Value'] = str(row[1]).replace('\n','')
                            elif 'EMD Amount' in row[0]:
                                print(row)
                                d['EMD Amount'] = str(row[1]).replace('\n','')
                            elif 'Pre-Bid Date and Time' in row[0]:
                                d['Pre-Bid Date'] = table[1][0]
                            elif len(row) > 2 and 'Address' in row[2]:
                                d['location'] = str(table[1][2]).replace('\n',' ').replace('*','')
                        except:
                            pass
    return d

def check_db(data):
    tender_ids = data['bid_no_1'].to_list()
    query = f"SELECT tender_id, submission_date FROM tender.tender_management WHERE tender_id in {tuple(tender_ids)};"
    db_data = db.get_row_as_dframe(query) 
    np_db = data[~data['bid_no_1'].isin(db_data['tender_id'].tolist())] 
    np_db.drop('Unnamed: 0', axis=1)
    p_db_1 = data[data['bid_no_1'].isin(db_data['tender_id'].tolist())]
    p_db_2 = p_db_1[['bid_no_1', 'End Date']]
    db_data = db_data.rename(columns={'tender_id': 'bid_no_1', 'submission_date': 'End Date'})
    new_df = p_db_2.merge(db_data, how='outer', indicator=True)
    new_df = new_df[new_df['_merge']=='left_only']
    new_df.drop('_merge', axis=1)
    p_db = new_df
    try:
        check_cor = data[~data['bid_no_1'].isin(np_db['bid_no_1'].tolist())]
        check_cor = check_cor[~check_cor['bid_no_1'].isin(p_db['bid_no_1'].tolist())]
    except:
        check_cor = pd.DataFrame()
    return np_db, p_db, check_cor


def main():
    print('Starting the bot')
    data = read_df()
    np_db, p_db, check_cor = check_db(data)
    if not p_db.empty:
        p_list = []
        for _, row in p_db.iterrows():
            # if row['bid_no_1'] == 'GEM_2024_B_5040970':
            #     break
            list_of_tend = []
            query = f"""update tender.tender_management set submission_date = '{row['End Date']}', done = 'New-Corrigendum', user_id = 'GEM BOT' where tender_id = '{row['bid_no_1']}' """
            db.execute(query)
            print(row['bid_no_1'])
            p_list.append(row['bid_no_1'])
        to_add = ['raman@shreenathgroup.in']
        to_cc = ['ramit.shreenath@gmail.com']
        sub = 'Submission date Updated'
        body = f"""
        Hello Team,

        Below is the list of tenders, which have updated submission date,
        \n
        \n
        {p_list}
        \n
        \n
        Thanks,
        GEM BOT
        """
        mail.send_mail(to_add, to_cc, sub, body)
    if np_db.empty:
        return None
    driver = webdriver.Chrome(options=chrome_options)
    driver.get('https://bidplus.gem.gov.in/all-bids')
    t_dict = {}
    for _, row in np_db.iterrows():
        print(row['BID NO'])
        print(1)
        try:
            wi.processing_check_wait(driver, xpath='//*[@id="searchBid"]', time=300)
            bid_search = driver.find_element(By.XPATH, '//*[@id="searchBid"]')
            bid_search.click()
            bid_search.clear()
            bid_search.send_keys(row['BID NO'])
            bid_search_press = driver.find_element(By.XPATH, '//*[@id="searchBidRA"]')
            bid_search_press.click()
            wi.processing_check_wait(driver, cls='card', time=10)
            try:
                bid_file = driver.find_element(By.XPATH, f'''//*[contains(text(),"{row['BID NO']}")]''')
                # bid_file = driver.find_element(By.XPATH, f'''//*[contains(text(),"GEM/2025/B/5847516")]''')
                bid_file.click()
                bids_page_data = driver.find_elements(By.CLASS_NAME, "card")
                # nas_path = os.path.join(os.getcwd(), 'NAS', str(row['bid_no_1']))
                nas_path = os.path.join(r'E:\Files_dump', str(row['bid_no_1']))
                # nas_path = os.path.join(r'E:\Files_dump', 'GEM_2025_B_5847516')
                # nas_path = os.path.join(r'E:\Files_dump', 'er')
                # nas_path = os.path.join(r'/abcd/tender_auto', 'testing_1')
                check_folder = os.makedirs(nas_path, exist_ok=True)
                time.sleep(5)
                # try:
                #     os.rmdir(download_folder)
                #     os.makedirs(os.path.join(os.getcwd(), 'downloads'))
                # except:
                #     pass
                tables_of_gem = {
                                'Bid End Date': None,
                                'Department Name': None,
                                'Item Category': None,
                                'Estimated Bid Value': None,
                                'EMD Amount': None,
                                'Pre-Bid Date': None,
                                'location': None
                            }
                try:
                    tries = 0
                    while tries < 10:
                        tries += 1
                        try:
                            latest_file = get_latest_downloaded_file('pdf')
                            tables_of_gem = extract_tables_from_pdf(latest_file)
                            f_name = os.path.basename(latest_file)
                            urls = extract_links_from_pdf(latest_file)
                            new_file_path = os.path.join(nas_path, f_name)
                            shutil.move(latest_file, new_file_path)
                            pdf_links = [url['uri'] for url in urls if url['uri'].lower().endswith(('.pdf', '.xls', '.xlsx', '.docx', '.doc', '.csv'))]
                            try:
                                new_paths_to_NAS = download_files(pdf_links, download_folder, nas_path)
                                # body = f'Hello Team,\nBelow are the file path when pdf files are donwload and move by bot.\n{new_paths_to_NAS}\n\nThanks,\nGem Bot'
                                # mail.send_mail(to_add=['preetinder@digital-dreams.in'], to_cc=['ramit.shreenath@gmail.com'], sub=f'Files path for tender id {new_paths_to_NAS}', body=body)
                            except Exception as err:
                                print(f"Error in download pdfs, Error: {str(err)}")
                            os.rmdir(download_folder)
                            os.makedirs(os.path.join(os.getcwd(), 'downloads'))
                            break
                        except:
                            time.sleep(5)
                except:
                    pass
                inserted_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                user_id = username = 'GEM BOT'
                link = 'https://bidplus.gem.gov.in/'
                pbm_date = datetime.datetime.strptime(tables_of_gem['Pre-Bid Date'], '%d-%m-%Y %H:%M:%S').strftime('%Y-%m-%d %H:%M') if tables_of_gem['Pre-Bid Date'] else ''
                query = f"""INSERT INTO tender.tender_management (local_tender_id, tender_id, customer, name_of_work,
                submission_date, link, file_location, folder_location, inserted_time, user_id, inserted_user_id, publish_date,
                verification_1, file_name, "location", pbm, emd) 
                VALUES ('{str(row['bid_no_1'])}','{str(row['bid_no_1'])}', '{str(row['Department Name And Address']).replace("'","''")}',
                '{str(row['new_itm']).replace("'","''")}', '{str(row['End Date'])}', '{link}', '{new_file_path}',
                '{nas_path}', '{inserted_time}', '{user_id}', '{username}', '{str(row['Start Date'])}', 'FOR UPDATE', '{str(f_name)}',
                '{str(tables_of_gem['location'])}', '{pbm_date}', '{str(tables_of_gem['EMD Amount'])}');"""
                db.execute(query)
                emd_dict = {
                    "tender_id": str(row['bid_no_1']),
                    "emd_required": "YES" if tables_of_gem['EMD Amount'] else "NO",
                    "emd_form": None,
                    "emd_amount": tables_of_gem['EMD Amount'] if tables_of_gem['EMD Amount'] else '0',
                    "in_favour_of": None,
                    "mail_to_fin": None,
                    "remarks": "EMD Details Not Inserted",
                    "time_stamp": datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")
                }
                db.insert_dict_into_table("tender.tender_emd", emd_dict)
                folder_dict = {
                    "tender_id": str(row['bid_no_1']),
                    "current_time_col": inserted_time,
                    "user_id": user_id
                }
                db.insert_dict_into_table("tender.tender_folder", folder_dict)
                try:
                    ass_name = 'BOT'
                    check_query_tat = f""" select t_id from tender.tender_tat where t_id = '{str(row['bid_no_1'])}' ; """
                    check_data_tat = db.get_data_in_list_of_tuple(check_query_tat)
                    if not check_data_tat:
                        tat_query = f"""INSERT INTO tender.tender_tat (t_id, stage, status, assign_time, assign_to, ext_col_1)
                                        VALUES ('{str(row['bid_no_1'])}', 'FOR UPDATE', 'Open', NOW(), '{ass_name}', '{username}'); """
                        db.execute(tat_query)
                except Exception as err:
                    print(err)
                    pass
                try:
                    t_dict[row['bid_no_1']] = str(f_name)
                except:
                    pass
            except Exception as e:
                print(str(e))
                raise Exception(f"Portal Loading error for {row['bid_no_1']}")
        except Exception as err:
            print(str(err))
            body = f'''Hello Team,\n\nBelow error found\nError:{str(err)}\n\n\nThanks,GEM BOT'''
            mail.send_mail(to_add=['ramit.shreenath@gmail.com'], to_cc=[],sub='Error in Gem Portal', body=body)
            pass
    try:
        mail.send_mail(to_add=['ramit.shreenath@gmail.com'], to_cc=[], sub=f'GEM Inserted Tenders {datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")}', body=t_dict)
    except:
        pass
    try:
        driver.close()
    except:
        pass

def job():
    try:
        main()
    except Exception as e:
        print(str(e))
        pass
    print('BOT executed at 5:00 AM and 1:00 PM')


if __name__ == '__main__':
    schedule.every().day.at('05:00').do(job)
    schedule.every().day.at('12:57').do(job)
    # schedule.every().day.at('13:46').do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)

