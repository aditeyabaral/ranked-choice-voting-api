import os
import pytz
import logging
import datetime
import gh_md_to_html
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from urllib.parse import urlparse
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
    # TODO: Add error handling -> required fields
    election_id = request.json.get('election_id', election_db.generate_election_id(election_db))
    created_at = datetime.datetime.now(IST)
    created_by = request.headers.getlist("X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr
    election_name = request.json.get('election_name', None)
    start_time = request.json.get('start_time', created_at)
    end_time = request.json.get('end_time', None)
    description = request.json.get('description', None)
    anonymous = request.json.get('anonymous', False)
    candidates = request.json.get('candidates', None)
    return election_id, created_at, created_by, election_name, start_time, end_time, description, anonymous, candidates

def get_election_data_get(request):
    # TODO: Add error handling -> required fields
    election_id = election_db.generate_election_id(election_db)
    created_at = datetime.datetime.now(IST)
    created_by = request.headers.getlist("X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr
    election_name = None
    start_time = created_at
    end_time = None
    description = None
    anonymous = False
    candidates = request.view_args.get('candidates', None).split('/')
    return election_id, created_at, created_by, election_name, start_time, end_time, description, anonymous, candidates

def convert_readme_to_html():
    if "README.html" not in os.listdir():
        html = gh_md_to_html.main("README.md").strip()
        with open("README.html", "w") as f:
            f.write(html)

@app.route("/")
def index():
    if "README.html" not in os.listdir():
       convert_readme_to_html()
    with open("README.html") as f:
        output = f.read()
        return output, 200

@app.route("/add", methods=['POST'])
@app.route("/add/<path:candidates>", methods=['GET'])
def create_election(**candidates):
    # TODO: Check if candidates are unique
    http_prefix = "https" if request.is_secure else "http"
    if request.method == 'POST':
        request_parser = get_election_data_post
    else:
        request_parser = get_election_data_get
    
    election_id, created_at, created_by, election_name, start_time, end_time, description, anonymous, candidates = request_parser(request)
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
        return jsonify(election_data), 200
    except Exception as e:
        logging.error(f"Exception while creating election: {e}")
        # TODO: Return JSON response, similar to add/
        return f"Error while creating election. Ensure you follow the instructions in the README while adding an election!\nError: {e}", 500

@app.route("/<election_id>", methods=['GET'])
def election_page(election_id):
    # TODO: Handle wrong election ID
    election_data = election_db.get_election_data(election_id)
    logging.debug(f"Election data fetched: {election_data}")
    ip_address = request.headers.getlist("X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr
    if election_data['anonymous'] and ip_address != election_data['created_by']:
        del election_data['votes']
    return jsonify(election_data), 200

@app.route("/vote/<election_id>/<path:votes>", methods=['GET'])
def add_vote(election_id, votes):
    # TODO: Handle wrong election ID
    http_prefix = "https" if request.is_secure else "http"
    ip_address = request.headers.getlist("X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr
    votes = votes.split('/')
    votes = list(filter(bool, votes))
    logging.debug(f"Ranked votes by {ip_address}: {votes}")
    election_url = f"{http_prefix}://{urlparse(request.base_url).netloc}/{election_id}"
    output = {'election_url': election_url}
    try:
        election_db.add_vote(election_id, ip_address, votes)
        output['status'] = True
        output['message'] = None
    except Exception as e:
        logging.error(f"Exception while voting: {e}")
        output['status'] = False
        output['message'] = e
    return jsonify(output), 500

if __name__ == "__main__":
    election_db = ElectionDatabase()
    convert_readme_to_html()
    app.run(host='0.0.0.0', port = int(os.environ.get("PORT", 5000)))