import logging
import os
import traceback
from typing import Any
from urllib.parse import urlparse

import gh_md_to_html
from bson import ObjectId
from dotenv import load_dotenv
from flask import Flask, jsonify, request

import helper
from db import ElectionDatabase

logging.basicConfig(
    level=logging.INFO,
    filemode="w",
    filename="app.log",
    format="%(asctime)s - %(levelname)s - %(name)s - %(filename)s - %(funcName)s - %(lineno)d - %(message)s",
)

load_dotenv()
app = Flask(__name__)


# TODO: Update routes

def convert_readme_to_html():
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
        stacktrace = traceback.format_exc()
        logging.error(f"Error rendering home page: {e}: {stacktrace}")
        return "Error occurred while retrieving home page", 500


@app.route("/addElection", methods=["POST"])
@app.route("/addElection/<path:candidates>", methods=["GET"])
def add_election(**candidates: str):
    logging.info(f"Received request to create new election")
    http_prefix = "https" if request.is_secure else "http"
    if request.method == "POST":
        request_parser = helper.parse_election_creation_data_from_post_request
    else:
        request_parser = helper.parse_election_creation_data_from_get_request

    try:
        election: dict[str, Any] = request_parser(request)
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"Error in creating election - {request}: {e}: {stacktrace}")
        output = {
            "status": False,
            "message": "Error occurred while creating election. This might also be due to invalid data in the request.",
            "error": str(e),
        }
        return jsonify(output), 400

    try:
        _id = str(election_db.add_election(election))
        election["_id"] = _id
        election["url"] = f"{http_prefix}://{urlparse(request.base_url).netloc}/{_id}"
        logging.info(f"Created new election with ID: {_id}")
        output = {
            "status": True,
            "message": "Election created successfully.",
            "data": election,
        }
        response_code = 201
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"Exception while inserting new election: {e}: {stacktrace}")
        output = {
            "status": False,
            "message": "Error occurred while creating election. This might also be due to a database error. Contact the administrators for more information.",
            "error": str(e),
        }
        response_code = 400

    return jsonify(output), response_code


@app.route("/removeElection/<_id>", methods=["GET"])
def remove_election(_id: str):
    logging.info(f"Received request to remove election with ID: {_id}")
    ip_address = (
        request.headers.getlist("X-Forwarded-For")[0]
        if request.headers.getlist("X-Forwarded-For")
        else request.remote_addr
    )

    try:
        election = election_db.get_election_by_id(_id)
        logging.info(f"Fetched election with ID: {_id} for removal")
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"Error in removing election - {_id}: {e}: {stacktrace}")
        output = {
            "status": False,
            "message": f"Error occurred while fetching election with ID: {_id}",
            "error": str(e),
        }
        return jsonify(output), 400

    if election["creator"] != ip_address:
        logging.warning(f"Unauthorized attempt to remove election - {_id} by {ip_address}")
        output = {
            "status": False,
            "message": "You are not authorized to remove this election.",
        }
        return jsonify(output), 401
    else:
        try:
            logging.info(f"Removing election with ID: {_id}")
            election_db.remove_election(_id)
        except Exception as e:
            stacktrace = traceback.format_exc()
            logging.error(f"Error in removing election - {_id}: {e}: {stacktrace}")
            output = {
                "status": False,
                "message": f"Error occurred while removing election {_id}",
                "error": str(e),
            }
            return jsonify(output), 400
        output = {
            "status": True,
            "message": "Election removed successfully.",
        }
        return jsonify(output), 200


