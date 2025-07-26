import pytesseract
from PIL import Image
import PIL.Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import os
import time
import json
import db_connect as db
import mail
from fuzzywuzzy import fuzz
import web_interface as wi
import datetime
import send_wp

# Set the path to the Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Set up Chrome options for downloads
chrome_options = Options()
chrome_options.add_argument('--start-maximized')

# Define the download folder path
download_folder = os.path.join(os.getcwd(), 'all_downloads')
prefs = {
    'download.default_directory': download_folder,
    'download.prompt_for_download': False,
    'download.directory_upgrade': True,
    'safebrowsing.enabled': False
}

ins_by = 'GEM Submit Details BOT'

# driver = webdriver.Chrome(options=chrome_options)

def get_captcha_text(captcha_element):
    captcha_screenshot = captcha_element.screenshot_as_png

    with open('captcha.png', 'wb') as file:
        file.write(captcha_screenshot)

    captcha_image = Image.open('captcha.png')

    captcha_text = pytesseract.image_to_string(captcha_image, config='--psm 7')

    captcha_text = ''.join(c for c in captcha_text if c.isalnum())

    return captcha_text
    pass

def login():
    driver = webdriver.Chrome(options=chrome_options)
    driver.get('https://sso.gem.gov.in/ARXSSO/oauth/doLogin')
    c = 0
    while c < 5:
        c += 1
        user_id = driver.find_element(By.XPATH, '//*[@id="loginid"]')
        user_id.clear()
        user_id.click()
        user_id.send_keys("sentmhl2")

        captcha_element = driver.find_element(By.XPATH, '//*[@id="captcha1"]')
        c_data = get_captcha_text(captcha_element)

        captcha = driver.find_element(By.XPATH,'//*[@id="captcha_math"]')
        captcha.click()
        captcha.clear()
        captcha.send_keys(c_data)
        time.sleep(5)

        submit_btn = driver.find_element(By.XPATH, '//*[@id="arxLoginSubmit"]')
        submit_btn.click()

        try:
            password = driver.find_element(By.XPATH, '//*[@id="password"]')
            password.click()
            password.clear()
            # password.send_keys("December2024@")
            password.send_keys("Shreenath@2025")
            break
        except:
            time.sleep(5)
            driver.find_element(By.XPATH,'//*[@id="loginFrm"]/div[2]/div[1]/div[3]/img').click()

        if c == 5:
            mail.send_mail(to_add=['ramit.shreenath@gmail.com'], to_cc=[], sub='Gem Portal is not working for login', body='')
            return None

    loginButton = driver.find_element(By.XPATH, '//*[@id="arxLoginSubmit"]')
    loginButton.click()
    return driver

