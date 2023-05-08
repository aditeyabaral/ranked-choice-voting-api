import datetime
import logging
import os
from typing import Any, Mapping, Optional

import pymongo
from bson.objectid import ObjectId

from election import get_election_result


# TODO: Add return type hints to functions


class ElectionDatabase:
    def __init__(self):
        self.client = pymongo.MongoClient(os.environ["MONGO_URI"])
        self.db = self.client["ranked_choice_voting"]
        self.election = self.db["election"]

    def get_election_by_id(self, _id: str) -> Mapping[str, Any]:
        if ObjectId.is_valid(_id):
            _id = ObjectId(_id)
        election = self.election.find_one({"_id": _id})
        if election is None:
            raise Exception("This election does not exist")
        else:
            return election

    def check_election_id_exists(self, _id: str) -> bool:
        if ObjectId.is_valid(_id):
            _id = ObjectId(_id)
        return self.election.find_one({"_id": _id}) is not None

    def add_election(self, election: dict[str, Any]) -> str:
        result = self.election.insert_one(election)
        return result.inserted_id

    def remove_election(self, _id: str):
        if ObjectId.is_valid(_id):
            _id = ObjectId(_id)
        self.election.delete_one({"_id": _id})

    def check_duplicate_election_is_running(self, creator: str, candidates: list[str]) -> tuple[bool, Optional[str]]:
        elections_with_same_candidates_by_creator = (
            list(self.election.find({"creator": creator, "candidates": candidates})))
        if len(elections_with_same_candidates_by_creator) == 0:
            return False, None
        else:
            _ids = [str(election["_id"]) for election in elections_with_same_candidates_by_creator]
            _ids = ", ".join(_ids)
            return True, _ids

    def get_election_ballots(self, _id: str) -> Optional[dict[str, list[str]]]:
        election = self.get_election_by_id(_id)
        return election.get("ballots", None)

    def get_election_candidates(self, _id: str) -> Optional[list[str]]:
        election = self.get_election_by_id(_id)
        return election.get("candidates", None)

    def get_election_start_and_end_time(self, _id: str) -> Optional[
        tuple[datetime.datetime, datetime.datetime]]:
        election = self.get_election_by_id(_id)
        return election["start_time"], election.get("end_time", None)

    def check_election_ballots_can_be_updated(self, _id: str) -> bool:
        election = self.get_election_by_id(_id)
        return election["update_ballots"]

    def check_election_allows_ties(self, _id: str) -> bool:
        election = self.get_election_by_id(_id)
        return election["allow_ties"]

    def add_ballot_to_election(self, _id: str, ip_address: str, ballot: list[str]):
        if ObjectId.is_valid(_id):
            _id = ObjectId(_id)
        current_time = datetime.datetime.utcnow()
        election = self.get_election_by_id(_id)
        ballots = election.get("ballots", None)
        update_ballot = election["update_ballot"]
        candidates = election["candidates"]
        start_time = election["start_time"]
        end_time = election.get("end_time", None)
        voting_strategy = election["voting_strategy"]
        number_of_winners = election["number_of_winners"]

        # check if the election has not started
        if current_time < start_time:
            logging.error(
                f"Ballot attempted before election start time by {ip_address}: {current_time} < {start_time}")
            raise Exception("Ballot casting attempted before election start time")

        # check if the election has ended
        if end_time is not None and current_time > end_time:
            logging.error(
                f"Ballot attempted after election end time by {ip_address}: {current_time} > {end_time}")
            raise Exception("Ballot attempted after election end time")

        # check if voter has already voted and election ballots cannot be updated
        if ballots is not None and ip_address in ballots and not update_ballot:
            logging.error(f"Voter {ip_address} has already voted and election ballots cannot be updated")
            raise Exception("Voter has already voted and election ballots cannot be updated")

        # add ballots to election
        if ballots is None:
            ballots = {}
        ballots[ip_address] = ballot
        logging.info(f"Ballot added to election {_id} by {ip_address}")

        # update ballots in database
        self.election.update_one({"_id": _id}, {"$set": {"ballots": ballots}})
        logging.info(f"Ballot added to database for election {_id} by {ip_address}")

        # calculate new winner
        winning_candidates, number_of_rounds, election_result_string = get_election_result(
            candidates,
            list(ballots.values()),
            voting_strategy,
            number_of_winners
        )
        logging.info(f"Calculated election results for election {_id} by {ip_address}")
        self.election.update_one({"_id": _id}, {"$set": {
            "winning_candidates": winning_candidates,
            "number_of_rounds": number_of_rounds,
            "summary": election_result_string
        }})
        logging.info(
            f"Updated election results in database for election {_id} due to ballot addition by {ip_address}")

    def remove_ballot_from_election(self, _id: str, ip_address: str):
        if ObjectId.is_valid(_id):
            _id = ObjectId(_id)
        current_time = datetime.datetime.utcnow()
        election = self.get_election_by_id(_id)
        ballots = election.get("ballots", None)
        update_ballot = election["update_ballot"]
        candidates = election["candidates"]
        start_time = election["start_time"]
        end_time = election.get("end_time", None)
        voting_strategy = election["voting_strategy"]
        number_of_winners = election["number_of_winners"]

        # check if ballots can be removed
        if not update_ballot:
            logging.error(f"Ballots cannot be removed from election {_id} by {ip_address}")
            raise Exception("Ballots cannot be removed from election")

        # check if the election has not started
        if current_time < start_time:
            logging.error(
                f"Ballot removal attempted before election start time by {ip_address}: {current_time} < {start_time}")
            raise Exception("Ballot removal attempted before election start time")

        # check if the election has ended
        if end_time is not None and current_time > end_time:
            logging.error(
                f"Ballot removal attempted after election end time by {ip_address}: {current_time} > {end_time}")
            raise Exception("Ballot removal attempted after election end time")

        # check if voter has not voted
        if ballots is None or (ballots is not None and ip_address not in ballots):
            logging.error(f"Voter {ip_address} has not voted")
            raise Exception("Voter has not voted")

        # remove ballots from election
        del ballots[ip_address]
        if not ballots:
            ballots = None
        logging.info(f"Ballot removed from election {_id} by {ip_address}")

        # update ballots in database
        self.election.update_one({"_id": _id}, {"$set": {"ballots": ballots}})
        logging.info(f"Ballot removed from database for election {_id} by {ip_address}")

        # calculate new winner
        if ballots is not None:
            winning_candidates, number_of_rounds, election_result_string = get_election_result(
                candidates,
                list(ballots.values()),
                voting_strategy,
                number_of_winners
            )
            logging.info(f"Calculated election results for election {_id} by {ip_address}")
            self.election.update_one({"_id": _id}, {"$set": {
                "winning_candidates": winning_candidates,
                "number_of_rounds": number_of_rounds,
                "summary": election_result_string
            }})
        else:
            # remove unnecessary fields
            self.election.update_one({"_id": _id}, {"$unset": {
                "winning_candidates": "",
                "number_of_rounds": "",
                "summary": ""
            }})

        logging.info(f"Updated election results in database for election {_id} due to ballot removal by {ip_address}")

    def update_election_details(self, election: dict[str, Any]):
        _id = election["_id"]
        if ObjectId.is_valid(_id):
            _id = ObjectId(_id)
        self.election.update_one({"_id": _id}, {"$set": election})
        logging.info(f"Updated election details in database for election {_id}")
