from flask import Flask, jsonify, request
import db_connect as db

app = Flask(__name__)

# @app.route('/user_details', methods=['GET'])
# def get_user_details():
#     query = "SELECT username, password FROM tender.user_details"
#     data = db.get_row_as_dframe(query)

#     # Convert the data to a list of dictionaries
#     user_details = data.to_dict(orient='records')

#     # Return the response as JSON
#     return jsonify(user_details)


@app.route('/tenders', methods=['GET'])
def get_tenders():
    query = "select * from tender.tender_folder ; "
    data = db.get_row_as_dframe(query)
    tenders = data.to_dict(orient='records')
    return jsonify(tenders)


@app.route('/update_data', methods=['POST'])
def update_data():
    data = request.get_json()
    if data is None:
        return jsonify({'error': 'Invalid request data'}), 400

    # varification_1 = data.get('value1')
    # ext_col_1 = data.get('value2')
    tender_id = data.get('value3')

    # if varification_1 is None or ext_col_1 is None:
    #     return jsonify({'error': 'Missing required data fields'}), 400

    # Update the database with the provided values
    # query = f"""UPDATE table_name SET verification_2 = '{varification_1}', ext_col_1 = '{ext_col_1}' where tender_id = '{tender_id}' """
    query = f"""UPDATE tender.tender_folder SET open_folder = 'no' where tender_id = '{tender_id}' """
    db.execute(query)

    return jsonify({'message': 'Data updated successfully'})


@app.route('/filtered_tenders', methods=['GET'])
def get_filtered_tenders():
    # filter_params = request.args.to_dict()

    data = request.get_json()
    open_folder = data.get('open_folder')
    user_id = data.get('user_id')

    query = f"SELECT * FROM tender.tender_folder where open_folder = '{open_folder}' and user_id = '{user_id}' limit 1;"
    data = db.get_row_as_dframe(query)
    if not data.empty:
        t_id = [i['tender_id'] for _,i in data.iterrows()]

        query_1 = f"""select folder_location from tender.tender_management where tender_id = '{t_id[0]}' limit 1"""
        f_loc = db.get_data_in_list_of_tuple(query_1)[0][0]
        data['folder_location'] = f_loc
    
    filtered_tenders = data.to_dict(orient='records')
    return jsonify(filtered_tenders)


if __name__ == '__main__':
    # print('192.168.0.16:5012')
    # app.run(host='192.168.1.190', port=5012, debug=True)
    app.run(host='192.168.0.16', port=5012, debug=True)
