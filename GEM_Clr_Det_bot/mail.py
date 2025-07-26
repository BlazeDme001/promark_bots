import smtplib
from configparser import ConfigParser
import os
import yagmail


user_name = 'dme@shreenathgroup.in'
password = 'Blaze@456'

# to_add = ['hr@shreenathgroup.in']
# to_add = ['ramit.shreenath@gmail.com']
# to_cc = None

HOST = server = "SMTP.gmail.com"
PORT = 587

def send_mail(to_add=None, to_cc=None, sub=None, body=None, attach=[]):
    """attachment = os.path.join(os.getcwd(),'config.ini')"""
    try:
        yag = yagmail.SMTP(user_name, password)
        yag.send(to=to_add, cc=to_cc, subject=sub, contents=body, attachments=attach)
        yag.close()
        print('Mail Sent Successful')
        return True
    except:
        return False

