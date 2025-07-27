
from flask import Flask, request, render_template, redirect, url_for, send_file, session, make_response, jsonify, flash
import os
from werkzeug.utils import secure_filename
import paramiko
import db_connect as db
import requests
import logging
from tempfile import NamedTemporaryFile
import smtplib
from email.mime.text import MIMEText
from functools import wraps
import datetime
import mail
# import plotly.graph_objs as go
import json
import pandas as pd
import activity as act
import send_wp as wp

# ================= GLOBAL CONFIGURATION =================
LOCAL_BASE_FOLDER = r"E:\Files_dump"
NAS_UPLOAD_FOLDER = '*************'  # Update as needed
NAS_HOST = '*************'
NAS_PORT = 22
NAS_USERNAME = '****'
NAS_PASSWORD = '*******'
ADMIN_EMAILS = ["ramit.shreenath@gmail.com"]
APPROVAL_EMAILS = ["ramit.shreenath@gmail.com"]
TENDER_URL_TEMPLATE = "http://103.223.15.47:5010/tenders/?filter_tender_id={tender_id}"
APPROVE_TENDER_URL_TEMPLATE = "http://103.223.15.47:5010/approve_tenders/?filter_tender_id={tender_id}"
PENDING_EMD_LIST_URL = "http://103.223.15.47:5010/pending_emd_list"
EMD_BG_DETAILS_URL = "http://103.223.15.47:5011/view_EMD_BG_details/{tender_id}/{emd_id}"
APP_SECRET_KEY = '1234567890'
TENDER_LOG_FILE = 'tender_data.log'

app = Flask(__name__)

logging.basicConfig(filename=TENDER_LOG_FILE,
                    format='%(asctime)s - Line:%(lineno)s - %(levelname)s ::=> %(message)s',
                    filemode='w')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

app.config['UPLOAD_FOLDER'] = ''

paramiko.util.log_to_file('paramiko.log')
logging.getLogger("paramiko").setLevel(logging.DEBUG)

app.secret_key = APP_SECRET_KEY

class User:
    def __init__(self, username, profile, team):
        self.username = username
        self.profile = profile
        self.team = team

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def authenticate(username, password):
    # query = "SELECT * FROM tender.user_details WHERE username = %s AND password = %s"
    query = """select ud.user_id , ud."name" ,ud.username ,ud."password" ,ud.profile ,ud.team ,ud.mobile,ud.email 
    from tender.user_details  ud where (ud.mobile = %s or ud.email = %s or ud.username = %s)
    and ud.status = 'ACTIVE' and ud."password" = %s;"""
    params = [username,username,username,password]
    result = db.get_data_in_list_of_tuple(query, params)
    if result:
        user_data = result[0]
        user = User(user_data[2], user_data[4], user_data[5])
        return user
    return None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = authenticate(username, password)
        if user:
            session['logged_in'] = True
            session['username'] = user.username
            session['profile'] = user.profile
            return redirect(url_for('tenders'))
        else:
            return render_template('login.html', error=True)
    return render_template('login.html', error=False)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/log_time_spent', methods=['POST'])
def log_time_spent():
    # Receive and process the time spent data
    data = request.json  # Assuming the data is sent in JSON format
    time_spent = data.get('timeSpent')
    activity = data.get('page')
    # Log the time spent into your database using your log_activity function
    username = session.get('username')  # Get the username from the session
    # activity = 'Time Spent on Page'  # Adjust the activity description as needed
    start_time = datetime.datetime.now()  # You may use the start time when the page was opened
    end_time = start_time + datetime.timedelta(seconds=float(time_spent))
    
    # Insert the time spent data into the database
    act.log_activity(username, activity, start_time, end_time, time_spent)

    return jsonify({'message': 'Time spent logged successfully'})

@app.route('/tenders/', methods=['GET'])
@login_required
def tenders():

    # current_user = USERS.get(session.get('username'))  # Get the current user object

    username = session.get('username')
    logger.info('Current user is %s', str(username))

    # start_time = session.get('activity_start_time', None)
    # if start_time is None:
    #     start_time = datetime.datetime.now()
    #     session['activity_start_time'] = start_time

    filter_tender_id = request.args.get('filter_tender_id')
    filter_customer = request.args.get('filter_customer')
    filter_name_of_work = request.args.get('filter_name_of_work')
    filter_start_date = request.args.get('filter_start_date')
    filter_end_date = request.args.get('filter_end_date')
    filter_days_old = request.args.get('filter_days_old')
    filter_to_whom = request.args.get('filter_to_whom')


    if filter_end_date:
        end_date = datetime.datetime.strptime(filter_end_date, "%Y-%m-%d")
        modified_end_date = end_date + datetime.timedelta(days=1)
        modified_end_date_str = modified_end_date.strftime("%Y-%m-%d")


    query = """SELECT tender_id, customer, name_of_work, submission_date, folder_location, verification_1,
    inserted_time, to_whom FROM tender.tender_management WHERE (verification_1 in ('none','', 'pre_approved')
    or verification_1 is NULL) and tender_id not in (select tender_id FROM tender.tender_management where 
    (done = 'Not Submitted' and rej_rsn = 'Expired')) and tender_id is not NULL"""

    filters = []
    parameters = []

    if filter_tender_id:
        filters.append("tender_id ILIKE %s")
        parameters.append(f"%{filter_tender_id.replace('/','_')}%")

    if filter_customer:
        filters.append("customer ILIKE %s")
        parameters.append(f"%{filter_customer}%")

    if filter_name_of_work:
        filters.append("name_of_work ILIKE %s")
        parameters.append(f"%{filter_name_of_work}%")

    if filter_start_date and filter_end_date:
        logger.info('Start Date and End Date both are present')
        logger.info(f'Start Date is {filter_start_date} and End Date is {filter_end_date}')
        filters.append("submission_date >= %s")
        parameters.append(f"{filter_start_date}")
        filters.append("submission_date <= %s")
        parameters.append(f"{modified_end_date_str}")
    else:
        if filter_start_date:
            logger.info(f'Start Date is {filter_start_date}')
            filters.append("submission_date >= %s")
            parameters.append(f"{filter_start_date}")
        if filter_end_date:
            logger.info(f'End Date is {filter_end_date}')
            filters.append("submission_date <= %s")
            parameters.append(f"{modified_end_date_str}")

    if filter_days_old:
        filters.append(f"submission_date :: date < current_date + {filter_days_old} and submission_date :: date > current_date")
        # parameters.append(f"{int(filter_days_old)}")

    if filter_to_whom and filter_to_whom != 'none':
        filters.append(f"to_whom = '{filter_to_whom}' ")


    logger.info(parameters)
    logger.info(filters)

    if filters:
        query += " AND " + " AND ".join(filters)

    query += ' order by submission_date asc '
    logger.info(query)
    tenders = db.get_data_in_list_of_tuple(query, parameters)
    get_assign_names_query = """ select ud.username from tender.user_details  ud where ud.status = 'ACTIVE'; """
    get_assign_names_data = db.get_data_in_list_of_tuple(get_assign_names_query)
    assign_names = [i[0] for i in get_assign_names_data] if get_assign_names_data else []
    return render_template('tenders.html', tenders=tenders, user_id=username, assign_names=assign_names)


@app.route('/update_verification/<folder_path>', methods=['POST'])
@login_required
def update_verification(folder_path):
    if request.method == 'POST':
        # current_user = USERS.get(session.get('username'))  # Get the current user object
        # logger.info('Current user is %s', str(current_user.username))
        username = session.get('username')
        logger.info('Current user is %s', str(username))
        user_id = str(username)
        verification_status = request.form['verification_status']
        
        suc = db.execute("UPDATE tender.tender_management SET verification_1 = %s, user_id = %s, done='Open' WHERE folder_location = %s; ",
                         (verification_status, user_id, folder_path))

        if suc:
            query = "SELECT tender_id, emd, customer, name_of_work, submission_date, location, link  FROM tender.tender_management WHERE folder_location = %(folder_path)s"
            t_id = db.get_data_in_list_of_tuple(query, {'folder_path': folder_path})

            if verification_status == 'approved':
                recipient_emails = ["ramit.shreenath@gmail.com"]
                email_subject = "New Entry Approved"
                email_message = f"""
                Hello Team,

                A new tender has been Approve with tender ID: {t_id[0][0]}
                Approver: {user_id}
                URL: http://103.223.15.47:5010/approve_tenders/?filter_tender_id={t_id[0][0]}
                \n
                Customer: {t_id[0][2]}
                Name Of Work: {t_id[0][3]}
                Submission Date: {t_id[0][4]}
                Location: {t_id[0][5]}
                EMD Amount: {t_id[0][1]}
                Link: {t_id[0][6]}
                \n\n
                Thanks,
                Tender APP BOT
                """
                mail.send_mail(to_add=recipient_emails, to_cc=[], sub=email_subject, body=email_message)

        return redirect(url_for('tenders'))


@app.route('/index_view/<folder_path>/', methods=['GET', 'POST'])
@login_required
def index(folder_path):
    files = os.listdir(folder_path)
    return render_template('index.html', files=files, folder_path=folder_path)


@app.route('/open_file/<filename>/<folder_path>', methods=['GET'])
@login_required
def open_file(filename, folder_path):
    file_path = os.path.join(filename).replace('@@', '/')
    # print('---------------------------------')
    return send_file(file_path, as_attachment=False)


@app.route('/tender_details/<tender_id>', methods=['GET'])
@login_required
def tender_details(tender_id):
    query = f"SELECT folder_location FROM tender.tender_management WHERE tender_id = '{tender_id}';"
    file_location = db.get_data_in_list_of_tuple(query)[0][0]
    folder_path = file_location.replace(NAS_UPLOAD_FOLDER, "")
    folder_path = LOCAL_BASE_FOLDER
    return redirect(url_for('view_files', folder_path=folder_path))


