# import os
# from google.oauth2 import service_account
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaFileUpload
# import glob

# # Replace with the path to your client ID JSON file
# credentials_file = 'client_secret_577067719554-mlsn80v926ful9up48ndg6h6rcegioov.apps.googleusercontent.com.json'

# # Create a service object for Google Drive
# # credentials = service_account.Credentials.from_service_account_file(
# #     credentials_file, ['https://www.googleapis.com/auth/drive'])
# credentials = service_account.Credentials.from_service_account_file(credentials_file, scopes=['https://www.googleapis.com/auth/drive'])
# service = build('drive', 'v3', credentials=credentials)

# # Find the latest backup file in the current working directory
# latest_backup_file = max(glob.glob(os.path.join(os.getcwd(),'bkp_files', '*.sql')), key=os.path.getctime)

# # File metadata
# file_metadata = {
#     'name': os.path.basename(latest_backup_file)
# }

# # Upload the latest backup file to Google Drive
# media = MediaFileUpload(latest_backup_file, mimetype='application/sql')
# file = service.files().create(body=file_metadata, media_body=media).execute()

# print(f'File ID: {file["id"]}')
