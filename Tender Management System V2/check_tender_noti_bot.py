import pandas as pd
import db_connect as db
import mail
import time


def get_tenders():
    tender_query = """select inserted_user_id from tender.tender_management tm 
            where inserted_time::timestamp >= current_date - 7 and inserted_user_id ilike '%bot'
            group by inserted_user_id ;"""
    tender_data = db.get_data_in_list_of_tuple(tender_query)
    tender_bot_list = [i[0] for i in tender_data]
    bot_list = [
        'HRYtenders GOV NICGEP BOT','GEM BOT','AndamanTenders GOV NICGEP BOT','TripuraTenders GOV NICGEP BOT',
        'JKDTenders GOV NICGEP BOT','Tntenders GOV NIC BOT','PBTenders GOV NICGEP BOT','Eprocuremdl Nic Nicgep BOT',
        'CHDTenders GOV NICGEP BOT','Iocletenders_NIC Nicgep BOT','Eprocurentpc Nic Nicgep BOT','Assam GOV NICGEP BOT',
        'UKtenders GOV NICGEP BOT','Coalindiatenders NIC Nicgep BOT','NagalandTenders GOV NICGEP BOT',
        'HPtenders GOV NICGEP BOT','Eproc Rajasthan GOV BOT','Mahatenders GOV BOT','Defproc Nicgep BOT',
        'DelhiTenders GOV NICGEP BOT','Eprocurehsl Nicgep BOT','LEHTenders GOV NICGEP BOT','SikkimTenders GOV NICGEP BOT',
        'LKDPTenders GOV NICGEP BOT','Eprocurebel Nicgep BOT','Centerl GOV BOT','Cpcletenders NIC Nicgep BOT',
        'GoaTenders GOV NICGEP BOT','Mptenders GOV BOT','DadrahaveliTenders GOV NICGEP BOT','J&KTenders GOV NICGEP BOT',
        'WBtenders GOV NICGEP BOT','Etenders UP NIC BOT','Etenders GOV BOT','Eprocuregrse Nicgep BOT',
        'KeralaTenders GOV NICGEP BOT','Eprocure Epublish BOT','APTenders NICGEP BOT','Pmgsytenders GOV Nicgep BOT',
        'Tendersodisha GOV BOT','PuducherryTenders GOV NICGEP BOT','ManipurTenders GOV NICGEP BOT', 'MeghTenders GOV NICGEP BOT',
        'MizoramTenders GOV NICGEP BOT','Mptenders GOV BOT','GEM BOT']
    np_list = [bot for bot in bot_list if bot not in tender_bot_list]
    
    sub = 'Tender not inserted in DB'
    body = f""" Hello Team,\n\nBelow is the list of tenders which is not inserted in DB since last 7 days.\n
    {np_list}\n\nPlease check and do the needful.\n\nThanks,\nTender Notification Bot\n"""
    to_add = ['ramit.shreenath@gmail.com','raman@shreenathgroup.in']
    to_cc = []
    mail.send_mail(to_add=to_add, to_cc=to_cc, sub=sub, body=body)


while True:
    get_tenders()
    time.sleep(259200)


