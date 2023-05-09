import datetime
import logging
from typing import Any

import flask

from db import ElectionDatabase


class APIHelper:
    def __init__(self, election_db: ElectionDatabase):
        self.election_db = election_db

    @staticmethod
    def get_request_ip_address(request: flask.Request) -> str:
        return (
            request.headers.getlist("X-Forwarded-For")[0]
            if request.headers.getlist("X-Forwarded-For")
            else request.remote_addr
        )

    def verify_election_creation_data(self, election: dict[str, Any]):
        logging.info(f"Verifying election data: {election}")
        if (_id := election.get("_id")) is not None:
            if self.election_db.check_election_id_exists(_id):
                raise Exception("Election ID already exists. Please choose a different one or do not specify one.")

        if (end_time := election.get("end_time")) is not None:
            if end_time <= election["start_time"]:
                raise Exception("End time cannot be before start time")

        if election["voting_strategy"] == "instant_runoff" and election["number_of_winners"] != 1:
            raise Exception("Instant runoff voting strategy can only have 1 winner")

        candidates = election["candidates"]
        if len(candidates) != len(set(candidates)):
            raise Exception("Duplicate candidates are not allowed")
        if len(candidates) < 2:
            raise Exception("There must be at least 2 candidates")

        # TODO: Enable this condition
        # duplicate_election_check, duplicate_id = self.election_db.check_duplicate_election_is_running(
        #     election["creator"], candidates)
        # if duplicate_election_check:
        #     raise Exception(f"One or more similar elections created by you is already running: {duplicate_id}. "
        #                     f"Please wait for it to end.")

    def parse_election_creation_data_from_post_request(self, request: flask.Request) -> dict[str, Any]:
        logging.info(f"Received POST request: {request.json}")
        current_time = datetime.datetime.utcnow()
        election = dict()

        def initialise_nullable_fields_if_not_none(field: str):
            if (value := request.json.get(field, None)) is not None:
                if field == "end_time":
                    value = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                election[field] = value

        initialise_nullable_fields_if_not_none("_id")
        initialise_nullable_fields_if_not_none("name")

        election["creator"] = (
            request.headers.getlist("X-Forwarded-For")[0]
            if request.headers.getlist("X-Forwarded-For")
            else request.remote_addr
        )

        initialise_nullable_fields_if_not_none("description")
        election["start_time"] = request.json.get("start_time", current_time)
        initialise_nullable_fields_if_not_none("end_time")

        election["voting_strategy"] = request.json.get("voting_strategy", "instant_runoff")
        election["number_of_winners"] = request.json.get("number_of_winners", 1)

        election["anonymous"] = request.json.get("anonymous", False)
        election["update_ballot"] = request.json.get("update_ballot", True)
        election["candidates"] = request.json.get("candidates", [])

        self.verify_election_creation_data(election)
        return election

    def parse_election_creation_data_from_get_request(self, request: flask.Request) -> dict[str, Any]:
        logging.info(f"Received GET request: {request.view_args}")
        current_time = datetime.datetime.utcnow()
        election = dict()

        election["creator"] = (
            request.headers.getlist("X-Forwarded-For")[0]
            if request.headers.getlist("X-Forwarded-For")
            else request.remote_addr
        )

        election["start_time"] = current_time
        election["voting_strategy"] = "instant_runoff"
        election["number_of_winners"] = 1
        election["anonymous"] = False
        election["update_ballot"] = True
        election["candidates"] = request.view_args.get("candidates", None).split("/")

        self.verify_election_creation_data(election)
        return election

    def update_election_with_new_data(self, election: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
        logging.info(f"Updating election: {election['_id']} with new data: {data}")
        fields_requiring_election_result_reset = [
            "candidates",
            "voting_strategy",
            "number_of_winners"
        ]

        allowed_fields = [
            "name",
            "description",
            "start_time",
            "end_time",
            "anonymous",
            "update_ballot"
        ]
        allowed_fields += fields_requiring_election_result_reset

        reset_election_result = False
        for field in data:
            logging.info(f"Updating field: {field}")
            if field not in allowed_fields:
                raise Exception(f"Field {field} is not allowed to be updated or is invalid")
            else:
                if field in fields_requiring_election_result_reset:
                    reset_election_result = True
                election[field] = data[field]

        _id = election.pop("_id")
        self.verify_election_creation_data(election)
        election["_id"] = _id
        if reset_election_result:
            logging.info(f"Resetting election result for election: {_id}")
            election.pop("ballots", None)
            election.pop("winning_candidates", None)
            election.pop("number_of_rounds", None)
            election.pop("summary", None)
            self.election_db.reset_election_results(_id)

        return election
