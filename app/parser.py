import pytz
import datetime
import logging
from flask import request
from db import ElectionDatabase

IST = pytz.timezone("Asia/Kolkata")


# TODO: Verify all possible details including data types
def verify_election_creation_parameters(election_data):
    assert (len(election_data["candidates"])) == len(set(election_data["candidates"])), "Duplicate candidates found"
    assert election_data["voting_strategy"] in \
           [
               "instant-runoff",
               "preferential-block",
               "single-transferable"
           ], "Invalid voting strategy"
    assert (1 <= election_data["num_winners"] < len(election_data["candidates"])), "Invalid number of winners"
    assert (election_data["start_time"] < election_data["end_time"]), "Start time must be before end time"


def get_election_data_post():
    logging.debug(f"Request data: {request.json}")

    election_id = request.json.get("election_id")
    created_at = datetime.datetime.now(IST)
    created_by = (
        request.headers.getlist("X-Forwarded-For")[0]
        if request.headers.getlist("X-Forwarded-For")
        else request.remote_addr
    )
    election_name = request.json.get("election_name", None)
    start_time = request.json.get("start_time", created_at)
    end_time = request.json.get("end_time", start_time + datetime.timedelta(days=7))
    description = request.json.get("description", None)
    anonymous = request.json.get("anonymous", False)
    update_votes = request.json.get("update_votes", True)
    voting_strategy = request.json.get("voting_strategy", "instant-runoff")
    num_winners = request.json.get("num_winners", 1)
    candidates = request.json.get("candidates", None)

    return {
        "election_id": election_id,
        "created_at": created_at,
        "created_by": created_by,
        "election_name": election_name,
        "start_time": start_time,
        "end_time": end_time,
        "description": description,
        "anonymous": anonymous,
        "update_votes": update_votes,
        "voting_strategy": voting_strategy,
        "num_winners": num_winners,
        "candidates": candidates,
    }


def get_election_data_get():
    logging.debug(f"Request data: {request.args}")

    election_id = None
    created_at = datetime.datetime.now(IST)
    created_by = (
        request.headers.getlist("X-Forwarded-For")[0]
        if request.headers.getlist("X-Forwarded-For")
        else request.remote_addr
    )
    election_name = None
    start_time = created_at
    end_time = start_time + datetime.timedelta(days=7)
    description = None
    anonymous = False
    update_votes = True
    voting_strategy = "instant-runoff"
    num_winners = 1
    candidates = request.view_args.get("candidates", None).split("/")

    return {
        "election_id": election_id,
        "created_at": created_at,
        "created_by": created_by,
        "election_name": election_name,
        "start_time": start_time,
        "end_time": end_time,
        "description": description,
        "anonymous": anonymous,
        "update_votes": update_votes,
        "voting_strategy": voting_strategy,
        "num_winners": num_winners,
        "candidates": candidates,
    }


def update_election_with_new_data(new_election_data, election_db: ElectionDatabase):
    election_id = new_election_data["election_id"]
    created_by = (
        request.headers.getlist("X-Forwarded-For")[0]
        if request.headers.getlist("X-Forwarded-For")
        else request.remote_addr
    )
    current_election_data = election_db.get_election_data_by_id_and_creator(
        election_id, created_by
    )
    for key in new_election_data:
        if key in current_election_data:
            if key == "candidates":
                if set(current_election_data["candidates"]) != set(
                        new_election_data["candidates"]
                ):
                    current_election_data["votes"] = None
                    current_election_data["round_number"] = None
                    current_election_data["winner"] = None
                    current_election_data["candidates"] = new_election_data[
                        "candidates"
                    ]
                    logging.warning(
                        "Candidates changed. Resetting votes, round_number, winner"
                    )
            elif key in [
                "election_id",
                "created_at",
                "created_by",
                "votes",
                "round_number",
                "winner",
            ]:
                logging.warning(
                    f"Attempt to update {key} not allowed for election {election_id}"
                )
                continue
            else:
                current_election_data[key] = new_election_data[key]

    start_time = current_election_data["start_time"]
    try:
        start_time = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    except:
        start_time = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S.%f")

    end_time = current_election_data["end_time"]
    try:
        end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    except:
        end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S.%f")

    if start_time >= end_time:
        end_time = start_time + datetime.timedelta(days=7)

    current_election_data["end_time"] = end_time
    current_election_data["start_time"] = start_time

    election_db.update_election_details(current_election_data)
    logging.debug(f"Updated election {election_id} with new data")
    return current_election_data