def view_bid_result(driver):
    data = []
    try:
        try:
            driver.find_element(By.XPATH, '//*[@id="bidCard"]/div[2]/div[3]/div[2]/div[2]/p/a[1]/input').click()
        except:
            return False
        driver.switch_to.window(driver.window_handles[1])
        time.sleep(2)
        driver.find_element(By.XPATH, "//a[contains(text(),'2. TECHNICAL EVALUATION')]").click()
        time.sleep(2)
        # table_h = driver.find_element(By.XPATH,'//*[@id="collapseTwo"]/div/div/div/div[1]/div/div/table/thead').text
        # table_b = driver.find_element(By.XPATH,'//*[@id="collapseTwo"]/div/div/div/div[1]/div/div/table/tbody').text.split('\n')
        print('get table body')
        data = []
        c = 0
        slr_names = []
        for row in range(50):
            data_1 = {}
            print(f'C = {c}')
            try:
                data_1['sl_no'] = str(driver.find_element(By.XPATH,f'//*[@id="collapseTwo"]/div/div/div/div[1]/div/div/table/tbody/tr[{c}]/td[1]').text).strip()
                time.sleep(2)
                data_1['sl_no'] = str(driver.find_element(By.XPATH,f'//*[@id="collapseTwo"]/div/div/div/div[1]/div/div/table/tbody/tr[{c}]/td[1]').text).strip()
                print(data_1)
                data_1['slr_name'] = str(driver.find_element(By.XPATH,f'//*[@id="collapseTwo"]/div/div/div/div[1]/div/div/table/tbody/tr[{c}]/td[2]').text).strip()
                data_1['ofr_item'] = str(driver.find_element(By.XPATH,f'//*[@id="collapseTwo"]/div/div/div/div[1]/div/div/table/tbody/tr[{c}]/td[3]').text).strip().replace("\n", ", ")
                data_1['paert_on'] = str(driver.find_element(By.XPATH,f'//*[@id="collapseTwo"]/div/div/div/div[1]/div/div/table/tbody/tr[{c}]/td[4]').text).strip()
                data_1['emd_status'] = str(driver.find_element(By.XPATH,f'//*[@id="collapseTwo"]/div/div/div/div[1]/div/div/table/tbody/tr[{c}]/td[5]').text).strip()
                data_1['mse_mii_status'] = str(driver.find_element(By.XPATH,f'//*[@id="collapseTwo"]/div/div/div/div[1]/div/div/table/tbody/tr[{c}]/td[6]').text).strip()
                data_1['status'] = str(driver.find_element(By.XPATH,f'//*[@id="collapseTwo"]/div/div/div/div[1]/div/div/table/tbody/tr[{c}]/td[7]').text).strip()

                data.append(data_1)
                slr_names.append(data_1['slr_name'])
                time.sleep(2)
            except Exception as er:
                print('Error in 83')
                # print(str(er))
                pass
            c += 1
    except:
        print('Error in 89')
        try:
            driver.find_element(By.XPATH, "//*[contains(text(), '3. FINANCIAL EVALUATION')]")
        except:
            print('No FINANCIAL EVALUATION found')
            time.sleep(3)
    return data


def vie_ra_result(driver, ra=False, k=5):
    data = []
    try:
        if ra:
            driver.switch_to.window(driver.window_handles[0])
            try:
                driver.find_element(By.XPATH, '//*[@id="bidCard"]/div[2]/div[3]/div[2]/div[2]/p/a[2]/input').click()
            except:
                return False
            time.sleep(5)
            driver.switch_to.window(driver.window_handles[1])
            check_fin = '//*[@id="accordion"]/div[2]/div[1]/h4/a'
        else:
            check_fin = '//*[@id="accordion"]/div[3]/div[1]/h4/a'
        time.sleep(2)
        try:
            driver.find_element(By.XPATH, "//*[contains(text(), '3. FINANCIAL EVALUATION')]").click()
        except:
            driver.switch_to.window(driver.window_handles[2])
            driver.find_element(By.XPATH, "//*[contains(text(), '3. FINANCIAL EVALUATION')]").click()
        
        c = 0
        while c < 5:
            losqf = driver.find_element(By.XPATH, check_fin).get_attribute("aria-expanded")
            if losqf != 'true':
                driver.refresh()
                time.sleep(5)
                driver.find_element(By.XPATH, f'{check_fin}/i').click()
            else:
                break
            c += 1
        # table_b = driver.find_element(By.XPATH, '//*[@id="collapseThree"]/div/div/div/div/div/div/table/tbody').text.split('\n')
        data = []
        c = 0
        # slr_names = []
        for i in range(int(k)+1):
            if i == 0:
                continue
            print(i)
            data_1 = {}
            # c += 1
            try:
                data_1['slr_name'] = str(driver.find_element(By.XPATH, f'//*[@id="collapseThree"]/div/div/div/div/div/div/table/tbody/tr[{i}]/td[2]/span[1]').text).strip()
                time.sleep(2)
                print(data_1['slr_name'])
                data_1['slr_name'] = str(driver.find_element(By.XPATH, f'//*[@id="collapseThree"]/div/div/div/div/div/div/table/tbody/tr[{i}]/td[2]').text).strip()
                data_1['total_price'] = str(driver.find_element(By.XPATH, f'//*[@id="collapseThree"]/div/div/div/div/div/div/table/tbody/tr[{i}]/td[4]').text).replace('`','').strip()
                data_1['rank'] = str(driver.find_element(By.XPATH, f'//*[@id="collapseThree"]/div/div/div/div/div/div/table/tbody/tr[{i}]/td[5]').text).strip()
                data.append(data_1)
                time.sleep(2)
            except:
                pass
        print(data)
    except Exception as er:
        print(f'Error : {er}')
        print('Error in Fin Eav')
        return False
    driver.close()
    return data

