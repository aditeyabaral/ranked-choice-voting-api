import os
import pytz
import logging
import datetime
import gh_md_to_html
from dotenv import load_dotenv
from urllib.parse import urlparse
from flask import Flask, jsonify, request

from db import ElectionDatabase

logging.basicConfig(
    level=logging.NOTSET,
    filemode='w',
    filename='app.log',
    format='%(asctime)s - %(levelname)s - %(name)s - %(filename)s - %(funcName)s - %(lineno)d - %(message)s'
)

load_dotenv()
app = Flask(__name__)
IST = pytz.timezone('Asia/Kolkata')


def get_election_data_post(request):
    election_id = request.json.get(
        'election_id', election_db.generate_election_id(election_db))
    if election_db.check_election_id_exists(election_id):
        raise Exception(
            "Election ID already exists. Please choose a different one or do not specify one.")
    created_at = datetime.datetime.now(IST)
    created_by = request.headers.getlist(
        "X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr
    election_name = request.json.get('election_name', None)
    start_time = request.json.get('start_time', created_at)
    end_time = request.json.get('end_time', None)
    description = request.json.get('description', None)
    anonymous = request.json.get('anonymous', False)
    candidates = request.json.get('candidates', None)
    if len(candidates) != len(set(candidates)):
        raise Exception("Candidates must be unique")
    return election_id, created_at, created_by, election_name, start_time, end_time, description, anonymous, candidates


def get_election_data_get(request):
    election_id = election_db.generate_election_id(election_db)
    created_at = datetime.datetime.now(IST)
    created_by = request.headers.getlist(
        "X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr
    election_name = None
    start_time = created_at
    end_time = None
    description = None
    anonymous = False
    candidates = request.view_args.get('candidates', None).split('/')
    if len(candidates) != len(set(candidates)):
        raise Exception("Candidates must be unique")
    return election_id, created_at, created_by, election_name, start_time, end_time, description, anonymous, candidates


def convert_readme_to_html():
    if "README.html" not in os.listdir():
        html = gh_md_to_html.main("README.md").strip()
        with open("README.html", "w") as f:
            f.write(html)


@app.route("/")
def index():
    try:
        if "README.html" not in os.listdir():
            convert_readme_to_html()
        with open("README.html") as f:
            output = f.read()
            return output, 200
    except Exception as e:
        logging.error(f"Error rendering home page: {e}")
        return "Error occurred while retrieving home page", 500


@app.route("/add", methods=['POST'])
@app.route("/add/<path:candidates>", methods=['GET'])
def create_election(**candidates):
    http_prefix = "https" if request.is_secure else "http"
    try:
        if request.method == 'POST':
            request_parser = get_election_data_post
        else:
            request_parser = get_election_data_get
    except Exception as e:
        logging.error(f"Error in creating election - {request}: {e}")
        output = {
            "status": False,
            "message": "Error occurred while creating election. This might be due to invalid data in the request.",
            "error": str(e)
        }
        return jsonify(output), 400

    election_id, created_at, created_by, election_name, start_time, end_time, description, anonymous, candidates = request_parser(
        request)
    election_data = {
        'election_id': election_id,
        'created_at': created_at,
        'created_by': created_by,
        'election_name': election_name,
        'start_time': start_time,
        'end_time': end_time,
        'description': description,
        'anonymous': anonymous,
        'candidates': candidates,
        'election_url': f"{http_prefix}://{urlparse(request.base_url).netloc}/{election_id}"
    }
    logging.debug(f"Election creation data: {election_data}")

    try:
        election_db.add_election(
            election_id,
            created_at,
            created_by,
            election_name,
            start_time,
            end_time,
            description,
            anonymous,
            candidates
        )
        output = {
            "status": True,
            "message": "Election created successfully.",
            "data": election_data
        }
        response_code = 201
    except Exception as e:
        logging.error(f"Exception while inserting new election: {e}")
        output = {
            "status": False,
            "message": "Error occurred while creating election. This might be due to a database error. Contact the administrators for more information.",
            "error": str(e)
        }
        response_code = 400
    return jsonify(output), response_code


@app.route("/remove/<election_id>", methods=['GET'])
def remove_election(election_id):
    try:
        if not election_db.check_election_id_exists(election_id):
            raise Exception("Election ID does not exist")
    except Exception as e:
        logging.error(
            f"Exception occurred while removing election {election_id}: {e}")
        output = {
            "status": False,
            "message": f"Error occurred while removing election. This might be due to an invalid election ID.",
            "error": str(e)
        }
        return jsonify(output), 400

    output = dict()
    ip_address = request.headers.getlist(
        "X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr
    logging.debug(
        f"Election removal request from {ip_address} for election {election_id}")
    try:
        election_data = election_db.get_election_data(election_id)
        election_db.remove_election(election_id, ip_address)
        output["status"] = True
        output["message"] = f"Election {election_id} removed successfully"
        output["data"] = election_data
        response_code = 200
    except Exception as e:
        logging.error(f"Exception occurred while removing election: {e}")
        output["status"] = False
        output["message"] = f"Error occurred while removing election {election_id}. This might be due to a database error. Contact the administrators for more information."
        output["error"] = e
        response_code = 400
    return jsonify(output), response_code


@app.route("/<election_id>", methods=['GET'])
def election_page(election_id):
    try:
        if not election_db.check_election_id_exists(election_id):
            raise Exception("Election ID does not exist")
    except Exception as e:
        logging.error(
            f"Exception occurred while retrieving election {election_id} details: {e}")
        output = {
            "status": False,
            "message": f"Error occurred while retrieving election details. This might be due to an invalid election ID.",
            "error": str(e)
        }
        return jsonify(output), 400

    try:
        election_data = election_db.get_election_data(election_id)
        logging.debug(f"Election data fetched: {election_data}")
        ip_address = request.headers.getlist(
            "X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr
        if election_data['anonymous'] and ip_address != election_data['created_by']:
            del election_data['votes']
        output = {
            "status": True,
            "message": "Election details fetched successfully.",
            "data": election_data
        }
        response_code = 200
    except Exception as e:
        logging.error(
            f"Exception occurred while retrieving election details for {election_id}: {e}")
        output = {
            "status": False,
            "message": f"Error occurred while retrieving election details for {election_id}. This might be due to a database error. Contact the administrators for more information.",
            "error": str(e)
        }
        response_code = 400
    return jsonify(output), response_code


@app.route("/vote/<election_id>/<path:votes>", methods=['GET'])
def add_vote(election_id, votes):
    try:
        if not election_db.check_election_id_exists(election_id):
            raise Exception("Election ID does not exist")
    except Exception as e:
        logging.error(
            f"Exception occurred while adding vote to {election_id}: {e}")
        output = {
            "status": False,
            "message": f"Error occurred while adding vote. This might be due to an invalid election ID.",
            "error": str(e)
        }
        return jsonify(output), 400

    http_prefix = "https" if request.is_secure else "http"
    ip_address = request.headers.getlist(
        "X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr
    votes = votes.split('/')
    votes = list(filter(bool, votes))
    try:
        num_votes = len(votes)
        assert num_votes > 0 and num_votes == len(set(votes))
        assert num_votes == len(
            election_db.get_election_candidates(election_id))
    except Exception as e:
        logging.error(f"Exception occurred while adding vote: {e}")
        output = {
            "status": False,
            "message": f"Error occurred while adding vote. This might be due to an invalid candidates.",
            "error": str(e)
        }
        return jsonify(output), 400

    logging.debug(f"Ranked votes by {ip_address}: {votes}")
    output = dict()
    try:
        election_db.add_vote(election_id, ip_address, votes)
        output['status'] = True
        output['message'] = "Vote added successfully."
        response_code = 200
    except Exception as e:
        logging.error(f"Exception occurred while adding vote: {e}")
        output['status'] = False
        output['message'] = "Error occurred while adding vote. This might be due to a database error. Contact the administrators for more information."
        output['error'] = e
        response_code = 400
    return jsonify(output), response_code


@app.route("/unvote/<election_id>", methods=['GET'])
def remove_vote(election_id):
    try:
        if not election_db.check_election_id_exists(election_id):
            raise Exception("Election ID does not exist")
    except Exception as e:
        logging.error(
            f"Exception occurred while removing vote from {election_id}: {e}")
        output = {
            "status": False,
            "message": f"Error occurred while removing vote. This might be due to an invalid election ID.",
            "error": str(e)
        }
        return jsonify(output), 400

    http_prefix = "https" if request.is_secure else "http"
    ip_address = request.headers.getlist(
        "X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr
    logging.debug(f"Unvoting for {ip_address} from election {election_id}")
    output = dict()
    try:
        election_db.remove_vote(election_id, ip_address)
        output['status'] = True
        output['message'] = "Vote removed successfully."
        response_code = 200
    except Exception as e:
        logging.error(f"Exception occurred while unvoting: {e}")
        output['status'] = False
        output['message'] = "Error occurred while removing vote. This might be due to a database error. Contact the administrators for more information."
        output['error'] = e
        response_code = 400
    return jsonify(output), response_code


if __name__ == "__main__":
    election_db = ElectionDatabase()
    convert_readme_to_html()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