@app.route('/insert', methods=['POST', 'GET'])
@login_required
def insert():
    t_query = """select tender_id from tender.tender_management; """
    r_t_data = db.get_data_in_list_of_tuple(t_query)
    t_data = [i[0] for i in r_t_data]
    if request.method == 'POST':
        try:
            # current_user = USERS.get(session.get('username'))  # Get the current user object
            # logger.info('Current user is %s', str(current_user.username))
            username = session.get('username')
            logger.info('Current user is %s', str(username))
            user_id = str(username)
            tender_id = request.form.get('tender_id').replace("/","_").strip()
            customer = request.form.get('customer','').strip()
            location = request.form.get('location','').strip()
            name_of_work = request.form.get('name_of_work','').strip()
            submission_date = request.form.get('submission_date').replace("T", " ")
            publish_date = request.form.get('publish_date').replace("T", " ")
            emd = request.form.get('emd').replace(",","")
            pbm = request.form.get('pbg').replace("T"," ")
            estimated_value = request.form.get('estimated_value').replace(",","")
            link = request.form.get('link')
            local_tender_id = tender_id + '_' + location.replace(" ", "")

            query = f"SELECT COUNT(*) FROM tender.tender_management WHERE tender_id = '{tender_id}' AND location = '{location}';"
            count = db.get_data_in_list_of_tuple(query)[0][0]
            if count > 0:
                return "Data already exists in the database!"

            local_tender_folder = os.path.join(LOCAL_BASE_FOLDER, tender_id)
            os.makedirs(local_tender_folder, exist_ok=True)

            nas_file_paths = []
            files = request.files.getlist('document')
            for file in files:
                if file:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(local_tender_folder, filename)
                    file.save(file_path)
                    nas_file_paths.append(file_path)


            folder_location = local_tender_folder
            nas_file_paths_string = ','.join(nas_file_paths)
            inserted_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            query = """INSERT INTO tender.tender_management (tender_id, customer, location, name_of_work,
                                submission_date, emd, pbm, e_value, link, file_location, folder_location,
                                local_tender_id, inserted_time, user_id, inserted_user_id, publish_date) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
            values = (
                tender_id, customer, location, name_of_work, submission_date, emd, pbm, estimated_value, link,
                nas_file_paths_string, folder_location, local_tender_id, inserted_time, user_id, username, publish_date)

            suc = db.execute(query, values)

            emd_dict = {
                "tender_id": tender_id,
                "emd_required": "NO",
                "emd_form": None,
                "emd_amount": emd,
                "in_favour_of": None,
                "mail_to_fin": None,
                "emd_status": 'For Tender Team',
                "remarks": "EMD Details Not Inserted",
                "time_stamp": datetime.datetime.now().strftime("%d-%b-%Y %H:%M:%S")
            }

            db.insert_dict_into_table("tender.tender_emd", emd_dict)

            folder_dict = {
                "tender_id": tender_id,
                "current_time_col": inserted_time,
                "user_id": user_id
            }
            db.insert_dict_into_table("tender.tender_folder", folder_dict)
            try:
                ass_name = 'set_to_none'
                tat_query = f""" insert into tender.tender_tat (t_id, stage, status, assign_time, assign_to, ext_col_1) 
                values('{tender_id}', 'pre_approved', 'Open', now(), '{ass_name}', '{username}'); """
                db.execute(tat_query)
            except Exception as er:
                logger.info(str(er))
                pass

            if suc:
                recipient_emails = ["ramit.shreenath@gmail.com"]
                email_subject = "New Entry Inserted"
                email_message = f"""
                Hello Team,

                A new tender has been inserted with tender ID: {tender_id}
                URL: http://103.223.15.47:5010/tenders/?filter_tender_id={tender_id}


                Thanks,
                Tender APP BOT
                """
                mail.send_mail(to_add=recipient_emails,to_cc=[],sub=email_subject, body=email_message)
                # send_email(email_subject, email_message, recipient_emails)
                return render_template('insert.html', success=True, t_data=t_data)
            else:
                return render_template('insert.html', error="Data insertion not successful", t_data=t_data)
        except Exception as e:
            # return str(e)
            return render_template('insert.html', error=str(e), t_data=t_data)
    else:
        tender_id = request.args.get('tender_id')
        customer = request.args.get('customer')
        location = request.args.get('location')
        return render_template('insert.html', tender_id=tender_id, customer=customer, location=location, t_data=t_data)


@app.route('/approve_tenders/', methods=['GET'])
@login_required
def approve_tenders():
    username = session.get('username')
    logger.info('Current user is %s', str(username))
    filter_tender_id = request.args.get('filter_tender_id')
    filter_customer = request.args.get('filter_customer')
    filter_name_of_work = request.args.get('filter_name_of_work')
    filter_status = request.args.get('filter_done')
    filter_start_date = request.args.get('filter_start_date')
    filter_end_date = request.args.get('filter_end_date')
    filter_pbm_start_date = request.args.get('filter_pbm_start_date')
    filter_pbm_end_date = request.args.get('filter_pbm_end_date')
    filter_rem_start_date = request.args.get('filter_rem_start_date')
    filter_rem_end_date = request.args.get('filter_rem_end_date')
    filter_days_old = request.args.get('filter_days_old')
    filter_to_whom = request.args.get('filter_to_whom')
    filter_rem_for = request.args.get('filter_rem_for')
    filter_oem = request.args.get('filter_oem')
    filter_ins_by = request.args.get('filter_ins_by')
    filter_assign_start_date = request.args.get('filter_assign_start_date')
    filter_assign_end_date = request.args.get('filter_assign_end_date')


    if filter_end_date:
        end_date = datetime.datetime.strptime(filter_end_date, "%Y-%m-%d")
        modified_end_date = end_date + datetime.timedelta(days=1)
        modified_end_date_str = modified_end_date.strftime("%Y-%m-%d")
    if filter_pbm_end_date:
        pbm_end_date = datetime.datetime.strptime(filter_pbm_end_date, "%Y-%m-%d")
        modified_pbm_end_date = pbm_end_date + datetime.timedelta(days=1)
        modified_pbm_end_date_str = modified_pbm_end_date.strftime("%Y-%m-%d")
    if filter_rem_end_date:
        rem_end_date = datetime.datetime.strptime(filter_rem_end_date, "%Y-%m-%d")
        modified_rem_end_date = rem_end_date + datetime.timedelta(days=1)
        modified_rem_end_date_str = modified_rem_end_date.strftime("%Y-%m-%d")


    # Build the base SQL query
    query = """SELECT tender_id, customer, name_of_work, submission_date, folder_location, 
    verification_1, done, remarks, inserted_time, to_whom, pbm, oem, t_category, assign_time
    FROM tender.tender_management WHERE verification_1 = 'approved'  and (done is null or 
    done not in ('Close-LOSE', 'Close-WIN', 'Close-Cancel', 'Not Submitted', 'Submitted', 'Submitted-L1')) """

    # Build the WHERE clause based on the provided filter criteria
    filters = []
    parameters = []
    rem_filters = []
    rem_parameters = []

    if filter_tender_id:
        filters.append("tender_id ILIKE %s")
        parameters.append(f"%{filter_tender_id.replace('/','_')}%")

    if filter_customer:
        filters.append("customer ILIKE %s")
        parameters.append(f"%{filter_customer}%")

    if filter_name_of_work:
        filters.append("name_of_work ILIKE %s")
        parameters.append(f"%{filter_name_of_work}%")

    if filter_status:
        filters.append("done ILIKE %s")
        parameters.append(f"%{filter_status}%")

    if filter_oem and filter_oem != 'none':
        filters.append(" tender_id in (select tender_id from tender.oem_management where oem ilike %s) ")
        parameters.append(f"%{filter_oem}%")

    if filter_start_date and filter_end_date:
        # logger.info('Start Date and End Date both are present')
        # logger.info(f'Start Date is {filter_start_date} and End Date is {filter_end_date}')
        filters.append("submission_date >= %s")
        parameters.append(f"{filter_start_date}")
        filters.append("submission_date <= %s")
        parameters.append(f"{modified_end_date_str}")
    else:
        if filter_start_date:
            logger.info(f'Start Date is {filter_start_date}')
            filters.append("submission_date >= %s")
            parameters.append(f"{filter_start_date}")
        if filter_end_date:
            logger.info(f'End Date is {filter_end_date}')
            filters.append("submission_date <= %s")
            parameters.append(f"{modified_end_date_str}")

    if filter_pbm_start_date and filter_pbm_end_date:
        logger.info('Start Date and End Date for pbm both are present')
        logger.info(f'Start Date is {filter_pbm_start_date} and End Date is {filter_pbm_end_date}')
        filters.append("pbm >= %s")
        parameters.append(f"{filter_pbm_start_date}")
        filters.append("pbm <= %s")
        parameters.append(f"{modified_pbm_end_date_str}")
    else:
        if filter_pbm_start_date:
            logger.info(f'Start Date is {filter_pbm_start_date}')
            filters.append("pbm >= %s")
            parameters.append(f"{filter_start_date}")
        if filter_pbm_end_date:
            logger.info(f'End Date is {filter_pbm_end_date}')
            filters.append("pbm <= %s")
            parameters.append(f"{modified_pbm_end_date_str}")

    if filter_rem_start_date or filter_rem_end_date or (filter_rem_for and filter_rem_for != 'none'):
        rem_query = "select tender_id from tender.rem_tenders where ext_col_1 is null "
        if filter_rem_for and filter_rem_for != 'none':
            rem_query += f"and rem_for in ('{filter_rem_for}') "
        if filter_rem_start_date and filter_rem_end_date:
            logger.info('Start Date and End Date for rem both are present for reminder')
            logger.info(f'Start Date is {filter_rem_start_date} and End Date is {filter_rem_end_date}')
            # rem_filters.append(f"for_date >= '{filter_rem_start_date}'")
            # rem_parameters.append(f"{filter_rem_start_date}")
            # rem_filters.append(f"for_date <= '{modified_rem_end_date_str}'")
            # rem_parameters.append(f"{modified_rem_end_date_str}")
            rem_query += f"and for_date >= '{filter_rem_start_date}' and for_date <= '{modified_rem_end_date_str}'"

        else:
            if filter_rem_start_date:
                logger.info(f'Start Date is {filter_rem_start_date}')
                # rem_filters.append(f"for_date >= '{filter_rem_start_date}'")
                # rem_parameters.append(f"{filter_start_date}")
                rem_query += f"and for_date >= '{filter_rem_start_date}' "
            if filter_rem_end_date:
                logger.info(f'End Date is {filter_rem_end_date}')
                # rem_filters.append(f"for_date <= '{modified_rem_end_date_str}'")
                # rem_parameters.append(f"{modified_rem_end_date_str}")
                rem_query += f"and for_date <= '{modified_rem_end_date_str}'"

        # Complete the SQL query if any filters are provided
        # if rem_filters:
        #     rem_query += " AND " + " AND ".join(rem_filters)
        filters.append(f"tender_id in ({rem_query})")

    if filter_days_old:
        filters.append(f"submission_date :: date < current_date + {filter_days_old} and submission_date :: date > current_date")

    if filter_to_whom and filter_to_whom != 'none':
        filters.append(f"to_whom = '{filter_to_whom}' ")

    if filter_ins_by:
        if filter_ins_by == 'bot':
            filters.append(f" inserted_user_id ilike '%bot%' ")
        elif filter_ins_by == 'not_bot':
            filters.append(f" inserted_user_id not ilike '%bot%' ")

    if filter_assign_start_date or filter_assign_end_date:
        if filter_assign_start_date:
            filters.append('assign_time :: date >= %s')
            parameters.append(f'{filter_assign_start_date}')
            logger.info(f'Start Assign Date {filter_assign_start_date}')
        if filter_assign_end_date:
            filters.append('assign_time :: date <= %s')
            parameters.append(f'{filter_assign_end_date}')
            logger.info(f'End Assign Date {filter_assign_end_date}')

    if filters:
        query += " AND " + " AND ".join(filters)
    query += ' order by submission_date asc ;'
    logger.info(query)
    tenders = db.get_data_in_list_of_tuple(query, parameters)
    try:
        oem_query = """select oem_name from tender.list_of_oem;"""
        get_oems = db.get_data_in_list_of_tuple(oem_query)
        get_oem = []
        for oem in get_oems:
            get_oem.append(oem[0])
    except:
        get_oem = []
    get_assign_names_query = """ select ud.username from tender.user_details  ud where ud.status = 'ACTIVE'; """
    get_assign_names_data = db.get_data_in_list_of_tuple(get_assign_names_query)
    assign_names = [i[0] for i in get_assign_names_data] if get_assign_names_data else []
    return render_template('approve_tenders.html', tenders=tenders, user_id=username, get_oem=get_oem, assign_names=assign_names)


@app.route('/search_tenders', methods=['GET','POST'])
@login_required
def search_tenders():
    username = session.get('username')
    msg = ''
    if request.method == 'POST':
        tender_id = request.form.get('tender_id').replace('/','_')
        query = f""" select tender_id FROM tender.tender_management where tender_id ilike '%{tender_id}%'; """
        data = db.get_data_in_list_of_tuple(query)
        if data:
            if len(data) == 1:
                return redirect(url_for('view_tender_details', tender_id=tender_id, user_id=username))
            else:
                ids = [d[0] for d in data]
                msg = f'''Multiple Tenders Found!! Please enter any one tender id from the list, 
                {ids} '''
        else:
            msg = 'No tender Found'
    return render_template('search_tender.html', msg=msg)
    pass


@app.route('/approve_tenders/view_tender_details/<tender_id>', methods=['GET'])
@login_required
def view_tender_details(tender_id):
    username = session.get('username')
    logger.info('Current user is %s', str(username))
    query = f"SELECT * FROM tender.tender_management WHERE tender_id = '{tender_id}';"
    tender_details = db.get_data_in_list_of_tuple(query)
    emd_query = f"select emd_required , emd_form , remarks as emd_remarks, in_favour_of, emd_exp_dt from tender.tender_emd te where tender_id ilike '%{tender_id}%' limit 1;"
    emd_details = db.get_data_in_list_of_tuple(emd_query)
    if len(tender_details) == 0:
        return "Tender not found."
    else:
        tender = tender_details[0]
        emd = emd_details[0]
        folder_path = os.path.join(LOCAL_BASE_FOLDER, tender_id)
        if 'rejected' in str(tender_details[0][12]).lower():
            folder_path = os.path.join(LOCAL_BASE_FOLDER,'Rejected Tenders', tender_id)
        return render_template('view_tender_details.html', tender=tender, folder=folder_path, emd=emd, user_id=str(username))


@app.route('/approve_tenders/view_tender_details/update_tender_status_remarks/<tender_id>', methods=['GET', 'POST'])
@login_required
def update_tender_status_remarks(tender_id):
    username = session.get('username')
    logger.info('Current user is %s', str(username))
    if request.method == 'POST':
        user_id = str(username)
        varification = request.form.get('verification')
        status = request.form.get('status')
        s_amt = request.form.get('s_amt')
        remarks = request.form.get('remarks')
        to_whom = request.form.get('to_whom')
        loc = request.form.get('loc')
        submission_date = request.form.get('submission_date').replace('T',' ')
        acc_submitted_date = request.form.get('acc_submitted_date').replace('T',' ')
        reminder_for = request.form.get('reminder_for')
        reminder_date = request.form.get('reminder_date').replace('T',' ')
        lose_reason = request.form.get('lose_reason')
        lose_remarks = request.form.get('lose_remarks').replace("'", "''")
        l1_amount = request.form.get('l1_amt')
        our_amount = request.form.get('our_amt')
# Rej Rsn Test =================================================
        rej_rsn = request.form.getlist('rejc_rsn[]')
        if_otr_rej = request.form.get('if_other')
        rej_rsn_1 = []
        for i in rej_rsn:
            if i == 'Other':
                i += f"({str(if_otr_rej).replace('(', ' << ').replace(')', ' >> ').strip()})"
            rej_rsn_1.append(i)

        r_rsn = '--'.join(rej_rsn_1) if rej_rsn_1 else ''
# =================================================
        if 'close' in status.lower():
            varification = 'closed'
        if not varification:
            varification = 'approved'

        # Use global LOCAL_BASE_FOLDER
        local_tender_folder = os.path.join(LOCAL_BASE_FOLDER, tender_id)
        os.makedirs(local_tender_folder, exist_ok=True)

        files = request.files.getlist('document')
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(local_tender_folder, filename)
                try:
                    file.save(file_path)
                    logger.info(f"File saved locally at {file_path}")
                except Exception as e:
                    logger.error(f"Failed to save file locally: {str(e)}")

        query = "UPDATE tender.tender_management SET done = %s, remarks = %s, user_id = %s, submitted_value = %s, verification_1 = %s "
        parameters = [status, remarks, user_id, s_amt, varification]

        if r_rsn:
            query += ", rej_rsn = %s"
            parameters.append(r_rsn)

        if submission_date:
            query += ", submission_date = %s"
            parameters.append(submission_date)

        if acc_submitted_date:
            query += ", acc_submitted_date = %s"
            parameters.append(acc_submitted_date)

        if reminder_date:
            query += ", reminder_date = %s"
            parameters.append(reminder_date)

        if to_whom and to_whom != 'None':
            query += ", to_whom = %s, assign_time = now() "
            parameters.append(str(to_whom))
            
        if status == 'Close-LOSE':  # Check if Close-LOSE is selected
            query += ", lose_state = %s, lose_remarks = %s, l1_amount = %s, our_amount = %s"
            parameters.extend([lose_reason, lose_remarks, l1_amount, our_amount])

        query += " WHERE tender_id = %s"
        parameters.append(str(tender_id))

        query_1 = f"""select location, name_of_work from tender.tender_management where tender_id = '{str(tender_id)}' ;"""
        data_1 = db.get_data_in_list_of_tuple(query_1)
        loc = data_1[0][0] if data_1 else ''
        name_of_work = data_1[0][1] if data_1 else ''
        logger.info(query)
        logger.info(parameters)


        if reminder_for and reminder_for != 'none':
            rem_ins_query = f"""INSERT INTO tender.rem_tenders (tender_id,rem_for,for_date, user_id)
                    VALUES ('{str(tender_id)}','{str(reminder_for)}','{str(reminder_date)}', '{str(username)}');"""
            db.execute(rem_ins_query)

        try:
            check_last_query = f""" select verification_1, to_whom, done from tender.tender_management where tender_id = '{str(tender_id)}' limit 1"""
            check_last_data = db.get_data_in_list_of_tuple(check_last_query)

            if check_last_data[0][0] == varification and varification == 'approved':
                logger.info('check_last_data[0][0] == varification and varification == "approved"')
                if not to_whom or str(to_whom).lower() == 'none':
                    logger.info("not to_whom or to_whom == 'None':")
                    time_ins_query = f""" insert into tender.tender_tat (t_id, stage, status, assign_time, assign_to, ext_col_1) 
                    values('{str(tender_id)}', '{varification}', '{status}', now(), 'no_user', '{username}') ; """
                    logger.info(time_ins_query)
                    db.execute(time_ins_query)
                elif check_last_data[0][1] != to_whom:
                    logger.info("check_last_data[0][1] != to_whom")
                    time_ins_query = f""" insert into tender.tender_tat (t_id, stage, status, assign_time, assign_to, ext_col_1) 
                    values('{str(tender_id)}', '{varification}', '{status}', now(), '{to_whom}', '{username}') ; """
                    logger.info(time_ins_query)
                    db.execute(time_ins_query)
            else:
                time_ins_query = f""" insert into tender.tender_tat (t_id, stage, status, assign_time, assign_to, ext_col_1) 
                values('{str(tender_id)}', '{varification}', '{status}', now(), 'no_user', '{username}') ; """
                logger.info(time_ins_query)
                db.execute(time_ins_query)
        except:
            pass

        suc = db.execute(query, parameters)


        if suc:
                recipient_emails = ["ramit.shreenath@gmail.com"]
                to_whom_mail_query = f""" select ud.email from tender.user_details  ud
                where ud.status = 'ACTIVE' and ud.username = '{to_whom}';"""
                to_whom_mail_data = db.get_data_in_list_of_tuple(to_whom_mail_query)
                recipient_emails.append(to_whom_mail_data[0][0]) if to_whom_mail_data else recipient_emails.append("ramit.shreenath@gmail.com")
                # email_subject = f"Tender ID: {str(tender_id)}, Location: {loc}"
                # if to_whom:
                email_subject = f"Tender ID: {str(tender_id)}, Assign: {to_whom}, Location: {loc}"
                # if status == '':
                email_message = f"""Hello Team,

                This is a notification mail for update status and remarks of tender ID: {tender_id}
                Name of Work: {name_of_work}
                Status: {status}
                Remarks: {remarks}
                Submission Date: {str(submission_date)}
                Updated By: {user_id}

                URL: http://103.223.15.47:5010/approve_tenders/?filter_tender_id={tender_id}

                Thanks,
                Tender APP BOT
                """
                if status in ("Submitted", "Under Consideration"):
                    pass
                mail.send_mail(to_add=recipient_emails, to_cc=[], sub=email_subject, body=email_message)
                # send_email(email_subject, email_message, recipient_emails)

        return redirect(url_for('view_tender_details', tender_id=tender_id, user_id=username))

    else:
        query = f"""select done, remarks, submitted_value, verification_1, location, lose_remarks, lose_state,
        l1_amount, our_amount, rej_rsn from tender.tender_management where tender_id = '{str(tender_id)}' ;"""
        data = db.get_data_in_list_of_tuple(query)

        query_1 = f"""select done, remarks, change_timestamp, user_id, to_whom, submitted_value from tender.tender_management_history tmh where 
        (ext_col_1 <> 'yes' or ext_col_1 is null) and tender_id  = '{str(tender_id)}' order by change_timestamp desc ;"""
        data_1 = db.get_row_as_dframe(query_1)
        
        # query_user_details = f"""select ext_col_1 from tender.user_details where ext_col_1 is not null or ext_col_1 not in ('', ' ') ;"""
        query_user_details = f"""select ud.username, ud.profile from tender.user_details  ud where ud.status = 'ACTIVE';"""
        data_res_det = db.get_data_in_list_of_tuple(query_user_details)
        users = [i[0] for i in data_res_det if i[0]]
        current_status = data[0][0]
        current_remarks = data[0][1]
        s_amt = data[0][2]
        loc = data[0][4]
        varification = data[0][3]
        l_rem = data[0][5]
        l1_amt = data[0][7]
        l_state = data[0][6]
        o_amt = data[0][8]
        rej_rsn = data[0][9]
        try:
            rej_opt = rej_rsn.split('--')
            rej_opt_output = []
            if_otr = None
            for i in rej_opt:
                if 'other(' in i:
                    extracted_text = i.split('other(')[1].split(')')[0] if ')' in i else ''
                    rej_opt_output.append('other')
                    if_otr = extracted_text
                else:
                    rej_opt_output.append(i)
        except:
            pass

        if not varification:
            varification = 'none'

        rejection_reason = f"""select rej_rsn from tender.rejection_reason;"""
        rej_data_check = db.get_data_in_list_of_tuple(rejection_reason)
        rej_data = [i[0] for i in rej_data_check]


        return render_template('update_tender_status_remarks.html', tender_id=tender_id, current_status=current_status,
                               current_remarks=current_remarks, s_amt=s_amt, loc=loc, verification=varification, l_rem=l_rem,
                               l1_amt=l1_amt, l_state=l_state, o_amt=o_amt, tender_history=data_1, users=users,rejrsn=rej_data)


@app.route('/approve_tenders/view_tender_details/view_files/<folder_path>/<t_id>', methods=['GET', 'POST'])
@login_required
def view_files(folder_path, t_id):
    folder_path = folder_path
    username = session.get('username')
    logger.info('Current user is %s', str(username))
    if request.method == 'POST':
        button_clicked = request.form.get("button_clicked")
        if button_clicked == "open_folder":
            try:
                # query = f""" select tender_id from tender.tender_management WHERE folder_location = '{folder_path}'; """
                query = f""" select tender_id from tender.tender_management WHERE tender_id = '{t_id}'; """
                data = db.get_data_in_list_of_tuple(query)
                logger.info(query)
                t_id = data[0][0]
                current_time_col = datetime.datetime.now().strftime('%d-%b-%Y %H:%M:%S')
                query_1 = f"""insert into tender.tender_folder (tender_id, current_time_col, open_folder, user_id)
                values ('{t_id}', '{current_time_col}', 'yes', '{username}') on conflict (tender_id)
                do update set current_time_col = '{current_time_col}', open_folder = 'yes', user_id = '{username}' ;"""
                db.execute(query_1)
                logger.info(query_1)
            except:
                pass

    # tender_id = folder_path.split('\\')[-1]
    tender_id = t_id
    files = []
    if folder_path not in ("", " ", 'none', 'None'):
        # print('Checking for file path')
        for root, _, filenames in os.walk(folder_path):
            # print('root: ', root)
            # print('filenames: ', filenames)
            for filename in filenames:
                file_path = os.path.join(root, filename)
                # print('File Name: ', filename)
                # print('File Path: ', file_path)
                relative_path = os.path.relpath(file_path, folder_path)
                # files.append(relative_path)
                files.append(file_path)
                # print('Files: ', files)
    return render_template('view_files.html', files=files, folder_path=folder_path, tender_id=tender_id, user_id=username)


@app.route('/approve_tenders/view_tender_details/update_emd_details/<tender_id>', methods=['GET', 'POST'])
@login_required
def update_emd_details(tender_id):
    username = session.get('username')
    logger.info('Current user is %s', str(username))
    user_id = str(username)
    if request.method == 'POST':
        emd_required = request.form.get('emd_required')
        form = request.form.getlist('emd_form[]')
        emd_form = ', '.join(form)
        logger.info(f'EMD form is {emd_form}')
        emd_amount = request.form.get('emd_amount').replace(",","")
        in_favour_of = request.form.get('in_favour_of')
        remarks = request.form.get('remarks').replace("\"", "").replace("'","''")
        emd_exp_dt = request.form.get('emd_exp_dt').replace("T"," ")
        time_stamp = datetime.datetime.now().strftime('%d-%b-%Y %H:%M:%S')
        try:
            bg_details = {
                "bank": request.form.get('bank'),
                "bg_ref_no": request.form.get('bg_ref_no'),
                "bg_issue_date": request.form.get('bg_issue_date'),
                "bg_outstanding": request.form.get('bg_outstanding'),
                "beneficiary_name": request.form.get('beneficiary_name'),
                "status": request.form.get('status'),
                "fdr_no": request.form.get('fdr_no'),
                "date_of_closure": request.form.get('date_of_closure'),
                "difference": request.form.get('difference')
            }
            logger.info(f"BG Details JSON: {bg_details}")
        except Exception as e:
            logger.error(f"Error while preparing BG details: {str(e)}")
            bg_details = None

        # Use global LOCAL_BASE_FOLDER
        emd_folder = os.path.join(LOCAL_BASE_FOLDER, tender_id, "EMD Documents")
        os.makedirs(emd_folder, exist_ok=True)

        files = request.files.getlist('document')
        for file in files:
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(emd_folder, filename)
                try:
                    file.save(file_path)
                    logger.info(f"EMD file saved locally at: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to save EMD file locally: {str(e)}")

        folder_location = emd_folder

        logger.info(f'EMD form is {emd_form}')
        query = f"""UPDATE tender.tender_emd SET emd_required = '{emd_required}', emd_form = '{emd_form}', emd_amount = '{emd_amount}',
        in_favour_of = '{in_favour_of}', remarks = '{remarks}', emd_exp_dt= '{emd_exp_dt}', time_stamp = '{time_stamp}', ext_col_1 = '', 
        epbg_file_loc = '{folder_location}', emd_status = 'For Approval - Admin' WHERE tender_id = '{str(tender_id)}'"""
        db.execute(query)
        logger.info(query)

        query_1 = f"""UPDATE tender.tender_management SET done = 'WIP-FOR EMD', user_id = '{str(user_id)}' WHERE tender_id = '{str(tender_id)}'"""
        db.execute(query_1)
        logger.info(query_1)

        attachments = []
        if folder_location:
            files = os.listdir(folder_location)
            for file in files:
                file_path = os.path.join(folder_location, file)
                attachments.append(file_path)
        if emd_required in ('Yes', 'exempted'):
            to_add = ["ramit.shreenath@gmail.com"]
            to_cc = None
            sub = f"EMD details for {tender_id}"
            body = f"""
            Hello Sir,

            EMD Required: {emd_required}
            EMD Type: {emd_form}
            EMD Amount: {emd_amount}
            EMD Updated by: {user_id}
            Required documents are shared as attachments.\n

            link: http://103.223.15.47:5010/pending_emd_list
            \n

            PFA\n

            Thanks,
            EMD BOT

            Team Shreenath
            """
            if emd_required == 'exempted':
                body = body.replace("link: http://103.223.15.47:5010/pending_emd_list", '')
            if tender_id != '1':
                mail.send_mail(to_add, to_cc, sub, body, attach=attachments)
                try:
                    wp.send_msg_in_group(msg=body)
                except:
                    pass

        return redirect(url_for('view_tender_details', tender_id=tender_id))

    else:
        query = f"""select * from tender.tender_emd where tender_id = '{str(tender_id)}' ;"""
        data = db.get_data_in_list_of_tuple(query)
    
        emd_required = data[0][2]
        emd_form = data[0][3]
        emd_amount = data[0][4]
        in_favour_of = data[0][5]
        remarks = data[0][7]

        return render_template('emd_pbc.html', tender_id=tender_id, emd_required=emd_required, emd_form=emd_form, emd_amount=emd_amount,
                            in_favour_of=in_favour_of, remarks=remarks)


@app.route('/pending_emd_list/', methods=['GET', 'POST'])
@login_required
def emd_list():
    username = session.get('username')
    logger.info('Current user is %s', str(username))
    user_id = str(username)
    filter_tender_id = request.args.get('filter_tender_id')
    emd_form = request.args.get('emd_form')
    emd_status = request.args.get('emd_status')

    query = """select emd.tender_id, emd.emd_required , emd.emd_form , emd.emd_amount , emd.in_favour_of , emd.remarks, 
    emd.emd_exp_dt, emd.id, emd.emd_status from tender.tender_emd as emd, tender.tender_management as tm
    where (emd.ext_col_1 is null or emd.ext_col_1 = '') and emd.emd_required = 'Yes' and tm.verification_1 <> 'rejected' and tm.done <> 'EMD Cancelled'
    and emd.tender_id = tm.tender_id """

    filters = []
    parameters = []

    if filter_tender_id:
        filters.append("emd.tender_id ILIKE %s")
        parameters.append(f"%{filter_tender_id}%")

    if emd_form:
        filters.append("emd.customer ILIKE %s")
        parameters.append(f"%{emd_form}%")

    if emd_status:
        filters.append("emd.emd_status ILIKE %s")
        parameters.append(f"%{emd_status}%")

    logger.info(parameters)
    logger.info(filters)

    # Complete the SQL query if any filters are provided
    if filters:
        query += " AND " + " AND ".join(filters)

    query += ' order by time_stamp asc '

    # Retrieve the relevant tenders from the database
    tenders = db.get_data_in_list_of_tuple(query, parameters)

    return render_template('emd_list.html', tenders=tenders)


@app.route('/view_EMD_BG_details/<tender_id>/<emd_id>', methods=['GET', 'POST'])
def view_EMD_BG_details(tender_id, emd_id):
    try:
        view_query = f""" SELECT id, tender_id, emd_required, emd_form, emd_amount, in_favour_of, remarks, emd_exp_dt, bg_details,
                    emd_status, int_remarks, epbg_file_loc FROM tender.tender_emd 
                    WHERE tender_id = '{tender_id}' AND id = {int(emd_id)} ;"""
        emd_details = db.get_data_in_list_of_tuple(view_query)
        print(emd_details[0][11])
        tender_status_query = f"""select done from tender.tender_management where tender_id = '{tender_id}' ;""" 
        try:
            tender_status = db.get_data_in_list_of_tuple(tender_status_query)[0][0]
        except:
            tender_status = None
        if not emd_details:
            flash("No details found for the given Tender ID and EMD ID.", "warning")
            return redirect(url_for('emd_list'))
        if request.method == 'POST':
            action = request.form.get('action')
            emd_required = 'Yes'
            emd_form = ','.join(request.form.getlist('emd_form[]'))
            emd_amount = request.form.get('emd_amount', '').strip()
            in_favour_of = request.form.get('in_favour_of', '').strip()
            remarks = request.form.get('remarks', '').strip()
            emd_exp_dt = request.form.get('emd_exp_dt', '').strip()
            new_tender_status = request.form.get('status', '').strip()
            files = request.files.getlist('document')
            try:
                file_loc = emd_details[0][11]
            except:
                file_loc = None
            if files:
                # Use global LOCAL_BASE_FOLDER
                emd_folder = os.path.join(LOCAL_BASE_FOLDER, tender_id, "EMD Documents")
                os.makedirs(emd_folder, exist_ok=True)

                for file in files:
                    if file:
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(emd_folder, filename)
                        try:
                            file.save(file_path)
                            logger.info(f"EMD file saved locally at: {file_path}")
                        except Exception as e:
                            logger.error(f"Failed to save EMD file locally: {str(e)}")

                file_loc = emd_folder  # Update to use this as storage path

            bg_details = {
                key.replace('bg_details[', '').rstrip(']'): value
                for key, value in request.form.items() if key.startswith('bg_details[')
            }
            if action == 'approve':
                current_status = emd_details[0][9]
                if current_status == 'For Approval - Admin' and session['profile'] != 'SUPER ADMIN':
                    new_emd_status = 'For Approval - Super Admin'
                elif current_status == 'For Approval - Super Admin' or session['profile'] == 'SUPER ADMIN':
                    new_emd_status = 'For Accounts'
                else:
                    flash("Approval not allowed at the current status.", "danger")
                int_remarks = f"Approved by {session['username']} at {datetime.datetime.now()}"
                query = f"""UPDATE tender.tender_emd 
                        SET emd_required = '{emd_required}', emd_form = '{emd_form}', emd_amount = '{emd_amount}', 
                            in_favour_of = '{in_favour_of}', remarks = '{remarks}', emd_exp_dt = '{emd_exp_dt}', 
                            bg_details = '{json.dumps(bg_details)}', emd_status = '{new_emd_status}', 
                            int_remarks = '{int_remarks}', epbg_file_loc = '{file_loc}'
                        WHERE tender_id = '{tender_id}' AND id = {int(emd_id)} ;"""
                db.execute(query)
                db.execute(f"update tender.tender_management set done='{new_tender_status}' where tender_id = '{tender_id}' ;")
                flash("EMD/BG approved and Details updated successfully. ", "success")
                # return redirect(url_for('view_EMD_BG_details', tender_id=tender_id, emd_id=emd_id))
            elif action == 'reject':
                if session['profile'] == 'ADMIN':
                    new_emd_status = 'For Tender Team'
                elif session['profile'] == 'SUPER ADMIN':
                    new_emd_status = 'For Approval - Admin'
                else:
                    flash("Rejection not allowed at the current status.", "danger")
                int_remarks = f"Rejected by {session['username']} at {datetime.datetime.now()}"
                query = f"""UPDATE tender.tender_emd 
                        SET emd_required = '{emd_required}', emd_form = '{emd_form}', emd_amount = '{emd_amount}', 
                            in_favour_of = '{in_favour_of}', remarks = '{remarks}', emd_exp_dt = '{emd_exp_dt}', 
                            bg_details = '{json.dumps(bg_details)}', emd_status = '{new_emd_status}',
                            int_remarks = '{int_remarks}', epbg_file_loc = '{file_loc}'
                        WHERE tender_id = '{tender_id}' AND id = {int(emd_id)} ;"""
                
                db.execute(query)
                db.execute(f"update tender.tender_management set done='{new_tender_status}' where tender_id = '{tender_id}' ;")
                flash("EMD/BG rejected and Details updated successfully.", "danger")
                # return redirect(url_for('view_EMD_BG_details', tender_id=tender_id, emd_id=emd_id))

            # Mail logic =======================================
            sub = f'Change in EMD status for {tender_id}'
            body = f"""Hello team, \n\nBelow are the EMD chnages,\nTender ID: {tender_id},\nEMD Status: {new_emd_status},
                    \nUpdated By: {int_remarks}, \nURL: http://103.223.15.47:5011/view_EMD_BG_details/{tender_id}/{emd_id}
                    \nCheck this emd details in 'EMD list' section.\n\nThanks,\ntender management System"""
            to_add = ['ramit.shreenath@gmail.com']
            to_cc = []
            if new_emd_status == 'For Approval - Admin':
                to_add.append('')
                to_cc.append('')
            elif new_emd_status == 'For Tender Team':
                to_add.append('')
                to_cc.append('')
            elif new_emd_status == 'For Approval - Super Admin':
                to_add.append('')
                to_cc.append('')
            elif new_emd_status == 'For Accounts':
                to_add.append('')
                to_cc.append('')
            print(to_add)

            mail.send_mail(to_add=to_add, to_cc=to_cc, sub=sub, body=body)
            wp.send_msg_in_group(msg=body)

            return redirect(url_for('view_EMD_BG_details', tender_id=tender_id, emd_id=emd_id))

        else:
            if emd_details:
                emd_form_list = emd_details[0][3].split(',')
                try:
                    bg_details = emd_details[0][8] if emd_details[0][8] else {}
                except:
                    bg_details = {
                        "bank": "",
                        "fdr_no": "",
                        "bg_amount": "",
                        "bg_ref_no": "",
                        "bg_status": "under_approvals",
                        "difference": "",
                        "bg_issue_date": "",
                        "bg_expiry_date": "",
                        "bg_outstanding": "",
                        "date_of_closure": "",
                        "required_expiry_date": "",
                        "beneficiary_name": ""
                        }
            return render_template('view_emd_bg_details.html', details=emd_details, bg_details=bg_details, tender_status=tender_status, emd_form_list=emd_form_list)
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('emd_list'))


@app.route('/pending_emd_list/update_emd_status/<tender_id>', methods=['GET', 'POST'])
@login_required
def update_EMD_details_fin(tender_id):
    if request.method == 'POST':
        # current_user = USERS.get(session.get('username'))  # Get the current user object
        # logger.info('Current user is %s', str(current_user.username))
        username = session.get('username')
        logger.info('Current user is %s', str(username))
        user_id = str(username)
        status = request.form.get('status')
        remarks = request.form.get('remarks').replace("'","''")
        emd_form = ','.join(request.form.getlist('emd_form'))
        loc = request.form.get('loc')

        time_stamp = datetime.datetime.now().strftime('%d-%b-%Y %H:%M:%S')

        files = request.files.getlist('document')
        # Use global LOCAL_BASE_FOLDER
        emd_folder = os.path.join(LOCAL_BASE_FOLDER, tender_id, "EMD Documents")
        os.makedirs(emd_folder, exist_ok=True)

        for file in files:
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(emd_folder, filename)
                try:
                    file.save(file_path)
                    logger.info(f"EMD file saved locally at: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to save EMD file locally: {str(e)}")

        folder_location = emd_folder

        query = f"""UPDATE tender.tender_emd SET ext_col_1 = '{status}', remarks = '{remarks}', 
        emd_form = '{emd_form}', time_stamp = '{time_stamp}', epbg_file_loc = '{folder_location}'
        WHERE tender_id = '{str(tender_id)}'"""
        suc = db.execute(query)
        logger.info(query)

        query_1 = f"""UPDATE tender.tender_management SET done = '{status}', remarks = '{remarks}', user_id = '{user_id}' WHERE tender_id = '{str(tender_id)}'"""
        suc = db.execute(query_1)
        logger.info(query_1)

        query_2 = f"select location from tender.tender_management  where tender_id = '{str(tender_id)}' ;"
        data_2 = db.get_data_in_list_of_tuple(query_2)

        loc = data_2[0][0]

        if suc:
                recipient_emails = ["ramit.shreenath@gmail.com"]
                email_subject = f"tender ID: {str(tender_id)}, Location: {loc}"
                email_message = f"""
                Hello Team,
                \n
                This is a notification mail for EMD Details Updted by Finance Team of tender ID: {tender_id}
                \n
                URL: http://103.223.15.47:5010/pending_emd_list/
                \n
                Thanks,
                Tender APP BOT
                """
                mail.send_mail(to_add=recipient_emails, to_cc=[], sub=email_subject, body=email_message)
                # send_email(email_subject, email_message, recipient_emails)

        return 'Status Updated'

    else:
        query = f"""select ext_col_1, remarks, emd_form from tender.tender_emd where tender_id = '{str(tender_id)}' ;"""
        data = db.get_data_in_list_of_tuple(query)
    
        query_1 = f"""select done, remarks, change_timestamp, user_id from tender.tender_management_history tmh where tender_id  = '{str(tender_id)}' order by change_timestamp desc ;"""
        data_1 = db.get_row_as_dframe(query_1)
        
        query_2 = f"select location from tender.tender_management  where tender_id = '{str(tender_id)}' ;"
        data_2 = db.get_data_in_list_of_tuple(query_2)

        loc = data_2[0][0]

        status = data[0][0]
        remarks = data[0][1]
        emd_form = data[0][2]

        return render_template('update_emd_status_fin.html', tender_id=tender_id, status=status, remarks=remarks, emd_form=emd_form, tender_history=data_1, loc=loc)


@app.route('/submitted_tenders/', methods=['GET'])
@login_required
def submitted_tenders():
    username = session.get('username')
    logger.info('Current user is %s', str(username))

    filter_tender_id = request.args.get('filter_tender_id')
    filter_customer = request.args.get('filter_customer')
    filter_name_of_work = request.args.get('filter_name_of_work')
    filter_status = request.args.get('filter_done')

    query = """SELECT tender_id, customer, name_of_work, submission_date, folder_location, verification_1, done, remarks, inserted_time
    FROM tender.tender_management WHERE verification_1 = 'approved'  and done in ('Submitted','Submitted-L1') """

    # Build the WHERE clause based on the provided filter criteria
    filters = []
    parameters = []

    if filter_tender_id:
        filters.append("tender_id ILIKE %s")
        parameters.append(f"%{filter_tender_id.replace('/','_')}%")

    if filter_customer:
        filters.append("customer ILIKE %s")
        parameters.append(f"%{filter_customer}%")

    if filter_name_of_work:
        filters.append("name_of_work ILIKE %s")
        parameters.append(f"%{filter_name_of_work}%")

    if filter_status:
        filters.append("done ILIKE %s")
        parameters.append(f"%{filter_status}%")

    # Complete the SQL query if any filters are provided
    if filters:
        query += " AND " + " AND ".join(filters)

    query += ' order by submission_date asc ;'

    # Retrieve the relevant tenders from the database
    tenders = db.get_data_in_list_of_tuple(query, parameters)

    return render_template('submitted_tenders.html', tenders=tenders, user_id=username)


@app.route('/closed_tenders/', methods=['GET'])
@login_required
def closed_tenders():
    username = session.get('username')
    logger.info('Current user is %s', str(username))

    filter_tender_id = request.args.get('filter_tender_id')
    filter_customer = request.args.get('filter_customer')
    filter_name_of_work = request.args.get('filter_name_of_work')
    filter_status = request.args.get('filter_done')

    # Build the base SQL query
    query = """SELECT tender_id, customer, name_of_work, submission_date, folder_location, verification_1, done, remarks, 
    inserted_time, lose_state, lose_remarks, l1_amount, our_amount
    FROM tender.tender_management WHERE verification_1 in ('approved','closed')  and done in ('Close-WIN', 'Close-LOSE', 'Close-Cancel') """

    # Build the WHERE clause based on the provided filter criteria
    filters = []
    parameters = []

    if filter_tender_id:
        filters.append("tender_id ILIKE %s")
        parameters.append(f"%{filter_tender_id.replace('/','_')}%")

    if filter_customer:
        filters.append("customer ILIKE %s")
        parameters.append(f"%{filter_customer}%")

    if filter_name_of_work:
        filters.append("name_of_work ILIKE %s")
        parameters.append(f"%{filter_name_of_work}%")

    if filter_status:
        filters.append("done ILIKE %s")
        parameters.append(f"%{filter_status}%")

    # Complete the SQL query if any filters are provided
    if filters:
        query += " AND " + " AND ".join(filters)

    query += ' order by submission_date asc ;'

    # Retrieve the relevant tenders from the database
    tenders = db.get_data_in_list_of_tuple(query, parameters)

    return render_template('closed_tenders.html', tenders=tenders, user_id=username)


@app.route('/rejected_tenders/', methods=['GET'])
@login_required
def rejected_tenders():
    username = session.get('username')
    logger.info('Current user is %s', str(username))

    filter_tender_id = request.args.get('filter_tender_id')
    filter_customer = request.args.get('filter_customer')
    filter_name_of_work = request.args.get('filter_name_of_work')
    filter_start_date = request.args.get('filter_start_date')
    filter_end_date = request.args.get('filter_end_date')

    if filter_end_date:
        end_date = datetime.datetime.strptime(filter_end_date, "%Y-%m-%d")
        modified_end_date = end_date + datetime.timedelta(days=1)
        modified_end_date_str = modified_end_date.strftime("%Y-%m-%d")


    query = """SELECT tender_id, customer, name_of_work, submission_date, folder_location, verification_1 , inserted_time
            FROM tender.tender_management WHERE ((verification_1 = 'rejected') or (verification_1 = 'approved' and done = 'Not Submitted')) """

    filters = []
    parameters = []

    if filter_tender_id:
        filters.append("tender_id ILIKE %s")
        parameters.append(f"%{filter_tender_id.replace('/','_')}%")

    if filter_customer:
        filters.append("customer ILIKE %s")
        parameters.append(f"%{filter_customer}%")

    if filter_name_of_work:
        filters.append("name_of_work ILIKE %s")
        parameters.append(f"%{filter_name_of_work}%")

    if filter_start_date and filter_end_date:
        logger.info('Start Date and End Date both are present')
        logger.info(f'Start Date is {filter_start_date} and End Date is {modified_end_date_str}')
        filters.append("submission_date >= %s")
        parameters.append(f"{filter_start_date}")
        filters.append("submission_date <= %s")
        parameters.append(f"{modified_end_date_str}")
    else:
        if filter_start_date:
            logger.info(f'Start Date is {filter_start_date}')
            filters.append("submission_date >= %s")
            parameters.append(f"{filter_start_date}")
        if filter_end_date:
            logger.info(f'End Date is {filter_end_date}')
            filters.append("submission_date <= %s")
            parameters.append(f"{modified_end_date_str}")

    logger.info(parameters)
    logger.info(filters)

    # Complete the SQL query if any filters are provided
    if filters:
        query += " AND " + " AND ".join(filters)

    query += ''' and TO_DATE(inserted_time, 'DD-MM-YYYY HH24:MI:SS')::date >= current_date - 120 order by submission_date asc '''

    # Retrieve the relevant tenders from the database
    tenders = db.get_data_in_list_of_tuple(query, parameters)

    return render_template('rejected_tenders.html', tenders=tenders, user_id=username)


@app.route('/all_tenders/', methods=['GET'])
@login_required
def all_tenders():

    username = session.get('username')
    logger.info('Current user is %s', str(username))

    filter_tender_id = request.args.get('filter_tender_id')
    filter_customer = request.args.get('filter_customer')
    filter_location = request.args.get('filter_location')
    filter_name_of_work = request.args.get('filter_name_of_work')
    filter_start_date = request.args.get('filter_start_date')
    filter_end_date = request.args.get('filter_end_date')
    filter_days_old = request.args.get('filter_days_old')


    if filter_end_date:
        end_date = datetime.datetime.strptime(filter_end_date, "%Y-%m-%d")
        modified_end_date = end_date + datetime.timedelta(days=1)
        modified_end_date_str = modified_end_date.strftime("%Y-%m-%d")


    query = """SELECT tender_id, customer, name_of_work, submission_date, folder_location, verification_1, done , inserted_time
            FROM tender.tender_management WHERE (verification_1 is null or verification_1 not in ('none', 'FOR UPDATE'))  """

    filters = []
    parameters = []

    if filter_tender_id:
        filters.append("tender_id ILIKE %s")
        parameters.append(f"%{filter_tender_id.replace('/','_')}%")

    if filter_customer:
        filters.append("customer ILIKE %s")
        parameters.append(f"%{filter_customer}%")
    
    if filter_location:
        filters.append("customer ILIKE %s")
        parameters.append(f"%{filter_location}%")

    if filter_name_of_work:
        filters.append("name_of_work ILIKE %s")
        parameters.append(f"%{filter_name_of_work}%")

    if filter_start_date and filter_end_date:
        logger.info('Start Date and End Date both are present')
        logger.info(f'Start Date is {filter_start_date} and End Date is {filter_end_date}')
        filters.append("submission_date >= %s")
        parameters.append(f"{filter_start_date}")
        filters.append("submission_date <= %s")
        parameters.append(f"{modified_end_date_str}")
    else:
        if filter_start_date:
            logger.info(f'Start Date is {filter_start_date}')
            filters.append("submission_date > %s")
            parameters.append(f"{filter_start_date}")
        if filter_end_date:
            logger.info(f'End Date is {filter_end_date}')
            filters.append("submission_date <= %s")
            parameters.append(f"{modified_end_date_str}")

    if filter_days_old:
        filters.append(f"submission_date :: date < current_date + {filter_days_old} and submission_date :: date > current_date")

    logger.info(parameters)
    logger.info(filters)

    if filters:
        query += " AND " + " AND ".join(filters)

    query += ''' and TO_DATE(inserted_time, 'DD-MM-YYYY HH24:MI:SS')::date >= current_date - 180 order by submission_date asc '''
    logger.info(query)
    tenders = db.get_data_in_list_of_tuple(query, parameters)

    return render_template('all_tenders.html', tenders=tenders, user_id=username)


@app.route('/update_status', methods=['POST'])
def update_tender_status_1():
    username = session.get('username')
    logger.info('Current user is %s', str(username))

    selected_tenders_str = request.form.get('selected_tenders')
    status = request.form.get('status')


    if selected_tenders_str:
        selected_tenders = selected_tenders_str.split(',')
        tender_ids = tuple(tender_id.strip() for tender_id in selected_tenders)
        ass_name = 'set_to_none'
        # Update the verification status for selected tenders in the database
        update_query = f"UPDATE tender.tender_management SET verification_1 = '{status}', user_id = '{username}' WHERE tender_id IN {tender_ids}"
        if len(tender_ids) == 1:
            update_query = f"UPDATE tender.tender_management SET verification_1 = '{status}', user_id = '{username}' WHERE tender_id IN ('{tender_ids[0]}')"
        logger.info(update_query)
        db.execute(update_query)
        for i in tender_ids:
            inst_query = f""" insert into tender.tender_tat (t_id, stage, status, assign_time, assign_to, ext_col_1)
            values('{i}', '{status}', 'Open', now(), '{ass_name}', '{username}'); """
            db.execute(inst_query)
    # Redirect back to the previous page after updating the status
    return redirect(request.referrer)


@app.route('/for_update_tenders/', methods=['GET', 'POST'])
@login_required
def for_update():

    username = session.get('username')
    logger.info('Current user is %s', str(username))

    filter_tender_id = request.args.get('filter_tender_id')
    filter_customer = request.args.get('filter_customer')
    filter_name_of_work = request.args.get('filter_name_of_work')
    filter_start_date = request.args.get('filter_start_date')
    filter_end_date = request.args.get('filter_end_date')
    filter_days_old = request.args.get('filter_days_old')
    # filter_to_whom = request.args.get('filter_to_whom')

    if filter_end_date:
        end_date = datetime.datetime.strptime(filter_end_date, "%Y-%m-%d")
        modified_end_date = end_date + datetime.timedelta(days=1)
        modified_end_date_str = modified_end_date.strftime("%Y-%m-%d")


    query = """SELECT tender_id, customer, name_of_work, submission_date, folder_location, verification_1, done ,
            TO_CHAR(to_timestamp(inserted_time, 'DD-MM-YYYY HH24:MI:SS'), 'DD-MM-YYYY HH24:MI:SS') as inserted_time, to_whom
            FROM tender.tender_management WHERE verification_1 = 'FOR UPDATE' """

    filters = []
    parameters = []

    if filter_tender_id:
        filters.append("tender_id ILIKE %s")
        parameters.append(f"%{filter_tender_id.replace('/','_')}%")

    if filter_customer:
        filters.append("customer ILIKE %s")
        parameters.append(f"%{filter_customer}%")
    
    if filter_name_of_work:
        filters.append("name_of_work ILIKE %s")
        parameters.append(f"%{filter_name_of_work}%")

    if filter_start_date and filter_end_date:
        filters.append("submission_date >= %s")
        parameters.append(filter_start_date)
        filters.append("submission_date < %s")
        parameters.append(modified_end_date_str)
    else:
        if filter_start_date:
            filters.append("submission_date > %s")
            parameters.append(filter_start_date)
        if filter_end_date:
            filters.append("submission_date <= %s")
            parameters.append(modified_end_date_str)

    if filter_days_old:
        filters.append(f"submission_date::date < current_date + interval '{filter_days_old}' and submission_date::date > current_date")

    # if filter_to_whom and filter_to_whom != 'none':
    #     filters.append(f"to_whom = '{filter_to_whom}' ")

    # logger.info(parameters)
    # logger.info(filters)

    if filters:
        query += " AND " + " AND ".join(filters)

    query += ' ORDER BY submission_date ASC'
    # logger.info(query)
    tenders = db.get_data_in_list_of_tuple(query, parameters)

    return render_template('for_update_tenders.html', tenders=tenders, user_id=username)


@app.route('/update_tender/<tender_id>', methods=['GET', 'POST'])
@login_required
def update_tender(tender_id):
    if request.method == 'POST':
        username = session.get('username')
        logger.info('Current user is %s', str(username))
        user_id = str(username)
        emd = request.form.get('emd')
        location = request.form.get('location').replace("'", "''")
        pre_bid_meeting = request.form.get('pre_bid_meeting').replace("T", " ")
        estimated_value = request.form.get('estimated_value')
        remarks = request.form.get('remarks')
        status = request.form.get('status')
        rej_rsn = request.form.getlist('rejc_rsn[]')
        if_otr_rej = request.form.get('if_other')
        rej_rsn_1 = []
        for i in rej_rsn:
            if i == 'Other':
                i += f'({str(if_otr_rej).strip()})'
            rej_rsn_1.append(i)

        r_rsn = '--'.join(rej_rsn_1) if rej_rsn_1 else ''

        # Update the tender details in the database
        query = f"""UPDATE tender.tender_management SET emd = '{str(emd)}', location = '{location}', pbm = '{pre_bid_meeting}',
        e_value = '{estimated_value}', remarks = '{remarks}', user_id = '{user_id}', verification_1 = '{status}', 
        rej_rsn = '{r_rsn}' WHERE tender_id = '{tender_id}' """

        logger.info(query)
        db.execute(query)

        query_emd = f"""update tender.tender_emd set emd_amount = '{emd}' where tender_id = '{tender_id}';"""
        db.execute(query_emd)
        ass_name = "set_to_none"
        tat_query = f"""INSERT INTO tender.tender_tat (t_id, stage, status, assign_time, assign_to, ext_col_1)
                        VALUES ('{tender_id}', 'pre_approved', 'Open', NOW(), '{ass_name}', '{username}'); """

        db.execute(tat_query)

        # Redirect to the tender details page
        return redirect(url_for('for_update'))
        # return rej_rsn

    else:
        # Retrieve the existing tender details from the database
        query = f"""SELECT emd, location, pbm, e_value, folder_location, remarks
                    FROM tender.tender_management WHERE tender_id = %s"""
        parameters = (tender_id,)
        data = db.get_data_in_list_of_tuple(query, parameters)

        emd = data[0][0]
        location = data[0][1]
        pre_bid_meeting = data[0][2]
        estimated_value = data[0][3]
        folder_loc = data[0][4].replace('/', '@@')
        remarks = data[0][5]

        try:
            pre_bid_meeting_str = datetime.datetime.strptime(pre_bid_meeting, "%Y-%m-%d") if str(pre_bid_meeting).strip() not in ('NA', '', None, 'None') else ""
        except:
            pre_bid_meeting_str = datetime.datetime.strptime(pre_bid_meeting, "%Y-%m-%d %H:%M") if str(pre_bid_meeting).strip() not in ('NA', '', None, 'None') else ""

        rejection_reason = f"""select rej_rsn from tender.rejection_reason;"""
        rej_data_check = db.get_data_in_list_of_tuple(rejection_reason)
        rej_data = [i[0] for i in rej_data_check]

        return render_template('update_for_tenders.html', tender_id=tender_id, emd=emd, location=location,
                               pre_bid_meeting=pre_bid_meeting_str, estimated_value=estimated_value,
                               folder_loc=folder_loc, remarks=remarks, rejrsn=rej_data)
        # return render_template('update_for_tenders.html', tender_id=tender_id, emd=emd, location=location,
        #                pre_bid_meeting=pre_bid_meeting_str, estimated_value=estimated_value,
        #                folder_loc=folder_loc, remarks=remarks, rejrsn=rej_data, pa=True)



@app.route('/for_submit_update_tender', methods=['GET', 'POST'])
@login_required
def for_submit_update_tender():
    username = session.get('username')
    query = """select tender_id, done, lose_state, lose_remarks, l1_amount, our_amount, customer, name_of_work, location, link, submission_date from tender.tender_management where done = 'Submitted' and
    TO_TIMESTAMP(submission_date, 'YYYY-MM-DD HH24:MI') < current_date - 10 and
    lose_state is null ORDER BY TO_TIMESTAMP(submission_date, 'YYYY-MM-DD HH24:MI') ASC limit 1"""
    data = db.get_data_in_list_of_tuple(query)
    tender_data = {
        'tender_id': data[0][0],
        'status': data[0][1],
        'lose_reason': data[0][2],
        'lose_remarks': data[0][3],
        'l1_amount': data[0][4],
        'our_amount': data[0][5],
        'customer': data[0][6],
        'name_of_work': data[0][7],
        'location': data[0][8],
        'link': data[0][9],
        'sub_date': data[0][10]
    }

    if request.method == 'POST':
        status = request.form.get('status')
        lose_reason = request.form.get('lose_reason')
        lose_remarks = request.form.get('lose_remarks')
        l1_amount = request.form.get('l1_amount')
        our_amount = request.form.get('our_amount')
        if status != 'Submitted':
            update_query = "UPDATE tender.tender_management SET done = %s, lose_state = %s, lose_remarks = %s, l1_amount = %s, our_amount = %s , user_id = %s WHERE tender_id = %s"
            db.execute(update_query, (status, lose_reason, lose_remarks, l1_amount, our_amount, username, tender_data['tender_id']))
            # print(update_query)
            # print(lose_reason, lose_remarks, l1_amount, our_amount, username, data[0])
        # Redirect to the same page to show the success message and load the next tender form
        return redirect(url_for('for_submit_update_tender'))
    return render_template('update_submitted_tenders.html', tender_data=tender_data)


@app.route('/update_oem_in_tenders/<t_id>', methods=['GET', 'POST'])
@login_required
def update_oem_in_tenders(t_id):
    username = session.get('username')
    existing_data = db.get_data_in_list_of_tuple(f"SELECT oem, status, sent_to, remarks FROM tender.oem_management WHERE tender_id = '{t_id}' ;")
    # num_entries = len(existing_data)
    if request.method == 'POST':
        if 'insert' in request.form:
            oem_list = request.form.getlist('oem[]')
            # status_list = request.form.get('status')
            sent_to_list = request.form.getlist('sent_to[]')
            remarks_list = request.form.getlist('remarks[]')

            # Insert new rows into the database
            for i in range(len(oem_list)):
                oem = oem_list[i]
                # status = status_list
                status = 'Mail Send'
                sent_to = sent_to_list[i]
                remarks = remarks_list[i]
                inserted_by = username
                inserted_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

                ins_query = f"""INSERT INTO tender.oem_management 
                            (tender_id, oem, status, sent_to, remarks, inserted_by, inserted_time) 
                            VALUES ('{t_id}', '{oem}', '{status}', '{str(sent_to).replace('T',' ')}', '{remarks}', '{inserted_by}', '{inserted_time}')"""

                logger.info(ins_query)
                # Execute the query using your database connection and cursor
                db.execute(ins_query)

            # return "New rows inserted successfully!"
            return redirect(url_for('update_oem_in_tenders', t_id=t_id))

        elif 'update' in request.form:
            update_entry_index = int(request.form.get('update_entry'))
            if update_entry_index:
                oem = request.form.get('oem')
                status = request.form.get('status')
                rec_date = request.form.get('rec_date').replace("T"," ")
                remarks = request.form.get('remarks')
                logger.info(oem)

                # Update database logic for the specific entry
                updated_by = username
                updated_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                update_query = f"""UPDATE tender.oem_management 
                                SET status='{status}', remarks='{remarks}', updated_by='{updated_by}', updated_time='{updated_time}' """
                if rec_date:
                    update_query += f", received_date='{rec_date}' "

                update_query += f" WHERE tender_id='{t_id}' AND oem='{oem}' ;"

                logger.info(update_query)
                # Execute the query using your database connection and cursor
                db.execute(update_query)

            return redirect(url_for('update_oem_in_tenders', t_id=t_id))
    try:
        query = """select oem_name from tender.list_of_oem;"""
        get_oems = db.get_data_in_list_of_tuple(query)
        get_oem = []
        for oem in get_oems:
            get_oem.append(oem[0])
    except:
        get_oem = []
    return render_template("update_oem.html", t_id=t_id, existing_data=existing_data, get_oem=get_oem)


@app.route('/insert_oem/<t_id>', methods=['GET', 'POST'])
@login_required
def insert_oem(t_id):
    username = session.get('username')
    if request.method == 'POST':
        oem_name = request.form.get('oem_name')
        if oem_name:
            inserted_by = username
            ins_query = f"""INSERT INTO tender.list_of_oem 
                        (oem_name, inserted_by) 
                        VALUES ('{oem_name}', '{inserted_by}')"""

            # Execute the query using your database connection and cursor
            db.execute(ins_query)
            inst_tat_query = f""" insert into tender.tender_tat (t_id, stage, assign_time, assign_to, ext_col_1)
            values('{t_id}', 'OEM', 'Open', now(), '{oem_name}', '{username}'); """
            db.execute(inst_tat_query)
            return redirect(url_for('update_oem_in_tenders', t_id=t_id))  # Redirect back to the same page after insertion
    
    return render_template('insert_oem.html', t_id=t_id)


@app.route('/insert_rej_rsn', methods=['GET', 'POST'])
@login_required
def insert_rej_rsn():
    username = session.get('username')
    inserted_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    if request.method == 'POST':
        rej_rsn = request.form.get('rej_rsn')
        if rej_rsn:
            inserted_by = username
            ins_query = f"""INSERT INTO tender.rejection_reason
                        (rej_rsn, ext_col_1, ext_col_2) 
                        VALUES ('{rej_rsn}', '{inserted_by}', '{inserted_time}'); """

            # Execute the query using your database connection and cursor
            db.execute(ins_query)    
    return render_template('insert_rej_rsn.html')


@app.route('/view_oems', methods=['GET'])
@login_required
def view_oem():
    username = session.get('username')
    logger.info('Current user is %s', str(username))
    filter_tender_id = request.args.get('filter_tender_id')
    filter_oem = request.args.get('filter_oem')
    filter_status = request.args.get('filter_status')

    # query = """select tender_id , oem , status , sent_to , received_date , remarks, updated_by  from tender.oem_management where remarks is not null"""
    query = """select om.tender_id , om.oem , om.status , om.sent_to, om.received_date , om.remarks , om.updated_by , tm.submission_date 
            from tender.tender_management tm right join tender.oem_management om on om.tender_id = tm.tender_id where om.remarks is not null"""

    filters = []
    parameters = []

    if filter_tender_id:
        filters.append("om.tender_id ILIKE %s")
        parameters.append(f"%{filter_tender_id.replace('/','_')}%")

    if filter_oem and filter_oem!='none':
        filters.append("om.oem ILIKE %s")
        parameters.append(f"%{filter_oem}%")
    
    # if filter_status:
    #     filters.append("status ILIKE %s")
    #     parameters.append(f"%{filter_status}%")

    logger.info(parameters)
    logger.info(filters)

    if filters:
        query += " AND " + " AND ".join(filters)

    query += ' order by sent_to asc '
    logger.info(query)
    oem_data = db.get_data_in_list_of_tuple(query, parameters)

    oem_query = "select oem_name from tender.list_of_oem;"
    oem_name = db.get_data_in_list_of_tuple(oem_query)
    names = [i[0] for i in oem_name]

    return render_template('oem_list.html', oems=oem_data, names=names)


@app.route('/tat/<id>', methods=['GET'])
@login_required
def tat_list(id):
    query = f""" select * from tender.tender_tat where t_id = '{id}'; """
    data = db.get_data_in_list_of_tuple(query)
    return render_template('tat_list.html', tenders=data)


@app.route('/all_tat_list', methods=['GET'])
@login_required
def all_tat_list():
    # query = """SELECT * FROM tender.tender_tat where stage <> 'rejected' ; """
    # query = """select * from tender.tender_tat tt where t_id not in (select t_id from tender.tender_tat tt where stage  = 'rejected' group by t_id having count(*) < 3); """
    # query = """select *  from tender.tender_tat tt where t_id not in 
    #         (select t_id from tender.tender_tat where stage in 
    #         ('approved-Not Submitted','rejected-Open','rejected-Not Submitted',
    #         'closed-Close-LOSE', 'approved-Submitted', 'rejected')); """
    query = """
        SELECT * FROM tender.tender_tat tt
        WHERE t_id NOT IN (
            SELECT tender_id
            FROM tender.tender_management
            WHERE verification_1 ILIKE 'reje%'
                OR done IN ('Submitted', 'Not Submitted', 'Close-WIN', 'Close-LOSE', 'Close-Cancel')
        )
        AND t_id NOT IN (
            SELECT t_id
            FROM tender.tender_tat
            WHERE stage IN ('approved-Not Submitted','rejected-Open','rejected-Not Submitted', 'closed-Close-LOSE', 'approved-Submitted', 'rejected')
        )
        AND t_id NOT IN (
            SELECT t_id
            FROM tender.tender_tat
            WHERE status IN ('Not Submitted', 'Not Submitted', 'Close-LOSE', 'Submitted')
                OR stage IN ('rejected', 'closed')
        );
    """

    data = db.get_row_as_dframe(query)
    data['tat'] = pd.to_timedelta(data['tat'], errors='coerce')

    pivot_table = pd.pivot_table(data, values='tat', index='t_id', columns='stage', aggfunc='sum', fill_value=pd.Timedelta(seconds=0))
    pivot_table['Total TAT'] = pivot_table.sum(axis=1)

    oem_query = """
        WITH turnaround_times AS (
            SELECT tender_id,
                CASE
                    WHEN tat IS NULL OR tat = '' THEN
                        AGE(NOW(), NOW())
                    ELSE
                        AGE(
                            NOW(),
                            NOW() - REPLACE(tat, 'days', '')::INTERVAL
                        )
                END AS total_interval
            FROM tender.oem_management
        )
        SELECT tender_id as t_id, 
            CASE WHEN EXTRACT(DAY FROM MAX(total_interval) - MIN(total_interval)) >= 0
                THEN EXTRACT(DAY FROM MAX(total_interval) - MIN(total_interval)) || ' days '
                ELSE '0:'
            END
            || LPAD(ABS(EXTRACT(HOUR FROM MAX(total_interval) - MIN(total_interval)))::TEXT, 2, '0')
            || ':'
            || LPAD(ABS(EXTRACT(MINUTE FROM MAX(total_interval) - MIN(total_interval)))::TEXT, 2, '0')
            || ':'
            || ABS(EXTRACT(SECOND FROM MAX(total_interval) - MIN(total_interval)))
            AS oem_tat
        FROM turnaround_times
        GROUP BY tender_id;
    """

    oem_tat = db.get_row_as_dframe(oem_query)

    try:
        mrg_df = pd.merge(pivot_table, oem_tat, on='t_id', how='left')
        mrg_df['oem_tat'].fillna('0 days 00:00:00.000000', inplace=True)

        # Convert 'oem_tat' column to Timedelta
        mrg_df['oem_tat'] = pd.to_timedelta(mrg_df['oem_tat'], errors='coerce')
    except Exception as e:
        print(f"An error occurred during merging: {e}")
        mrg_df = pd.DataFrame()  # or handle the error in an appropriate way
    try:
        mrg_df.drop('OEM', axis=1)
    except:
        pass
    column_order = ['t_id', 'FOR UPDATE', 'pre_approved', 'approved', 'Total TAT', 'oem_tat']
    mrg_df = mrg_df[column_order]
    mrg_df.fillna(pd.Timedelta(0), inplace=True)
    columns_to_replace_nan = ['FOR UPDATE', 'pre_approved', 'approved', 'Total TAT', 'oem_tat']
    mrg_df[columns_to_replace_nan] = mrg_df[columns_to_replace_nan].fillna('0 days 00:00:00.000000', inplace=False).astype('timedelta64[s]')
    return render_template('all_tat_list.html', tenders=data, pivot_table=mrg_df)