def get_bid_and_ra_details(driver, t_id):
    try:
        BID_result_list = view_bid_result(driver)
        driver.switch_to.window(driver.window_handles[0])
        try:    
            ra_no = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[1]/p[3]/a').text
        except:
            try:
                ra_no = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[6]/div[1]/p[3]/a').text
            except:
                ra_no = "No Data"
        RA_result_list = []
        if ra_no != 'No Data':
            RA_result_list = vie_ra_result(driver, True, len(BID_result_list) if BID_result_list else 0)
        else:
            try:
                driver.switch_to.window(driver.window_handles[1])
            except:
                driver.switch_to.window(driver.window_handles[0])
            RA_result_list = vie_ra_result(driver, False, len(BID_result_list) if BID_result_list else 0)
        try:
            wh = driver.window_handles
            # num_windows = len(window_handles)
            for i in range(1,len(wh)+1):
                driver.switch_to.window(driver.window_handles[i])
                driver.close()
        except:
            pass
        driver.switch_to.window(driver.window_handles[0])

        d2_mapping = {item['slr_name'].split('(')[0].strip(): {'total_price': item['total_price'], 'rank': str(item['rank']).split('\n')[0]} for item in RA_result_list}
        result = []

        # Define a minimum similarity score for matching
        min_similarity_score = 90  # You can adjust this threshold as needed

        for item in BID_result_list:
            item['tender_id'] = t_id.replace('/','_')
            slr_name = item['slr_name']

            # Find the best match in d2_mapping based on similarity score
            best_match = None
            best_score = 0

            for d2_name, d2_data in d2_mapping.items():
                score = fuzz.partial_ratio(slr_name, d2_name)
                if score > best_score and score >= min_similarity_score:
                    best_match = d2_name
                    best_score = score

            if best_match:
                item.update(d2_mapping[best_match])
            else:
                item['total_price'] = '0.00'
                item['rank'] = 'NA'
            result.append(item)

        return result
    except:
        return None

def clar_hist(driver):
# clarification history>>>>>>>>>>>>>>>>>>>>>>
    try:
        try:
            c_h_p = driver.find_element(By.XPATH, "//*[text()='Clarification History: ']")
        except:
            c_h_p = False
        if not c_h_p:
            clar_hist={}

        clar_hist = driver.find_element(By.XPATH, '//a[@class="clarification_history"]')
        clar_hist.click()

        clar_data = []
        data_3 = {}
        try:
            time.sleep(10)
            try:
                read_more = driver.find_element(By.XPATH, "//*[text()='(Read more)']")
            except:
                read_more = None
            if read_more:
                read_more.click()
            data_3['type'] = str(driver.find_element(By.XPATH, f'//*[@id="showClarificationBox"]/table/tbody/tr[1]/td').text).strip()
            data_3['clar_descrp'] = str(driver.find_element(By.XPATH, f'//*[@id="showClarificationBox"]/table/tbody/tr[2]/td').text).strip()
            try:
                data_3['sta'] = str(driver.find_element(By.XPATH, f'//*[@id="showClarificationBox"]/table/tbody/tr[3]/td/span').text).strip()
            except:
                data_3['sta'] = str(driver.find_element(By.XPATH, f'//*[@id="showClarificationBox"]/table[1]/tbody/tr[4]/td').text).strip()
                
            data_3['req_intiated_at'] = str(driver.find_element(By.XPATH, f'//*[@id="showClarificationBox"]/label/span').text).replace("Request Initiated At:", " ").strip()
            try:
                data_3['slr_resp_desc'] = str(driver.find_element(By.XPATH, f'//*[@id="showClarificationBox"]/table[1]/tbody/tr[5]/td').text).strip()
            except:
                pass

            clar_data.append(data_3)

            cncl_btn = driver.find_element(By.XPATH, '//*[@id="showModalCloseBtn"]')
            cncl_btn.click()
            return clar_data
        except Exception as er:
            print('Error in 43')
            return {}
    except:
        try:
            cncl_btn = driver.find_element(By.XPATH, '//*[@id="showModalCloseBtn"]')
            cncl_btn.click()
        except:
            pass
        return {}

