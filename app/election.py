from typing import Union

import pyrankvote
from pyrankvote import Candidate, Ballot
from pyrankvote.helpers import ElectionResults


def format_candidates_and_ballots_for_voting(candidates: list[str], ballots: list[list[str]]) -> \
        tuple[list[Candidate], list[Ballot]]:
    candidates = list(map(lambda x: Candidate(x), candidates))
    if isinstance(ballots[0], list):
        ballots = list(map(lambda x: Ballot(ranked_candidates=x), ballots))
    return candidates, ballots


def get_election_result(
        candidates: list[Union[str, Candidate]],
        ballots: list[Union[list[str], Ballot]],
        voting_strategy: str = "instant_runoff",
        number_of_winners: int = 1
):
    candidates, ballots = format_candidates_and_ballots_for_voting(candidates, ballots)
    voting_strategies = {
        "instant_runoff": pyrankvote.instant_runoff_voting,
        "preferential_block": pyrankvote.preferential_block_voting,
        "single_transferable": pyrankvote.single_transferable_vote,
    }
    voting_strategy_function = voting_strategies.get(voting_strategy, None)
    if voting_strategy is None:
        raise ValueError(f"Invalid voting strategy: {voting_strategy}")

    if voting_strategy == "single_transferable":
        election_result: ElectionResults = voting_strategy_function(candidates, ballots)
    else:
        election_result: ElectionResults = voting_strategy_function(
            candidates,
            ballots,
            number_of_seats=number_of_winners
        )

    winning_candidates = list(map(lambda x: x.name, election_result.get_winners()))
    if len(winning_candidates) == 1:
        return winning_candidates[0]
    number_of_rounds = election_result.rounds
    election_result_string = str(election_result)
    return winning_candidates, number_of_rounds, election_result_string