@app.route("/viewElection/<_id>", methods=["GET"])
def view_election(_id: str):
    logging.info(f"Received request to view election with ID: {_id}")
    ip_address = (
        request.headers.getlist("X-Forwarded-For")[0]
        if request.headers.getlist("X-Forwarded-For")
        else request.remote_addr
    )

    try:
        election = election_db.get_election_by_id(_id)
        if isinstance(election["_id"], ObjectId):
            election["_id"] = str(election["_id"])
        logging.info(f"Fetched election with ID: {_id} for rendering")
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"Error in fetching election - {_id}: {e}: {stacktrace}")
        output = {
            "status": False,
            "message": f"Error occurred while fetching election with ID: {_id}",
            "error": str(e),
        }
        return jsonify(output), 400

    try:
        if election["anonymous"] and election["creator"] != ip_address and "ballots" in election:
            del election["ballots"]
        output = {
            "status": True,
            "message": "Election details fetched successfully.",
            "data": election,
        }
        response_code = 200
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"Error in deleting ballots from election - {_id}: {e}: {stacktrace}")
        output = {
            "status": False,
            "message": f"Error occurred while fetching election with ID: {_id}",
            "error": str(e),
        }
        response_code = 400

    return jsonify(output), response_code


@app.route("/addVote/<_id>/<path:ballot>", methods=["GET"])
def add_vote(_id: str, ballot: str):
    logging.info(f"Received ballot: {ballot} for election with ID: {_id}")
    ballot = list(filter(bool, ballot.split("/")))
    ip_address = (
        request.headers.getlist("X-Forwarded-For")[0]
        if request.headers.getlist("X-Forwarded-For")
        else request.remote_addr
    )

    try:
        election = election_db.get_election_by_id(_id)
        logging.info(f"Fetched election with ID: {_id} for rendering")
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"Error in fetching election - {_id}: {e}: {stacktrace}")
        output = {
            "status": False,
            "message": f"Error occurred while fetching election with ID: {_id}",
            "error": str(e),
        }
        return jsonify(output), 400

    candidates = election["candidates"]
    if len(ballot) != len(set(ballot)) \
            or not all([c in candidates for c in ballot]):
        logging.warning(f"Invalid ballot for election - {_id} by {ip_address}")
        output = {
            "status": False,
            "message": f"Invalid ballot. Valid candidates are: {', '.join(candidates)}",
        }
        return jsonify(output), 400

    try:
        logging.info(f"Adding ballot for election - {_id} by {ip_address}")
        election_db.add_ballot_to_election(_id, ip_address, ballot)
        logging.info(f"Successfully added ballot for election - {_id} by {ip_address}")
        output = {
            "status": True,
            "message": "Ballot added successfully.",
        }
        response_code = 200
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"Error in adding ballot for election - {_id}: {e}: {stacktrace}")
        output = {
            "status": False,
            "message": f"Error occurred while adding ballot for election with ID: {_id}",
            "error": str(e),
        }
        response_code = 400

    return jsonify(output), response_code


@app.route("/removeVote/<_id>", methods=["GET"])
def remove_vote(_id: str):
    ip_address = (
        request.headers.getlist("X-Forwarded-For")[0]
        if request.headers.getlist("X-Forwarded-For")
        else request.remote_addr
    )
    logging.info(f"Received request to remove ballot for election - {_id} by {ip_address}")

    try:
        if election_db.check_election_id_exists(_id) is None:
            raise Exception(f"Election with ID: {_id} does not exist.")
        logging.info(f"Fetched election with ID: {_id} for removing ballot")
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"Error in fetching election - {_id}: {e}: {stacktrace}")
        output = {
            "status": False,
            "message": f"Error occurred while fetching election with ID: {_id}",
            "error": str(e),
        }
        return jsonify(output), 400

    try:
        logging.info(f"Removing ballot for election - {_id} by {ip_address}")
        election_db.remove_ballot_from_election(_id, ip_address)
        logging.info(f"Successfully removed ballot for election - {_id} by {ip_address}")
        output = {
            "status": True,
            "message": "Ballot removed successfully.",
        }
        response_code = 200
    except Exception as e:
        stacktrace = traceback.format_exc()
        logging.error(f"Error in removing ballot for election - {_id}: {e}: {stacktrace}")
        output = {
            "status": False,
            "message": f"Error occurred while removing ballot for election with ID: {_id}",
            "error": str(e),
        }
        response_code = 400

    return jsonify(output), response_code


if __name__ == "__main__":
    election_db = ElectionDatabase()
    helper = helper.APIHelper(election_db)
    app.run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 5000))
    )