def rep_hist(driver):
    try:
        try:
            r_h_p = driver.find_element(By.XPATH, "//*[text()='Representation History: ']")
        except:
            r_h_p = False
        if not r_h_p:
            rep_hist={}

        rep_hist = driver.find_element(By.XPATH, '//a[@class="representation_history"]')
        rep_hist.click()

        rep_data = []
        data_4 = {}
        try: 
            time.sleep(10)
            try:
                read_more = driver.find_element(By.XPATH, "//*[text()='(Read more)']")
            except:
                read_more = None
            if read_more:
                read_more.click()
            data_4['rep_descrp'] = str(driver.find_element(By.XPATH, f'//*[@id="showRepresentationBox"]/table/tbody/tr[1]/td').text).strip()
            data_4['rep_status'] = str(driver.find_element(By.XPATH, f'//*[@id="showRepresentationBox"]/table/tbody/tr[3]/td/span').text).strip()
            data_4['rep_respnd'] = str(driver.find_element(By.XPATH, f'//*[@id="showRepresentationBox"]/table/tbody/tr[4]/td').text).strip()
            data_4['rspn_descrp'] = str(driver.find_element(By.XPATH, f'//*[@id="showRepresentationBox"]/table/tbody/tr[5]/td').text).strip().replace('(Read less)', '')
            data_4['rep_int_at'] = str(driver.find_element(By.XPATH, f'//*[@id="showRepresentationBox"]/label/span').text).split(":")[1].strip()

            rep_data.append(data_4)
            
            cncl_btn = driver.find_elements(By.XPATH, "//*[@id='showModalCloseBtn' and @class='close']")
            cncl_btn[1].click()
            return rep_data
        except Exception as er:
            print('Error in 63')
            pass
    except:
        try:
            cncl_btn = driver.find_elements(By.XPATH, "//*[@id='showModalCloseBtn' and @class='close']")
            cncl_btn[1].click()
        except:
            pass
        return {}


