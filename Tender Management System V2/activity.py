import db_connect as db
import datetime

def log_activity(username, activity, start_time, end_time, time_spent):
    query = "INSERT INTO tender.user_activity (username, activity, start_time, end_time, time_spent) VALUES (%s, %s, %s, %s, %s)"
    params = [username, activity, start_time, end_time, time_spent]
    db.execute(query, params)
