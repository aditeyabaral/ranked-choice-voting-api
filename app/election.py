import logging
from typing import Literal

import pyrankvote
from pyrankvote import Candidate, Ballot


def get_ballot_from_candidate_list_string(candidate_list: list[str]) -> Ballot:
    candidate_list = [Candidate(candidate) if isinstance(candidate, str) else candidate for candidate in candidate_list]
    return Ballot(ranked_candidates=candidate_list)


def compute_ranked_voting_result(
        candidates: list[Candidate],
        ballots: list[Ballot],
        voting_strategy: Literal["instant-runoff", "preferential-block", "single-transferable"] = "instant-runoff",
        num_winners: int = 1,
) -> tuple[str, int, str]:
    logging.info(f"Obtaining election results for candidates: {candidates} and ballots: {ballots} "
                 f"using voting strategy: {voting_strategy}")

    if voting_strategy == "instant-runoff":
        election_result = pyrankvote.instant_runoff_voting(candidates, ballots)
    else:
        if voting_strategy == "preferential-block":
            _function = pyrankvote.preferential_block_voting
        elif voting_strategy == "single-transferable":
            _function = pyrankvote.single_transferable_vote
        else:
            raise NotImplementedError(f"Voting strategy {voting_strategy} not implemented")
        election_result = _function(candidates, ballots, num_winners)

    num_rounds = len(election_result.rounds)
    winners = ', '.join(list(map(lambda x: x.name, election_result.get_winners())))
    election_round_details = str(election_result)
    return election_round_details, num_rounds, winners