def get_bid_details(driver):
    try:
        try:
            bid_no = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[1]/p[1]/a').text
        except:
            bid_no = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[5]/div[1]/p[1]/a').text    
        try:
            items = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[3]/div/div[1]/div[1]/a').get_attribute('data-content')
        except:
            try:
                items = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[5]/div[3]/div[1]/div[1]/div[1]/a').get_attribute('data-content')
            except:
                items = driver.find_element(By.XPATH,'//*[@id="bidCard"]/div[2]/div[3]/div[1]/div[1]/div[1]').text.split('Items: ')[1]
        try:
            Dept_nm = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[3]/div/div[2]/div[2]').text.replace("NA", "").strip().replace('\n', ', ')
        except:
            Dept_nm = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[3]/div/div[2]/div[2]').text.replace("NA", "").strip().replace('\n', ', ')
        try:    
            qnty = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[3]/div/div[1]/div[2]').text.split(":")[1].strip()
        except:
            qnty = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[3]/div/div[1]/div[2]').text.split(":")[1].strip()
        try:
            strt_dt = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[3]/div/div[3]/div[1]/span').text
        except:
            strt_dt = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[5]/div[3]/div[1]/div[3]/div[1]/span').text
        try:
            end_dt = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[3]/div/div[3]/div[2]/span').text
        except:
            end_dt = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[5]/div[3]/div[1]/div[3]/div[2]/span').text
        try:
            status = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[1]/p[2]/span[1]').text
        except:
            status = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[1]/p[4]/span[1]').text
        try:
            bid_ra_status = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[1]/p[2]/span[2]').text
        except:
            bid_ra_status = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[1]/p[4]/span[2]').text

        try:
            tech_status = driver.find_element(By.XPATH, f"//*[text()='Technical Status:']/..").text.replace('Technical Status: ','')
        except:
            try:
                tech_status = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[5]/div[3]/div[1]/div[1]/div[3]/span').text
            except:
                tech_status = "No Data"

        try:    
            ra_no = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[2]/div[1]/p[3]/a').text
        except:
            try:
                ra_no = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[6]/div[1]/p[3]/a').text
            except:
                ra_no = "No Data"

        try:
            rep_rejecn = driver.find_element(By.XPATH, f"//*[text()='Representation/Challenge Rejection:']").text
        except:
            try:
                rep_rejecn = driver.find_element(By.XPATH, f'//*[@id="bidCard"]/div[4]/div[3]/div[1]/div[1]/div[4]').text
            except:
                rep_rejecn = "No Data"

        rep_his = rep_hist(driver)
        clr_his = clar_hist(driver)

        data = {
        't_id': bid_no.replace('/', '_'),
        'items': items,
        'dept_name': Dept_nm,
        'qnty': qnty,
        'strt_dt': strt_dt,
        'end_dt': end_dt,
        'status': status,
        'bid_ra_status': bid_ra_status,
        'tech_status': tech_status,
        'ra_no': ra_no,
        'rep_rejec':rep_rejecn,
        'rep_hist': rep_his  if rep_his else None,
        'clar_hist': clr_his if clr_his else None,
        'updated_by': ins_by,
        'updated_time': datetime.datetime.now()
        }

        # update_query = f" UPDATE tender.gem_res_details SET \
        #         items = '{data['items']}', dept_name = '{data['dept_name']}', qnty = '{data['qnty']}', strt_dt = '{data['strt_dt']}', end_dt = '{data['end_dt']}', \
        #         status = '{data['status']}', bid_ra_status = '{data['bid_ra_status']}', tech_status = '{data['tech_status']}', ra_no = '{data['ra_no']}', \
        #         rep_rejec = '{data['rep_rejec']}' "
        # if rep_his:
        #     update_query += f" , rep_hist = {data['rep_hist']}"
        # if clr_his:
        #     # update_query += f", clar_hist = jsonb_set('[]'::jsonb, '{{0}}', {data['clar_hist']})"
        #     # update_query += f", clar_hist = {data['clar_hist']}"
        #     update_query += f""", clar_hist = {{"{0}": {data['clar_hist']}}}"""

        # update_query +=  f""", updated_by = '{data['updated_by']}', updated_time = now() WHERE t_id = '{data['t_id']}'; """

        update_query = f"""
            UPDATE tender.gem_res_details
            SET
                items = '{data['items']}',
                dept_name = '{data['dept_name']}',
                qnty = '{data['qnty']}',
                strt_dt = '{data['strt_dt']}',
                end_dt = '{data['end_dt']}',
                status = '{data['status']}',
                bid_ra_status = '{data['bid_ra_status']}',
                tech_status = '{data['tech_status']}',
                ra_no = '{data['ra_no']}',
                rep_rejec = '{data['rep_rejec']}',
                rep_hist = '{{"0": {json.dumps(data['rep_hist'])}}}',
                clar_hist = '{{"0": {json.dumps(data['clar_hist'])}}}',
                updated_by = '{data['updated_by']}',
                updated_time = now()
            WHERE t_id = '{data['t_id']}';
        """


        db.execute(update_query)
        
        # db.insert_dict_into_table('tender.gem_res_details', data)

        return data
    except:
        return False

