import datetime
import logging
import os
from typing import Any, Mapping, Optional

import pymongo
import pytz

from election import get_election_result

IST = pytz.timezone("Asia/Kolkata")


class ElectionDatabase:
    def __init__(self):
        self.client = pymongo.MongoClient(os.environ["MONGO_URI"])
        self.db = self.client["ranked_choice_voting"]
        self.election = self.db["election"]

    def check_election_id_exists(self, election_id: str) -> bool:
        return self.election.find_one({"_id": election_id}) is not None

    def generate_election_id(self) -> str:
        # TODO - is this required?
        return "test"

    def get_election_data_by_id(self, election_id: str) -> Mapping[str, Any]:
        election = self.election.find_one({"_id": election_id})
        if election is None:
            raise Exception("This election does not exist")
        else:
            return election

    def get_election_data_by_creator(self, created_by: str) -> list[Mapping[str, Any]]:
        return list(self.election.find({"created_by": created_by}))

    def get_election__by_id_and_creator(self, election_id: str, created_by: str) -> Mapping[str, Any]:
        election = self.election.find_one({"_id": election_id, "created_by": created_by})
        if election is None:
            raise Exception("This election does not exist")
        else:
            return election

    def add_election(self, election_data: dict[str, Any]):
        self.election.insert_one(election_data)

    def remove_election(self, election_id: str, ip_address: str):
        election = self.election.find_one({"_id": election_id})
        if election is None:
            raise Exception("This election does not exist")
        else:
            if election["ip_address"] != ip_address:
                raise Exception("You are not authorized to delete this election")
            else:
                self.election.delete_one({"_id": election_id, "ip_address": ip_address})

    def check_duplicate_election_is_running(self, created_by: str, candidates):
        elections_by_creator = list(self.election.find({"created_by": created_by}))
        duplicate_found, duplicate_election_id, duplicate_election_end_time = False, None, None
        for election in elections_by_creator:
            if election["candidates"] == candidates:
                duplicate_found = True
                duplicate_election_id = election["_id"]
                duplicate_election_end_time = election["end_time"]
                break
        if duplicate_found and duplicate_election_end_time > datetime.datetime.now(IST):
            return True, duplicate_election_id
        else:
            return False, None

    def get_election_votes(self, election_id: str) -> Optional[dict[str, list[str]]]:
        election = self.election.find_one({"_id": election_id})
        if election is None:
            raise Exception("This election does not exist")
        else:
            return election.get("votes", None)

    def get_election_candidates(self, election_id: str) -> Optional[list[str]]:
        election = self.election.find_one({"_id": election_id})
        if election is None:
            raise Exception("This election does not exist")
        else:
            return election["candidates"]

    def get_election_start_and_end_time(self, election_id: str) -> Optional[
        tuple[datetime.datetime, datetime.datetime]]:
        election = self.election.find_one({"_id": election_id})
        if election is None:
            raise Exception("This election does not exist")
        else:
            return election["start_time"], election.get("end_time", None)

    def check_election_votes_can_be_updated(self, election_id: str) -> bool:
        election = self.election.find_one({"_id": election_id})
        if election is None:
            raise Exception("This election does not exist")
        else:
            return election["update_votes"]

    def check_election_allows_ties(self, election_id: str) -> bool:
        election = self.election.find_one({"_id": election_id})
        if election is None:
            raise Exception("This election does not exist")
        else:
            return election["allow_ties"]

    def add_vote_to_election(self, election_id: str, voter_ip_address: str, votes: list[str]):
        current_time = datetime.datetime.now(IST)
        election = self.election.find_one({"_id": election_id})
        if election is None:
            raise Exception("This election does not exist")

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
        logging.info(f"Vote added to election {election_id} by {voter_ip_address}")

        # update votes in database
        self.election.update_one({"_id": election_id}, {"$set": {"votes": election_votes}})
        logging.info(f"Vote added to database for election {election_id} by {voter_ip_address}")

        # calculate new winner
        # TODO - fix this
        election_results = get_election_result(election_candidates, election_votes, election_allow_ties)
        logging.info(f"Calculated election results for election {election_id} by {voter_ip_address}")
        election_winner, round_number = election_results
        self.election.update_one({"_id": election_id},
                                 {"$set": {"winner": election_winner, "round_number": round_number}})
        logging.info(
            f"Updated election results in database for election {election_id} due to vote addition by {voter_ip_address}")

    def remove_vote_from_election(self, election_id: str, voter_ip_address: str):
        current_time = datetime.datetime.now(IST)
        election = self.election.find_one({"_id": election_id})
        if election is None:
            raise Exception("This election does not exist")

        election_votes = election.get("votes", None)
        election_can_update_votes = election["update_votes"]
        election_allow_ties = election["allow_ties"]
        election_candidates = election["candidates"]
        election_candidates_string = ", ".join(election_candidates)
        election_start_time = election["start_time"]
        election_end_time = election.get("end_time", None)

        # check if votes can be removed
        if not election_can_update_votes:
            logging.error(f"Votes cannot be removed from election {election_id} by {voter_ip_address}")
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
        logging.info(f"Vote removed from election {election_id} by {voter_ip_address}")

        # update votes in database
        self.election.update_one({"_id": election_id}, {"$set": {"votes": election_votes}})
        logging.info(f"Vote removed from database for election {election_id} by {voter_ip_address}")

        # calculate new winner
        # TODO - fix this
        election_results = get_election_result(election_candidates, election_votes, election_allow_ties)
        logging.info(f"Calculated election results for election {election_id} by {voter_ip_address}")
        election_winner, round_number = election_results
        self.election.update_one({"_id": election_id},
                                 {"$set": {"winner": election_winner, "round_number": round_number}})
        logging.info(
            f"Updated election results in database for election {election_id} due to vote removal by {voter_ip_address}")

    def update_election_details(self, election: dict[str, Any]):
        election_id = election["_id"]
        self.election.update_one({"_id": election_id}, {"$set": election})
        logging.info(f"Updated election details in database for election {election_id}")
