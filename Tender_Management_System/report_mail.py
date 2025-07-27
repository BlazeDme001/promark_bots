import db_connect as db
import datetime
import pandas as pd
import os
import mail
import schedule
import time

os.makedirs(os.path.join(os.getcwd(),'report_csv'), exist_ok=True)
folder_path = os.path.join(os.getcwd(),'report_csv')


def summery_report():
    ins_query = f"""SELECT COUNT(*) AS tender_count
                    FROM tender.tender_management 
                    WHERE TO_DATE(inserted_time, 'DD-MM-YYYY HH24:MI:SS')::date >= current_date - 7;"""
    try:
        ins_data = db.get_row_as_dframe(ins_query)
    except:
        ins_data = pd.DataFrame({'tender_count': [0]})
    sum_query = """
                WITH latest_status AS (SELECT tender_id, done, verification_1, lose_state, change_timestamp,
                        ROW_NUMBER() OVER (PARTITION BY tender_id ORDER BY change_timestamp DESC) AS rn
                    FROM tender.tender_management_history
                    WHERE change_timestamp >= current_date - 7
                )SELECT verification_1 as "Stage", done as "Status", lose_state as "Lose Reason", COUNT(*) AS "tender_count"
                FROM latest_status
                WHERE rn = 1
                GROUP BY done, verification_1, lose_state
                ORDER BY tender_count DESC;
                """
    try:
        sum_data = db.get_row_as_dframe(sum_query)
    except:
        sum_data = pd.DataFrame(columns=['Stage', 'Status', 'Lose Reason', 'tender_count'])

    try:
        # Adding a new column to `ins_data` for consistency
        ins_data['Stage'] = 'Inserted'
        ins_data['Status'] = 'Open'
        ins_data['Lose Reason'] = None

        # Ensure column order matches
        ins_data = ins_data[['Stage', 'Status', 'Lose Reason', 'tender_count']]

        # Combine the DataFrames
        df = pd.concat([ins_data, sum_data], ignore_index=True)
        print(df.sort_values(by=['Stage', 'Status']))
    except Exception as e:
        print(f"Error combining DataFrames: {e}")
        df = pd.DataFrame([],columns=['Stage', 'Status', 'Lose Reason', 'tender_count'])
    return df.sort_values(by=['Stage', 'Status'])


def send_report_mail(path):
    # table_html = report_df.to_html(index=False, border=1, justify="center")
    # table_str = report_df.to_string(index=False)
    sub = 'Weekly reports of Tenders'
    body = f"""Hello Team,\nBelow is the summery report of tenders.\n\n\n\nThanks,\nTender Report BOT """
    # to = ['ramit.shreenath@gmail.com']
    to = ['ramit.shreenath@gmail.com']
    cc = []
    
    # attach = [paths[0], paths[1], paths[2], paths[3], paths[4]]
    # attach = paths
    mail.send_mail(to_add=to, to_cc=cc, sub=sub,body=body, attach=path)



def main():
    report_df = summery_report().reset_index(drop=True)
    report_df.index = report_df.index + 1
    file_path = os.path.join(folder_path, 'summery_report.csv')
    report_df.to_csv(file_path, index=True)
    # report_df.to_csv('test.csv', index=True)

    send_report_mail(file_path)
    try:
        os.remove(file_path)
        print(f"File {file_path} deleted successfully.")
    except FileNotFoundError:
        print(f"File {file_path} not found.")
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")


schedule.every().saturday.at("09:00").do(main)

if __name__=='__main__':
    while True:
        schedule.run_pending()
        time.sleep(60) 