def pend_clar(driver,t_id):
    try:
        try:
            p_c = driver.find_element(By.XPATH, '//*[text()="Pending Clarifications: "]')
        except:
            p_c = False
        if not p_c:
            update_query = f"UPDATE tender.gem_res_details SET chk_pend_clr = 'NO' WHERE t_id = '{t_id}' ;"
            db.execute(update_query)
            return False

        pending_clarf = driver.find_element(By.XPATH, '//*[@class="pending_clarification" and text()="Click here to submit"]')
        pending_clarf.click()
        time.sleep(30)
        driver.save_screenshot('pending_clarf.png')

        to_add = ['ramit.shreenath@gmail.com', 'raman@shreenathgroup.in', 'ASHISH@shreenathgroup.in',  'preetinder@digital-dreams.in', 'gursimran@digital-dreams.in']
        sub = f'Pending Clarification of {t_id}'
        body = f"""
        Hello Team,

        Tender ID: {t_id}
        Pending clarification,
        Please check and do needfull.
        
        Thanks,
        GEM Check Clarification Bot
        """
        send_wp.send_msg_in_group(group_id='120363162363027722@g.us', msg=body)
        mail.send_mail(to_add=to_add, sub=sub, body=body, attach=[os.path.join(os.getcwd(), 'pending_clarf.png')])
        update_query = f"UPDATE tender.gem_res_details SET chk_pend_clr = 'YES' WHERE t_id = '{t_id}' ;"
        db.execute(update_query)
        name = f'Clarification: {t_id}'
        remarks = f""" A new pending clarification found for Tender ID: {t_id}, It is assign to Gurpreet Lamby"""
        insert_task(name,remarks)

    except Exception as er:
        update_query = f"""UPDATE tender.gem_res_details SET chk_pend_clr_err = '{str(er).replace("'", "''")}',chk_pend_clr = 'ERROR' WHERE t_id = '{t_id}' ;"""
        db.execute(update_query)
        
    cncl_btn = driver.find_element(By.XPATH, '//*[@id="pendingClarificationModal"]/div/div/div[1]/button')
    cncl_btn.click()

    return True

def rep_rejecn(driver,t_id):
    try:
        try:
            r_r = driver.find_element(By.XPATH, "//*[text()='Representation/Challenge Rejection:']")
        except:
            r_r = False
        if not r_r:
            update_query = f"UPDATE tender.gem_res_details SET chk_rep_rejecn = 'NO' WHERE t_id = '{t_id}' ;"
            db.execute(update_query)
            return None
        rep_rejecn = driver.find_element(By.XPATH, '//*[@class="challenge_rejection" and text()="Click here to submit"]')
        rep_rejecn.click()
        
        # time.sleep(5)
        c = 0
        while c < 5:
            c+=1
            print(c)
            try:
                check_text = driver.find_element(By.XPATH, '//*[@id="formSubmitRejectionChallenge"]/label[1]').text
                if check_text:
                    break
            except:
                pass
            time.sleep(3)

        driver.save_screenshot('rep_rejection.png')

        to_add = ['ramit.shreenath@gmail.com', 'raman@shreenathgroup.in', 'ASHISH@shreenathgroup.in', 'preetinder@digital-dreams.in', 'gursimran@digital-dreams.in']
        sub = f'Representation/Challenge Rejection {t_id}'
        body = f"""
        Hello Team,
        Tender ID: {t_id}
        Representation/Challenge Rejection,
        Please check and do needfull.
        
        Thanks,
        GEM Check Representation Bot
        """
        send_wp.send_msg_in_group(group_id='120363162363027722@g.us', msg=body)
        mail.send_mail(to_add=to_add, sub=sub, body=body, attach=[os.path.join(os.getcwd(), 'rep_rejection.png')])

        update_query = f"UPDATE tender.gem_res_details SET chk_rep_rejecn = 'YES' WHERE t_id = '{t_id}' ;"
        db.execute(update_query)
        name = f'Representation/Challenge Rejection: {t_id}'
        remarks = f""" A new Representation/Challenge Rejection found for Tender ID: {t_id}, It is assign to Gurpreet Lamby."""
        insert_task(name,remarks)


    except Exception as er:
        update_query = f"UPDATE tender.gem_res_details SET chk_rep_rejecn_err = '{str(er)}', chk_rep_rejecn = 'ERROR' WHERE t_id = '{t_id}' ;"
        db.execute(update_query)
    cncl_btn = driver.find_element(By.XPATH, '//*[@id="challengeRejectionModal"]/div/div/div[1]/button')
    cncl_btn.click()

    return True

