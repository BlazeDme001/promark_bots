import db_connect as db
import schedule
import time


def main():
    query = """ update tender.tender_management set verification_1 = 'rejected', user_id = 'Set Reject BOT' where
    tender_id in (select tender_id from tender.tender_management where submission_date :: date < current_date - 9 
    and submission_date  <> '' and submission_date is not null and verification_1 in ('pre_approved','FOR UPDATE', '') 
    and (done not in ('Submitted', 'Close-WIN', 'Close-LOSE', 'Close-Cancel') or done is null)); """

    db.execute(query)


def job():
    main()
    print('BOT executed at 2:00 AM')


if __name__ == '__main__':
    schedule.every().day.at('02:00').do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)

