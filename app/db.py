import datetime
import logging
import os
from typing import Any, Mapping, Optional

import pymongo
import pytz
from bson.objectid import ObjectId

from election import get_election_result

IST = pytz.timezone("Asia/Kolkata")


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

    def get_election_data_by_creator(self, creator: str) -> list[Mapping[str, Any]]:
        return list(self.election.find({"creator": creator}))

    def get_election_by_id_and_creator(self, _id: str, creator: str) -> Mapping[str, Any]:
        if ObjectId.is_valid(_id):
            _id = ObjectId(_id)
        election = self.election.find_one({"_id": _id, "creator": creator})
        if election is None:
            raise Exception("This election does not exist")
        else:
            return election

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

    def get_election_votes(self, _id: str) -> Optional[dict[str, list[str]]]:
        election = self.get_election_by_id(_id)
        return election.get("votes", None)

    def get_election_candidates(self, _id: str) -> Optional[list[str]]:
        election = self.get_election_by_id(_id)
        return election.get("candidates", None)

    def get_election_start_and_end_time(self, _id: str) -> Optional[
        tuple[datetime.datetime, datetime.datetime]]:
        election = self.get_election_by_id(_id)
        return election["start_time"], election.get("end_time", None)

    def check_election_votes_can_be_updated(self, _id: str) -> bool:
        election = self.get_election_by_id(_id)
        return election["update_votes"]

    def check_election_allows_ties(self, _id: str) -> bool:
        election = self.get_election_by_id(_id)
        return election["allow_ties"]

    def add_vote_to_election(self, _id: str, voter_ip_address: str, votes: list[str]):
        current_time = datetime.datetime.now(IST)
        election = self.get_election_by_id(_id)

        election_votes = election.get("votes", None)
        election_can_update_votes = election["update_votes"]
        election_allow_ties = election["allow_ties"]
        election_candidates = election["candidates"]
        election_candidates_string = ", ".join(election_candidates)
        election_start_time = election["start_time"]
        election_end_time = election.get("end_time", None)

        # check if the election has not started
        if current_time < election_start_time:
            logging.error(
                f"Vote attempted before election start time by {voter_ip_address}: {current_time} < {election_start_time}")
            raise Exception("Vote attempted before election start time")

        # check if the election has ended
        if election_end_time is not None and current_time > election_end_time:
            logging.error(
                f"Vote attempted after election end time by {voter_ip_address}: {current_time} > {election_end_time}")
            raise Exception("Vote attempted after election end time")

        # check if votes contain all candidates
        if set(votes) != set(election_candidates):
            logging.error(
                f"Votes by {voter_ip_address} contain invalid candidates. Valid candidates are: {election_candidates_string}")
            raise Exception(f"Invalid candidates. Valid candidates are: {election_candidates_string}")

        # check if voter has already voted and election votes cannot be updated
        if election_votes is not None and voter_ip_address in election_votes and not election_can_update_votes:
            logging.error(f"Voter {voter_ip_address} has already voted and election votes cannot be updated")
            raise Exception("Voter has already voted and election votes cannot be updated")

        # add votes to election
        if election_votes is None:
            election_votes = {}
        election_votes[voter_ip_address] = votes
        logging.info(f"Vote added to election {_id} by {voter_ip_address}")

        # update votes in database
        self.election.update_one({"_id": {"$in": [_id, ObjectId(_id)]}}, {"$set": {"votes": election_votes}})
        logging.info(f"Vote added to database for election {_id} by {voter_ip_address}")

        # calculate new winner
        # TODO - fix this
        election_results = get_election_result(election_candidates, election_votes, election_allow_ties)
        logging.info(f"Calculated election results for election {_id} by {voter_ip_address}")
        election_winner, round_number = election_results
        self.election.update_one({"_id": {"$in": [_id, ObjectId(_id)]}},
                                 {"$set": {"winner": election_winner, "round_number": round_number}})
        logging.info(
            f"Updated election results in database for election {_id} due to vote addition by {voter_ip_address}")

    def remove_vote_from_election(self, _id: str, voter_ip_address: str):
        current_time = datetime.datetime.now(IST)
        election = self.get_election_by_id(_id)

        election_votes = election.get("votes", None)
        election_can_update_votes = election["update_votes"]
        election_allow_ties = election["allow_ties"]
        election_candidates = election["candidates"]
        election_candidates_string = ", ".join(election_candidates)
        election_start_time = election["start_time"]
        election_end_time = election.get("end_time", None)

        # check if votes can be removed
        if not election_can_update_votes:
            logging.error(f"Votes cannot be removed from election {_id} by {voter_ip_address}")
            raise Exception("Votes cannot be removed from election")

        # check if the election has not started
        if current_time < election_start_time:
            logging.error(
                f"Vote removal attempted before election start time by {voter_ip_address}: {current_time} < {election_start_time}")
            raise Exception("Vote removal attempted before election start time")

        # check if the election has ended
        if election_end_time is not None and current_time > election_end_time:
            logging.error(
                f"Vote removal attempted after election end time by {voter_ip_address}: {current_time} > {election_end_time}")
            raise Exception("Vote removal attempted after election end time")

        # check if voter has not voted
        if election_votes is None or (election_votes is not None and voter_ip_address not in election_votes):
            logging.error(f"Voter {voter_ip_address} has not voted")
            raise Exception("Voter has not voted")

        # remove votes from election
        del election_votes[voter_ip_address]
        if not election_votes:
            election_votes = None
        logging.info(f"Vote removed from election {_id} by {voter_ip_address}")

        # update votes in database
        self.election.update_one({"_id": {"$in": [_id, ObjectId(_id)]}}, {"$set": {"votes": election_votes}})
        logging.info(f"Vote removed from database for election {_id} by {voter_ip_address}")

        # calculate new winner
        # TODO - fix this
        election_results = get_election_result(election_candidates, election_votes, election_allow_ties)
        logging.info(f"Calculated election results for election {_id} by {voter_ip_address}")
        election_winner, round_number = election_results
        self.election.update_one({"_id": {"$in": [_id, ObjectId(_id)]}},
                                 {"$set": {"winner": election_winner, "round_number": round_number}})
        logging.info(
            f"Updated election results in database for election {_id} due to vote removal by {voter_ip_address}")

    def update_election_details(self, election: dict[str, Any]):
        _id = election["_id"]
        if ObjectId.is_valid(_id):
            _id = ObjectId(_id)
        self.election.update_one({"_id": _id}, {"$set": election})
        logging.info(f"Updated election details in database for election {_id}")
