import requests
import json

url = "http://whatsapp.zillion.io/api/v1/message/create"

headers = {
'Username': 'ashish@shreenathgroup.in',
'Password': '*******',
'Content-Type': 'application/json',
'Authorization': 'Basic *************************'
}

def send_otp_via_wp(mob, otp):
    # Replace this with your existing send_mail function
    body = f'Your login OTP is: {otp}'

    payload = json.dumps({
    "receiverMobileNo": mob.replace("+91",""),
    "message": [body]
    })

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        return True
    return False


def send_wp_msg(mob, msg):
    payload = json.dumps({
        "receiverMobileNo": mob.replace("+91",""),
        "message": [msg]
    })

    response = requests.request("POST", url, headers=headers, data=payload)

    if response.status_code == 200:
        return True
    return False
    pass

def send_msg_in_group(group_id=None, msg=None):
    # import requests
    # import json
    try:
        if not group_id:
            group_id = "120363303624388047@g.us"
            group_id = "120363162363027722@g.us"
        if not msg:
            msg = 'Testing msg'
        id = group_id.replace('@','%40')
        url = f'http://whatsapp.zillion.io/api/v1/message/create?username=ashish%40shreenathgroup.in&password=*******&recipientIds={id}&message={msg}'

        response = requests.request("GET", url)

        print(response.text)
    except:
        pass

