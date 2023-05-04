import pyrankvote
from pyrankvote import Candidate, Ballot

bush = Candidate("George W. Bush (Republican)")
gore = Candidate("Al Gore (Democratic)")
nader = Candidate("Ralph Nader (Green)")

candidates = [bush, gore, nader]

ballots = [
    Ballot(ranked_candidates=[bush, gore]),
    Ballot(ranked_candidates=[gore, bush]),
]

election_result = pyrankvote.instant_runoff_voting(candidates, ballots)

winners = election_result.get_winners()
print(winners)

print(election_result)