def tender_processing(driver, t_id):
# Search Logic ==========================================
    driver.find_element(By.XPATH, '//*[@id="participatedBids"]').click()
    cont = driver.find_element(By.XPATH, '//*[@id="searchBid"]')
    cont.click()
    cont.clear()
    # t_id = 'GEM/2023/B/4253301'
    cont.send_keys(t_id.replace('_', '/'))
    #GEM/2023/B/4075839 BID nd RA
    #GEM/2023/B/3911856 BID nd RA
    #GEM/2023/B/4033455 BID nd RA
    #GEM/2023/B/4034597 for rep rej mail checking
    # GEM/2021/R/58864
    # GEM/2023/B/3933891
    # GEM/2023/B/4033455
    # GEM/2023/B/4026527
    cont.send_keys(Keys.ENTER)
    time.sleep(10)
    # try:
    #     srch_bt = driver.find_element(By.XPATH, '//*[@id="searchBidRA"]')
    #     srch_bt.click()
    # except Exception as er:
    #     print(str(er))
    #     time.sleep(5)
# ========================================================
    bid_data = get_bid_details(driver)
    pend_clar(driver, t_id)
    rep_rejecn(driver, t_id)
    time.sleep(10)
    res = get_bid_and_ra_details(driver, t_id)
    if res:
        res_query = f""" UPDATE tender.gem_res_details SET
                    result_details = '{json.dumps(res)}'::jsonb,
                    updated_by = '{ins_by}',
                    updated_time = now()
                    WHERE t_id = '{t_id.replace('/','_')}'; """
        db.execute(res_query)

def ins_gem_table():
    t_id_query = "SELECT tender_id FROM tender.tender_management WHERE done = 'Submitted' and tender_id ilike 'gem%'; "
    temp = db.get_data_in_list_of_tuple(t_id_query)

    t_id_list = [i[0] for i in temp]

    for t_id in t_id_list:
        gem_res_query = f"SELECT sl_no FROM tender.gem_res_details WHERE t_id = '{t_id}' ;"
        result = db.get_data_in_list_of_tuple(gem_res_query)

        if not result:
            gem_insert_query = f"INSERT INTO tender.gem_res_details (t_id, inserted_by) VALUES ('{t_id}', '{ins_by}') ;"
            db.execute(gem_insert_query)

def log_check(driver):
    pass

def main():
    l = []
    query_no_closed = "SELECT t_id FROM tender.gem_res_details WHERE closed = 'NO'"
    temp = db.get_data_in_list_of_tuple(query_no_closed)

    t_id_no_closed = [row[0] for row in temp]

    driver = login()
    if not driver:
        return None
    time.sleep(10)
    
    for cnfm in range(5):    
        try:
            cnfm = driver.find_element(By.XPATH, "//a[text()='Ok']")
            cnfm.click()
        except:
            pass
        bids = driver.find_element(By.XPATH, '//a[@id="dLabel" and contains(text(),"Bids ")]')
        if bids:
            try:
                bids.click()
                break
            except:
                pass

    time.sleep(2)
    lob = driver.find_element(By.XPATH, '//*[@id="HEADER_DIV"]/section[3]/section/div/div/div[2]/ul/li[5]/ul/li/a')
    lob.click()

    p_bids = driver.find_element(By.XPATH, '//*[@id="participatedBids"]')
    p_bids.click()
    time.sleep(10)

    for t_id in t_id_no_closed:
        print(t_id)
        
        try:
            tender_processing(driver, t_id) 
        except:
            print(f'{t_id} error in main fun')
            try:
                driver.close()
            except:
                pass
            driver = login()
            if not driver:
                return None
            time.sleep(10)

            for cnfm in range(5):    
                try:
                    cnfm = driver.find_element(By.XPATH, "//a[text()='Ok']")
                    cnfm.click()
                except:
                    pass
                bids = driver.find_element(By.XPATH, '//a[@id="dLabel" and contains(text(),"Bids ")]')
                if bids:
                    try:
                        bids.click()
                        break
                    except:
                        pass

            time.sleep(2)
            lob = driver.find_element(By.XPATH, '//*[@id="HEADER_DIV"]/section[3]/section/div/div/div[2]/ul/li[5]/ul/li/a')
            lob.click()

            p_bids = driver.find_element(By.XPATH, '//*[@id="participatedBids"]')
            p_bids.click()
            time.sleep(10)
        l.append(t_id)
    return l

