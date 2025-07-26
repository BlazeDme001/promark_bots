import subprocess
import datetime
import os
import mail
import glob
import requests
from werkzeug.utils import secure_filename
import paramiko
from tempfile import NamedTemporaryFile
import datetime
import mail
import send_wp
import time
import pdfplumber

db_host = 'localhost'
db_port = '5400'
db_name = 'postgres'
db_user = 'postgres'
db_password = '7980'

# Set the PGPASSWORD environment variable
os.environ['PGPASSWORD'] = db_password

pg_dump_path = r'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe'
NAS_HOST = '******'
NAS_PORT = 22
NAS_USERNAME = '****'
NAS_PASSWORD = '********'
# NAS_UPLOAD_FOLDER = '************'
NAS_UPLOAD_FOLDER = '*********'
# NAS_UPLOAD_FOLDER_1 = r'/mnt/tender_auto'



def move_bkp_nas(source_file, destination_path):
    try:
        with paramiko.SSHClient() as ssh_client:
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(NAS_HOST, NAS_PORT, NAS_USERNAME, NAS_PASSWORD)

            try:
                sftp = ssh_client.open_sftp()
                try:
                    sftp.chdir(destination_path)
                except FileNotFoundError:
                    sftp.mkdir(destination_path)
                sftp.put(source_file, os.path.join(destination_path,source_file.split('/')[-1]))
                sftp.close()
            except Exception as e:
                print(f"Failed to move the file to NAS: {str(e)}")
    except Exception as e:
        print(f"Failed to connect to NAS: {str(e)}")


def create_bkp():
    try:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_dir = 'bkp_files_1'
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = os.path.join(backup_dir, f'db_backup_{timestamp}.sql')

        # backup_command = [
        #     'pg_dump',
        #     '-h', db_host,
        #     '-p', db_port,
        #     '-U', db_user,
        #     '-d', db_name,
        #     '-f', backup_file
        # ]

        backup_command = f'"{pg_dump_path}" -h {db_host} -p {db_port} -U {db_user} -d {db_name} -f {backup_file}'

        try:
            subprocess.run(backup_command, check=True)
            print(f'Backup completed. File saved as {backup_file}')
            latest_backup_file = max(glob.glob(os.path.join(os.getcwd(),'bkp_files_1', '*.sql')), key=os.path.getctime)
            move_bkp_nas(latest_backup_file, NAS_UPLOAD_FOLDER)
            try:
                sub = 'Backup Sucessful'
                body = f'''
                Hi Ramit,

                We are successfully taken the backup.
                loc: {latest_backup_file}

                Thanks & Regards,
                Backup Bot
                '''
                # attachment = [latest_backup_file]
                mail.send_mail(to_add=['ramit.shreenath@gmail.com'], to_cc=[], sub=sub, body=body, attach=[])
            except Exception as err:
                raise Exception(err)
            # send_wp.send_wp_attach('7980328205', 'Backup text', latest_backup_file)
        except subprocess.CalledProcessError as e:
            print(f'Error during backup: {e.stderr}')
    except Exception as er:
        print(str(er))
        body = '''
        Hi Ramit,

        We are having error while taking backup of DB.
        Please check and do the needful.

        Thanks & regards,
        Backup Bot
        '''
        mail.send_mail(to_add=['ramit.shreenath@gmail.com'],sub='Error wjile taking backup of DB', body=body)


while True:
    print('Starting Backup BOT')
    create_bkp()
    print('Backup BOT will start after 24 hours')
    time.sleep(86400)

