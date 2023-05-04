import copy
import logging
import pyrankvote
from pyrankvote import Candidate, Ballot


def get_election_result(candidates, ballots, voting_strategy="instant_runoff"):
    if voting_strategy == "instant_runoff":
        _function = pyrankvote.instant_runoff_voting
    elif voting_strategy == "borda_count":
        _function = pyrankvote.


def resolve_tiebreaker(candidates, votes):
    logging.debug("Resolving tiebreaker")
    num_candidates = len(candidates)
    candidate_scores = dict()

    # Finding candidates Borda Count
    for voter in votes:
        for idx, candidate in enumerate(votes[voter]):
            if candidate not in candidate_scores:
                candidate_scores[candidate] = 0
            candidate_scores[candidate] += num_candidates - idx + 1
    logging.debug(f"Candidate scores: {candidate_scores}")

    # Finding max candidate score
    max_candidate_score = max(candidate_scores.values())
    logging.debug(f"Max candidate score: {max_candidate_score}")

    # Return candidate with max score (if tied again, return first candidate)
    max_score_candidates = [
        candidate
        for candidate in candidate_scores
        if candidate_scores[candidate] == max_candidate_score
    ]
    return max_score_candidates[0]


def ranked_choice_voting(candidates, votes, majority_threshold=None, round=1):
    votes = copy.deepcopy(votes)
    candidates = copy.deepcopy(candidates)
    logging.debug(f"Round: {round}")

    # Calculating majority threshold
    num_voters = len(votes)
    if majority_threshold is None:
        majority_threshold = num_voters // 2 + 1
    elif majority_threshold < 0:
        majority_threshold = int(majority_threshold * num_voters) + 1

    # set frequency of first ranked votes to 0
    first_choice_frequencies = dict()
    for candidate in candidates:
        first_choice_frequencies[candidate] = 0

    # count first ranked votes
    for voter in votes:
        if votes[voter]:
            first_choice_frequencies[votes[voter][0]] += 1
    logging.debug(f"First choice frequencies: {first_choice_frequencies}")

    # check if candidates have same number of votes
    if (
        len(set(first_choice_frequencies.values())) == 1
        and len(first_choice_frequencies) > 1
    ):
        logging.debug("Tiebreaker needed")
        return "tied", round

    # check if any value is equal to majority_threshold, return that candidate
    for candidate in first_choice_frequencies:
        if first_choice_frequencies[candidate] >= majority_threshold:
            logging.debug(f"Winner is {candidate}")
            return candidate, round

    # if no candidate has majority, find the candidate with least votes
    least_pair = min(first_choice_frequencies.items(), key=lambda x: x[1])
    least_votes_candidate, least_votes = least_pair
    logging.debug(f"Eliminating {least_votes_candidate} with {least_votes}")

    # remove least_votes_candidate from candidates
    candidates.remove(least_votes_candidate)
    # remove least_votes_candidate from votes
    for voter in votes:
        if least_votes_candidate in votes[voter]:
            votes[voter].remove(least_votes_candidate)
    logging.debug(f"New candidates for next round: {candidates}")
    logging.debug(f"New votes for next round: {votes}")

    # recurse
    return ranked_choice_voting(candidates, votes, majority_threshold, round + 1)


def get_election_results(candidates, votes, allow_ties=False):
    winner, round = ranked_choice_voting(candidates, votes)
    if not allow_ties and winner == "tied":
        winner = resolve_tiebreaker(candidates, votes)
    return winner, round