@app.route('/oem_tat/<id>', methods=['GET'])
@login_required
def oem_tat(id):
    query = f""" select * from tender.oem_management where tender_id = '{id}'; """
    data = db.get_data_in_list_of_tuple(query)
    return render_template('oem_tat_list.html', tenders=data)


@app.route('/result_details/<t_id>', methods=['GET'])
def display_result_details(t_id):

    query = f"""SELECT result_details FROM tender.gem_res_details where t_id = '{t_id}' and result_details is not null;"""
    result_details = db.get_data_in_list_of_tuple(query)
    if result_details:
        return render_template('result_details.html', result_details=result_details[0][0])
    return render_template('result_details.html', result_details=result_details)


@app.route('/reports_1', methods=['GET'])
def reports_1():

    query_bot = """
    SELECT tender_id, inserted_time, inserted_user_id
    FROM tender.tender_management
    WHERE TO_DATE(inserted_time, 'DD-MM-YYYY HH24:MI:SS')::date >= current_date - 7
    AND inserted_user_id ILIKE '%BOT';
    """
    df_bot = db.get_row_as_dframe(query_bot)
    # bot_csv_path = os.path.join(folder_path, 'inserted_by_bot.csv')
    # df_bot.to_csv(bot_csv_path, index=False)

    # Query for rejected
    query_rejected = """
    SELECT DISTINCT ON (t.tender_id)
        t.tender_id, t.name_of_work, t.customer, t.inserted_time, t.inserted_user_id, t.verification_1, t.done
    FROM tender.tender_management_history t
    WHERE t.change_timestamp IN (
        SELECT DISTINCT ON (t2.tender_id) t2.change_timestamp
        FROM tender.tender_management_history t2
        WHERE t2.verification_1 = 'rejected' OR t2.done = 'Not Submitted'
        ORDER BY t2.tender_id, t2.change_timestamp DESC
    ) AND t.change_timestamp::date >= current_date - 7
    ORDER BY t.tender_id, t.change_timestamp DESC limit 10;
    """
    df_rejected = db.get_row_as_dframe(query_rejected)
    # rejected_csv_path = os.path.join(folder_path, 'rejected.csv')
    # df_rejected.to_csv(rejected_csv_path, index=False)

    # Query for submitted
    query_submitted = """
    SELECT DISTINCT ON (t.tender_id)
        t.tender_id, t.name_of_work, t.customer, t.inserted_time, t.inserted_user_id, t.verification_1, t.done
    FROM tender.tender_management_history t
    WHERE t.change_timestamp IN (
        SELECT DISTINCT ON (t2.tender_id) t2.change_timestamp
        FROM tender.tender_management_history t2
        WHERE t2.done = 'Submitted'
        ORDER BY t2.tender_id, t2.change_timestamp DESC
    ) AND t.change_timestamp::date >= current_date - 7
    ORDER BY t.tender_id, t.change_timestamp DESC;
    """
    df_submitted = db.get_row_as_dframe(query_submitted)
    # submitted_csv_path = os.path.join(folder_path, 'submitted.csv')
    # df_submitted.to_csv(submitted_csv_path, index=False)

    return render_template('reports_1.html', df_bot=df_bot, df_rejected=df_rejected, df_submitted=df_submitted)