def make_no():
    query= """update tender.gem_res_details set closed = 'YES' where t_id in (
                select tender_id from tender.tender_management where done ilike '%close%' and tender_id in (
                    select t_id from tender.gem_res_details where closed = 'NO')); """
    db.execute(query)
    return query

def insert_task(name,remarks):
    t_name = name
    s_id = 'S001'
    # ex_end_dt = datetime.datetime.strptime(str(datetime.datetime.now()), '%Y-%m-%dT%H:%M')
    ex_end_dt = datetime.datetime.now()
    assign_id = 3
    # assign_details = db.get_data_in_list_of_tuple(f"""select * from tms.login_details ld where id = {assign_id};""")
    assign_to = 'U-6-Preetender Kaur'
    assign_email = 'preetinder@digital-dreams.in'
    assign_mobile = '7986852781'
    priority = 'High'
    assign_by = 'Raman Dua'
    assign_dt = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    remark = remarks
    
    latest_t_id_tuple = db.get_data_in_list_of_tuple("SELECT t_id FROM tms.task_assign ORDER BY t_id DESC LIMIT 1;")
    if latest_t_id_tuple:
        latest_t_id = latest_t_id_tuple[0][0]
        next_number = int(latest_t_id.split('-')[1]) + 1
        next_t_id = f"T-{next_number:04d}"
    else:
        next_t_id = 'T-0001'
    inserted_dt = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    inserted_by = 'GEM Cler BOT'
    insert_query = f"""
    INSERT INTO tms.task_assign (t_id, t_name, s_id, start_dt, ex_end_dt, assign_to,
    priority, assign_by, assign_dt, remark,inserted_dt, inserted_by)
    VALUES ('{next_t_id}', '{t_name}', '{s_id}', now(),'{ex_end_dt}', '{assign_to}', 
    '{priority}', '{assign_by}', '{assign_dt}', '{remark}', '{inserted_dt}','{inserted_by}' );"""
    print(insert_query)
    check_query = f"""select count(*) from  tms.task_assign where t_name='{name}' and status in ('Open', 'WIP'); """
    check_data = db.get_data_in_list_of_tuple(check_query)
    if check_data and check_data[0][0] == 0:
        print(insert_query)
        success = db.execute(insert_query)

        sub = f'New Task Assign, Task ID: {next_t_id}'
        to_add = [assign_email]
        to_cc = ['raman@shreenathgroup.in','ramit.shreenath@gmail.com','ashish@shreenathgroup.in']
        body = f"""
        Hello {assign_to},
        
        A new task has been assigned by you. Please check it by login in to our portal.
        ID : {next_t_id},
        Task: {t_name},
        Priority: {priority}

        Thanks,
        Task Management System
        (GEM CLR BOT)
        """
        mail.send_mail(to_add=to_add, to_cc=to_cc, sub=sub, body=body)


if __name__ == "__main__":
    while True:
        print('BOT is started')
        try:
            ins_gem_table()
            make_no()
            l = main()
        except Exception as err:
            sub='Gem Portal Error in main fun'
            body=f'''Hello Ramit,\n\nThere is an error in GEM BOT\nError: {str(err)}\n\n\nthanks,\nGEM BOT'''
            mail.send_mail(to_add=['ramit.shreenath@gmail.com'], to_cc=[],sub=sub,body=body)
        print('BOT will start after 12 hours')
        time.sleep(43200)
