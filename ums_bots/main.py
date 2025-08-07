from flask import Flask, request, jsonify
import db_connect as db  # your custom DB module
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('user_api')


@app.route('/user', defaults={'username': None}, methods=['GET'])
@app.route('/user/<username>', methods=['GET'])
def get_user(username):
    try:
        if username:
            query = f"""
                SELECT username, "password", team, "name", profile, mobile, email, status, date_stamp
                FROM tender.user_details 
                WHERE username = '{username}'
            """
            df = db.get_row_as_dframe(query)
        else:
            query = """
                SELECT username, "password", team, "name", profile, mobile, email, status, date_stamp
                FROM tender.user_details
            """
            df = db.get_row_as_dframe(query)

        if df is None or df.empty:
            return jsonify({"status": "not found", "data": None}), 404

        data = df.to_dict(orient="records")
        if username:
            return jsonify({"status": "success", "data": data[0]}), 200
        else:
            return jsonify({"status": "success", "data": data}), 200

    except Exception as e:
        logger.error(str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/user', methods=['POST'])
def insert_user():
    try:
        data = request.get_jsondate_stamp
        required_fields = ["username", "password", "team", "name", "profile", "mobile", "email", "status"]

        if not all(field in data for field in required_fields):
            return jsonify({"status": "error", "message": "Missing fields in request"}), 400

        db.insert_dict_into_table("tender.user_details", data)
        return jsonify({"status": "success", "message": "User inserted"}), 201
    except Exception as e:
        logger.error(str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/user/<username>', methods=['PUT'])
def update_user(username):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data to update"}), 400

        set_clause = ", ".join([f"{k} = %s" for k in data.keys()])
        values = list(data.values())
        values.append(username)

        query = f"UPDATE tender.user_details SET {set_clause} WHERE username = %s"
        db.execute(query, tuple(values))
        return jsonify({"status": "success", "message": "User updated"}), 200
    except Exception as e:
        logger.error(str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/user/<username>', methods=['DELETE'])
def delete_user(username):
    try:
        query = "DELETE FROM tender.user_details WHERE username = %s"
        db.execute(query, (username,))
        return jsonify({"status": "success", "message": f"User '{username}' deleted"}), 200
    except Exception as e:
        logger.error(str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/user/drop_table', methods=['POST'])
def drop_user_table():
    try:
        secret = request.args.get("secret")
        if secret != "your_secret_token":
            return jsonify({"status": "error", "message": "Unauthorized"}), 403

        query = "DROP TABLE IF EXISTS tender.user_details"
        db.execute(query)
        return jsonify({"status": "success", "message": "user_details table dropped"}), 200
    except Exception as e:
        logger.error(str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True, port=5001)
