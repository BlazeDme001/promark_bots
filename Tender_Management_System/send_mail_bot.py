import pandas as pd
import db_connect as db
import mail
import schedule
import time

def check_send_mail():
    query = """update tender.tender_management set mail_send ='Y' where tender_id in (
        select tender_id from tender.tender_management where (mail_send <> 'Y' or mail_send is null) 
        and verification_1 not in ('approved', 'rejected')) returning tender_id;"""
    data = db.get_row_as_dframe(query)
    if data.empty:
        return print('No data')
    to = ['ramit.shreenath@gmail.com', 'sentmhl@gmail.com']
    cc = None
    sub = "List of Newly inserted tender"
    body = f"""
    Hello Team,

    URL: http://192.168.0.16:5010/tenders/

    Below list is the newly inserted tenders:
    {data['tender_id']}

    Thanks,
    Tender Mail Send BOT
    """
    mail.send_mail(to_add=to, to_cc=cc, sub=sub, body=body)
    return None

# Schedule the check_send_mail function to run every day at 8:00 AM
schedule.every().day.at("12:32").do(check_send_mail)

# Continuously run the scheduler
while True:
    schedule.run_pending()
    time.sleep(1)
