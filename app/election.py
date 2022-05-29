import logging


def get_election_results(candidates, votes, majority_threshold=None, round=1):
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

    # check if all values are equal
    if len(set(first_choice_frequencies.values())) == 1:
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
    return get_election_results(candidates, votes, majority_threshold, round+1)
