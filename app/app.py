import os
import pytz
import logging
import datetime
from dotenv import load_dotenv
from flask import Flask, request
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

@app.route("/")
def index():
    output = "A simple app for <a href='https://www.rankedvote.co/guides/understanding-ranked-choice-voting/how-does-ranked-choice-voting-work'>ranked-choice voting</a> in an election.<br><br>\n"
    output += "Ranked-voting is a Flask app that serves API endpoints for a ranked-choice voting, supporting both creation of elections, retrieval of results and casting of votes using HTTP requests.<br><br>\n"
    output += "You can learn more about the app including instructions to use it on the <a href='https://github.com/aditeyabaral/ranked-voting'>GitHub repository</a><br><br>"
    output = f"<html><body>{output}</body></html>"
    return output, 200

@app.route("/add", methods=['POST'])
@app.route("/add/<path:candidates>", methods=['GET'])
def create_election(**candidates):
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
        'candidates': candidates
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
    except Exception as e:
        logging.error(f"Exception while creating election: {e}")
        return f"Error while creating election. Ensure you follow the instructions in the README while adding an election!\nError: {e}", 500

    output = f"Your election has been successfully created! Here is your Election ID: {election_id}<br>\nYou can find your election's details on <a href='{http_prefix}://{urlparse(request.base_url).netloc}/{election_id}'>this link</a>"
    output = f"<html><body>{output}</body></html>"
    return output, 200

@app.route("/<election_id>", methods=['GET'])
def election_page(election_id):
    # TODO: format in following way and return
    # Election ID: {election_id}
    # Election Name: {election_data['election_name']}
    # Election Description: {election_data['description']}
    # Election Candidates: {election_data['candidates']}"
    # ...
    election_data = election_db.get_election_data(election_id)
    logging.debug(f"Election data fetched: {election_data}")
    ip_address = request.headers.getlist("X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr
    output = str()
    for key in election_data:
        if ((key == "votes" and election_data['created_by'] == ip_address) or key != "votes"):
            output += f"{key}: {election_data[key]}<br>\n"
    output = f"<html><body>{output}</body></html>"
    return output, 200

@app.route("/vote/<election_id>/<path:votes>", methods=['GET'])
def add_vote(election_id, votes):
    http_prefix = "https" if request.is_secure else "http"
    ip_address = request.headers.getlist("X-Forwarded-For")[0] if request.headers.getlist("X-Forwarded-For") else request.remote_addr
    votes = votes.split('/')
    votes = list(filter(bool, votes))
    logging.debug(f"Ranked votes by {ip_address}: {votes}")
    try:
        election_db.add_vote(election_id, ip_address, votes)
        output = f"Your vote has been successfully recorded! You can now view the election results on <a href='{http_prefix}://{urlparse(request.base_url).netloc}/{election_id}'>this link</a>"
        output = f"<html><body>{output}</body></html>"
        return output, 200
    except Exception as e:
        logging.error(f"Exception while voting: {e}")
        return f"Error while voting: {e}", 500

if __name__ == "__main__":
    election_db = ElectionDatabase()
    app.run(host='0.0.0.0', port = int(os.environ.get("PORT", 5000)))