@app.route('/reports_2', methods=['GET', 'POST'])
def reports_2():
    e_dt = datetime.datetime.now().date().strftime('%Y-%m-%d')
    s_dt = (datetime.datetime.now().date() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    # if request.method == 'POST':
    s_dt  = request.args.get('start_date',s_dt)
    e_dt  = request.args.get('end_date',e_dt)
    user = request.args.get('user_id', '')

    ins_for_update_query = f""" SELECT 
                            CASE 
                                WHEN inserted_user_id ILIKE '%BOT' THEN 'BOT'
                                ELSE inserted_user_id
                            END AS modified_user_id, 
                            COUNT(*) AS count
                        FROM tender.tender_management tm
                        WHERE TO_DATE(tm.inserted_time, 'DD-MM-YYYY HH24:MI:SS')::date BETWEEN '{s_dt}' AND '{e_dt}' 
                        GROUP BY modified_user_id; """
    ins_for_update_data = db.get_row_as_dframe(ins_for_update_query)
    
    pre_appv_query = f""" SELECT COUNT(*) AS count, user_id 
                    FROM (SELECT DISTINCT ON (tender_id) *
                            FROM tender.tender_management_history
                            WHERE change_timestamp::date BETWEEN '{s_dt}' AND '{e_dt}' AND verification_1 = 'pre_approved'
                            and (done is null or done <> 'New-Corrigendum') ORDER BY tender_id, change_timestamp ASC
                        ) AS tm GROUP BY user_id; """
    pre_appv_data = db.get_row_as_dframe(pre_appv_query)
    
    appv_query = f""" SELECT COUNT(*) AS count, user_id FROM (
                    SELECT DISTINCT ON (tender_id) * FROM tender.tender_management_history
                    WHERE change_timestamp::date BETWEEN '{s_dt}' AND '{e_dt}' AND 
                    verification_1 = 'approved' and (done = 'Open') ORDER BY tender_id, change_timestamp ASC
                ) AS tm GROUP BY user_id; """
    appv_data = db.get_row_as_dframe(appv_query)
    
    rej_query = f"""  SELECT COUNT(*) AS count, user_id FROM ( SELECT DISTINCT ON (tender_id) *
                FROM tender.tender_management_history WHERE change_timestamp::date BETWEEN '{s_dt}' AND '{e_dt}'
                    AND ((verification_1 = 'rejected' and (done <> 'New-Corrigendum' or done is null)) or 
                    (done = 'Not Submitted' and verification_1 = 'approved')) ORDER BY tender_id, change_timestamp ASC
                ) AS tm GROUP BY user_id; """
    rej_data = db.get_row_as_dframe(rej_query)
    
    try:
        ins_for_update_data = ins_for_update_data.rename(columns={'modified_user_id': 'user_id'})
        summary_data = pd.merge(ins_for_update_data, pre_appv_data, on='user_id', how='outer', suffixes=('_Insert', '_Pre_Approve'))
        summary_data = pd.merge(summary_data, appv_data, on='user_id', how='outer', suffixes=('', '_Approved'))
        summary_data = pd.merge(summary_data, rej_data, on='user_id', how='outer', suffixes=('_Approved', '_Rejected'))
        
        summary_data = summary_data.fillna(0)
        
        summary_data['count_Insert'] = summary_data['count_Insert'].astype(int)
        summary_data['count_Pre_Approve'] = summary_data['count_Pre_Approve'].astype(int)
        summary_data['count_Approved'] = summary_data['count_Approved'].astype(int)
        summary_data['count_Rejected'] = summary_data['count_Rejected'].astype(int)
    except:
        summary_data = pd.DataFrame([], columns=('count','user_id'))

    user_ids = summary_data['user_id'].dropna().tolist() if not summary_data.empty else []

    if user:
        summary_data = summary_data[summary_data['user_id'] == user]

    summary_data['Total'] = summary_data.sum(numeric_only=True, axis=1).astype(int)

    # Calculate column total and add it as a new row
    total_row = summary_data.sum(numeric_only=True)
    total_row['user_id'] = 'Total'

    # Concatenate the 'Total' row to the DataFrame
    summary_data = pd.concat([summary_data, total_row.to_frame().T], ignore_index=True, sort=False)

    # Convert all numeric columns to integer
    numeric_columns = summary_data.select_dtypes(include='number').columns
    summary_data[numeric_columns] = summary_data[numeric_columns].apply(pd.to_numeric, errors='coerce', downcast='integer')


    table_html = summary_data.to_html(classes='table table-striped', index=False)
    return render_template('reports_2.html', table_html=table_html, s_dt=s_dt, e_dt=e_dt, user_ids=user_ids)
    

if __name__ == '__main__':
    # app.run(host='103.223.15.47', port=5010, debug=True)
    # app.run(host='192.168.0.137', port=5010, debug=True)
    # app.run(host='192.168.1.190', port=5010, debug=True)
    app.run(host='0.0.0.0', port=5010, debug=True)

