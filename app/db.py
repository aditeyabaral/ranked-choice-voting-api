import os
import pytz
import json
import uuid
import logging
import datetime
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from election import get_election_results
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.ext.declarative import declarative_base


load_dotenv()
IST = pytz.timezone("Asia/Kolkata")


class ElectionDatabase:
    def __init__(self):
        DATABASE_URL = os.environ.get("APP_DATABASE_URL")
        self.base = declarative_base()
        self.engine = create_engine(DATABASE_URL)
        self.connection = self.engine.connect()
        self.metadata = MetaData()
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        logging.debug(f"Database connection established: {self}")
        self.setup_tables()

        self.election_table = Table(
            "election", self.metadata, autoload=True, autoload_with=self.engine
        )

    def setup_tables(self):
        with open("app/conf/setup_db.sql") as f:
            queries = f.read().strip().split("\n\n")
            for query in queries:
                try:
                    self.connection.execute(query)
                except Exception as e:
                    logging.error(f"Exception while executing query: {query}: {e}")

    def check_election_id_exists(self, election_id):
        query = self.election_table.select().where(
            self.election_table.c.election_id == election_id
        )
        result = self.connection.execute(query)
        return result.rowcount > 0

    def generate_election_id(self, election_db):
        while True:
            election_id = str(uuid.uuid1().hex[:5])
            if not self.check_election_id_exists(election_id):
                return election_id

    def add_election(
        self,
        election_id,
        created_at,
        created_by,
        election_name,
        start_time,
        end_time,
        description,
        anonymous,
        update_votes,
        allow_ties,
        candidates,
    ):
        candidates = list(map(str, candidates))
        candidates = json.dumps(candidates)
        query = self.election_table.insert().values(
            election_id=election_id,
            created_at=created_at,
            created_by=created_by,
            election_name=election_name,
            start_time=start_time,
            end_time=end_time,
            description=description,
            anonymous=anonymous,
            update_votes=update_votes,
            allow_ties=allow_ties,
            candidates=candidates,
        )
        self.connection.execute(query)

    def remove_election(self, election_id, ip_address):
        election_data = self.get_election_data(election_id)
        if election_data["created_by"] != ip_address:
            raise Exception("You are not authorized to remove this election.")
        query = self.election_table.delete().where(
            self.election_table.c.election_id == election_id
        )
        self.connection.execute(query)

    def get_election_data(self, election_id):
        query = self.election_table.select().where(
            self.election_table.c.election_id == election_id
        )
        result = self.connection.execute(query).fetchall()[0]
        (
            election_id,
            created_at,
            created_by,
            election_name,
            start_time,
            end_time,
            description,
            anonymous,
            update_votes,
            allow_ties,
            candidates,
            votes,
            round_number,
            winner,
        ) = result
        candidates = json.loads(candidates)
        votes = json.loads(votes) if votes is not None else votes
        created_at = datetime.datetime.strftime(created_at, "%Y-%m-%d %H:%M:%S")
        start_time = datetime.datetime.strftime(start_time, "%Y-%m-%d %H:%M:%S")
        end_time = str(end_time) if end_time is not None else end_time
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
            "allow_ties": allow_ties,
            "candidates": candidates,
            "votes": votes,
            "round_number": round_number,
            "winner": winner,
        }

    def get_election_votes(self, election_id):
        query = self.election_table.select().where(
            self.election_table.c.election_id == election_id
        )
        result = self.connection.execute(query).fetchall()[0]
        votes = json.loads(result[-3]) if result[-3] is not None else None
        return votes

    def get_election_candidates(self, election_id):
        query = self.election_table.select().where(
            self.election_table.c.election_id == election_id
        )
        result = self.connection.execute(query).fetchall()[0]
        candidates = json.loads(result[-4]) if result[-4] is not None else None
        return candidates

    def get_election_time(self, election_id):
        query = self.election_table.select().where(
            self.election_table.c.election_id == election_id
        )
        result = self.connection.execute(query).fetchall()[0]
        start_time, end_time = result[4], result[5]
        start_time = IST.localize(start_time)
        end_time = IST.localize(end_time) if end_time is not None else end_time
        return start_time, end_time

    def check_election_update_votes(self, election_id):
        query = self.election_table.select().where(
            self.election_table.c.election_id == election_id
        )
        result = self.connection.execute(query).fetchall()[0]
        update_votes = result[-6]
        return update_votes

    def check_election_allow_ties(self, election_id):
        query = self.election_table.select().where(
            self.election_table.c.election_id == election_id
        )
        result = self.connection.execute(query).fetchall()[0]
        allow_ties = result[-5]
        return allow_ties

    def add_vote(self, election_id, voter_ip, votes):
        current_time = datetime.datetime.now(IST)
        election_votes = self.get_election_votes(election_id)
        election_update_votes = self.check_election_update_votes(election_id)
        election_allow_ties = self.check_election_allow_ties(election_id)
        election_candidates = self.get_election_candidates(election_id)
        election_candidates_string = ", ".join(election_candidates)
        election_start_time, election_end_time = self.get_election_time(election_id)

        # check if election has not started
        if current_time < election_start_time:
            logging.error(
                f"Vote attempted before election start time: {current_time} < {election_start_time}"
            )
            raise Exception("Vote attempted before election start time")

        # check if election has ended
        if election_end_time is not None and current_time > election_end_time:
            logging.error(
                f"Vote attempted after election end time: {current_time} > {election_end_time}"
            )
            raise Exception("Vote attempted after election end time")

        # check if votes contain all candidates
        if set(election_candidates) != set(votes):
            logging.error(
                f"Votes contain invalid candidates. Valid candidates are: {election_candidates_string}"
            )
            raise Exception(
                f"Invalid candidates. Valid candidates are: {election_candidates_string}"
            )

        # check if voter has already voted to prevent voter from updating votes
        if (
            election_votes is not None
            and voter_ip in election_votes
            and not election_update_votes
        ):
            logging.error(
                f"Voter {voter_ip} has already voted. Votes cannot be updated."
            )
            raise Exception(
                f"Voter {voter_ip} has already voted. You cannot update your vote."
            )

        # add vote
        if election_votes is None:
            election_votes = {voter_ip: votes}
        else:
            election_votes[voter_ip] = votes
        logging.info(f"Adding vote for voter {voter_ip}")
        logging.debug(f"New Votes: {election_votes}")

        # update new votes in database
        query = (
            self.election_table.update()
            .where(self.election_table.c.election_id == election_id)
            .values(votes=json.dumps(election_votes))
        )
        self.connection.execute(query)

        # calculate new winner
        election_results = get_election_results(
            election_candidates, election_votes, election_allow_ties
        )
        logging.debug(f"Election Results: {election_results}")
        winner, round_number = election_results
        query = (
            self.election_table.update()
            .where(self.election_table.c.election_id == election_id)
            .values(winner=winner, round_number=round_number)
        )
        self.connection.execute(query)

    def remove_vote(self, election_id, voter_ip):
        current_time = datetime.datetime.now(IST)
        election_votes = self.get_election_votes(election_id)
        election_update_votes = self.check_election_update_votes(election_id)
        election_allow_ties = self.check_election_allow_ties(election_id)
        election_candidates = self.get_election_candidates(election_id)
        election_start_time, election_end_time = self.get_election_time(election_id)

        # check if votes can be removed
        if not election_update_votes:
            logging.error(
                f"Voter {voter_ip} cannot remove vote. Votes cannot be updated."
            )
            raise Exception("Votes cannot be removed. Updating votes is disabled.")

        # check if election has not started
        if current_time < election_start_time:
            logging.error(
                f"Vote removal attempted before election start time: {current_time} < {election_start_time}"
            )
            raise Exception("Vote removal attempted before election start time")

        # check if election has ended
        if election_end_time is not None and current_time > election_end_time:
            logging.error(
                f"Vote removal attempted after election end time: {current_time} > {election_end_time}"
            )
            raise Exception("Vote removal attempted after election end time")

        # check if voter has already voted -> cannot remove vote
        if election_votes is None or (
            election_votes is not None and voter_ip not in election_votes
        ):
            logging.error(f"Voter {voter_ip} has not voted")
            raise Exception(f"Voter {voter_ip} has not voted")

        # remove vote
        if election_votes is not None:
            del election_votes[voter_ip]
            if not election_votes:
                election_votes = None
            logging.info(f"Removing vote for voter {voter_ip}")
            logging.debug(f"New Votes: {election_votes}")

        # update new votes in database
        query = (
            self.election_table.update()
            .where(self.election_table.c.election_id == election_id)
            .values(votes=json.dumps(election_votes), round_number=None, winner=None)
        )
        self.connection.execute(query)

        # calculate new winner
        if election_votes is not None:
            election_results = get_election_results(
                election_candidates, election_votes, election_allow_ties
            )
            logging.debug(f"Election Results: {election_results}")
            winner, round_number = election_results
            query = (
                self.election_table.update()
                .where(self.election_table.c.election_id == election_id)
                .values(winner=winner, round_number=round_number)
            )
            self.connection.execute(query)
