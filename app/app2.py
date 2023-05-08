import logging
import os
import traceback
from typing import Any
from urllib.parse import urlparse

import gh_md_to_html
import pytz
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
IST = pytz.timezone("Asia/Kolkata")


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


@app.route("/add", methods=["POST"])
@app.route("/add/<path:candidates>", methods=["GET"])
def create_election(**candidates):
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


@app.route("/remove/<_id>", methods=["GET"])
def remove_election(_id):
    ip_address = (
        request.headers.getlist("X-Forwarded-For")[0]
        if request.headers.getlist("X-Forwarded-For")
        else request.remote_addr
    )

    try:
        election: dict[str, Any] = election_db.get_election_by_id(_id)
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


if __name__ == "__main__":
    election_db = ElectionDatabase()
    helper = helper.APIHelper(election_db)
    app.run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", 5000))
    )
