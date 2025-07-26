import requests
import json

url = "http://whatsapp.zillion.io/api/v1/message/create"

headers = {
'Username': 'ashish@shreenathgroup.in',
'Password': 'banbhori0031',
'Content-Type': 'application/json',
'Authorization': 'Basic YXNoaXNoQHNocmVlbmF0aGdyb3VwLmluOmJhbmJob3JpMDAzMQ=='
}

def send_otp_via_wp(mob, otp):
    # # Replace this with your existing send_mail function
    # body = f'Your login OTP is: {otp}'

    # payload = json.dumps({
    # "receiverMobileNo": mob.replace("+91",""),
    # "message": [body]
    # })

    # response = requests.request("POST", url, headers=headers, data=payload)

    # if response.status_code == 200:
    #     return True
    # return False
    pass


def send_wp_msg(mob, msg):
    # payload = json.dumps({
    #     "receiverMobileNo": mob.replace("+91",""),
    #     "message": [msg],
        
    # })

    # response = requests.request("POST", url, headers=headers, data=payload)

    # if response.status_code == 200:
    #     return True
    # return False
    pass


def send_wp_attach(mob, msg, attach):
    payload = json.dumps({
        "receiverMobileNo": mob.replace("+91",""),
        "message": [msg],
        "ftpFilePathUrl": [attach],
        
    })

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        return True
    return False
