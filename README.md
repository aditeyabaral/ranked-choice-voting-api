# ranked-choice-voting-api

A simple API
for [ranked-choice voting](https://www.rankedvote.co/guides/understanding-ranked-choice-voting/how-does-ranked-choice-voting-work)
in an election.

Ranked-choice Voting is a Flask app that serves API endpoints for ranked-choice voting, supporting features such as
election creation, deletion and updating, vote casting, and result viewing. It supports election voting
strategies for electing both a single winner and multiple winners.

# Choosing a Voting Strategy

The following voting strategies are supported by this API:

- [Instant Run-off Voting (IRV)](https://en.wikipedia.org/wiki/Instant-runoff_voting): A single candidate election
  method that elects the candidate that can obtain majority
  support (more than 50%). Voters rank candidates and are granted one vote. The candidate with the fewest votes is
  removed and this candidate's votes are transferred according to the voters 2nd preference (or 3rd etc).

- [Preferential Block Voting (PBV)](https://en.wikipedia.org/wiki/Preferential_block_voting): A multiple candidate
  election method that elects candidates that can obtain majority support (more than 50%). PBV tends to elect
  uncontroversial candidates that agree with each other. Minority group often lose their representation.

- [Single Transferable Vote (STV)](https://en.wikipedia.org/wiki/Single_transferable_vote): A multiple candidate
  election method that elects candidates based on proportional representation. Minority (and extreme) groups get
  representation if they have enough votes to elect a candidate. STV is therefore the preferred ranked-choice voting
  method for parliament elections and most multiple seat elections, but it's more complex than PBV.

Preferential block voting and Single transferable vote are the same as Instant-runoff voting when *only one candidate
is elected*.

Instant-runoff voting and Preferential block voting are basically the same as exhaustive ballot, the preferred method in
Rober's rules of order. The only difference is that in exhaustive ballot voters can adjust their preferences between
each round (elimination or election of one candidate).

More details about each of these voting strategies can be found [here](https://github.com/jontingvold/pyrankvote).

# How to use ranked-choice-voting-api

## Create an Election

The creation of elections is performed by sending either a `GET` or `POST` request.

### ```GET```

A `GET` request is the quickest way to set up a ranked-choice election but offers no customization options since all
fields take their default values. Create an election by appending a `/` separated list of candidates to
the `/addElection` endpoint.

```bash
curl --location --request GET 'https://localhost:5000/addElection/pancakes/waffles/ice-cream'
```

### ```POST```

You can also create an election by sending a `POST` request. This is the most flexible way to create an election but
requires you to specify the fields you wish to customize.

The request body is a JSON object with the following fields:

| Field               | Optional | Default             | Description                                                                                                                   |
|---------------------|----------|---------------------|-------------------------------------------------------------------------------------------------------------------------------|
| `_id`               | Yes      | Random              | A custom ID for your election                                                                                                 |
| `name`              | Yes      |                     | The name of your election                                                                                                     |
| `description`       | Yes      |                     | A short description of your election                                                                                          |
| `start_time`        | Yes      | Current time in UTC | The timestamp at which your election starts. Ballots cast only after the start time will be counted                           |
| `end_time`          | Yes      |                     | The timestamp at which your election ends. Ballots cast only before the end time will be counted.                             |
| `voting_strategy`   | Yes      | `instant_runoff`    | A string indicating the voting strategy to use. Can be one of `instant_runoff`, `preferential_block` or `single_transferable` |
| `number_of_winners` | Yes      | `1`                 | An integer indicating the required number of winning candidates for your election                                             |
| `update_ballot`     | Yes      | `True`              | A boolean value indicating whether a voter can update or delete their ballot                                                  |
| `anonymous`         | Yes      | `False`             | A boolean value indicating whether ballots cast in your election are publicly viewable                                        |
| `candidates`        | **No**   |                     | A list of unique strings where each element represents a candidate                                                            |

An example is provided below:

```bash
curl --location --request POST 'https://localhost:5000/addElection' \
--header 'Content-Type: application/json' \
--data-raw '{
    "name": "Food ranking",
    "description": "Rank your favorite foods!",
    "candidates": ["pancakes", "ice-cream", "waffles"],
    "anonymous": true
}'
```

### Response Format

| Field     | Description                                                                                |
|-----------|--------------------------------------------------------------------------------------------|
| `status`  | A boolean indicating whether the request succeeded or failed                               |
| `message` | A feedback on the action that was requested                                                |
| `data`    | A key-value map of your election's configuration, returned only if `status` returns `true` |
| `error`   | The exception that occurred at the server, returned only if `status` returns `false`       |

If your election creation request is successful, you will be able to access your election's `_id` stored in
the `data` field. Remember to use this ID when casting your votes and to access results.

## Retrieve Results

You can view your election results by sending a `GET` request to the `/viewElection/_id` endpoint.

An example is provided below:

```bash
curl --location --request GET 'https://localhost:5000/viewElection/_id'
```

### Response Format

| Field     | Description                                                                                                              |
|-----------|--------------------------------------------------------------------------------------------------------------------------|
| `status`  | A boolean indicating whether the request succeeded or failed                                                             |
| `message` | A feedback on the action that was requested                                                                              |
| `data`    | A key-value map of your election's data including configuration and votes cast, returned only if `status` returns `true` |
| `error`   | The exception that occurred at the server, returned only if `status` returns `false`                                     |

## Remove an Election

You can remove an election by sending a `GET` request to the `/removeElection/_id` endpoint. Note that this
action is irreversible and can only be performed by the person who created the election.

```bash
curl --location --request GET 'https://localhost:5000/removeElection/_id'
```

### Response Format

| Field     | Description                                                                                                              |
|-----------|--------------------------------------------------------------------------------------------------------------------------|
| `status`  | A boolean indicating whether the request succeeded or failed                                                             |
| `message` | A feedback on the action that was requested                                                                              |
| `data`    | A key-value map of your election's data including configuration and votes cast, returned only if `status` returns `true` |
| `error`   | The exception that occurred at the server, returned only if `status` returns `false`                                     |

## Update an Election

You can update an election by sending a `POST` request to the `/updateElection/_id` endpoint. Note that this
action can only be performed by the person who created the election.

The request body is a JSON object with the fields that you wish to update. These fields are the same as the ones
described in the [Create an Election](#create-an-election) section.

Note that updating the `_id` field is not allowed. If you update the `candidates`, `number_of_winners`
or `voting_strategy`, all ballots cast in the election will be removed and the election will be reset.

```bash
curl --location --request POST 'https://localhost:5000/updateElection/_id' 
--header 'Content-Type: application/json' \
--data-raw '{
    "candidates": ["pancakes", "doughnuts", "waffles"],
    "anonymous": true
}'
```

### Response Format

| Field     | Description                                                                                                              |
|-----------|--------------------------------------------------------------------------------------------------------------------------|
| `status`  | A boolean indicating whether the request succeeded or failed                                                             |
| `message` | A feedback on the action that was requested                                                                              |
| `data`    | A key-value map of your election's data including configuration and votes cast, returned only if `status` returns `true` |
| `error`   | The exception that occurred at the server, returned only if `status` returns `false`                                     |

## Cast or Update your Ballot

You can cast your votes by sending a `GET` request to the `/addVote/_id` endpoint. Append the URL with the
ordered candidates, separated with a ```/```. If you have already cast a vote, this action will update your
vote. An example is provided below:

```bash
curl --location --request GET 'https://localhost:5000/addVote/_id/pancakes/icecream/waffles'
```

### Response Format

| Field     | Description                                                                          |
|-----------|--------------------------------------------------------------------------------------|
| `status`  | A boolean indicating whether the request succeeded or failed                         |
| `message` | A feedback on the action that was requested                                          |
| `error`   | The exception that occurred at the server, returned only if `status` returns `false` |

## Remove your Ballot

You can remove your vote by sending a `GET` request to the `/removeVote/_id` endpoint. Note that this action
will remove only your vote, not all votes.

```bash
curl --location --request GET 'https://localhost:5000/removeVote/_id'
```

### Response Format

| Field     | Description                                                                          |
|-----------|--------------------------------------------------------------------------------------|
| `status`  | A boolean indicating whether the request succeeded or failed                         |
| `message` | A feedback on the action that was requested                                          |
| `error`   | The exception that occurred at the server, returned only if `status` returns `false` |

# How to set up the API

## Using Docker-Compose

The easiest way to set up the app is to use Docker-Compose. Run the following command:

```bash
docker-compose --project-name ranked-choice-voting-api up -d
```

## Using a Python Environment

Alternatively, you can also use the following commands to set up the app:

1. Create a new Python3 environment and activate it
    ```bash
    virutalenv ranked-choice-voting-api
    source ranked-choice-voting-api/bin/activate
    ```

2. Install the requirements
    ```bash
    pip install -r requirements.txt
    ```

3. Modify the `.env` file if you wish to customize the app. The default values are:
    ```bash
    MONGO_URI=mongodb://mongo:27017/ # Change this to your MongoDB URI
    TTL_SECONDS=2592000 # time in seconds the election is persisted after it ends (default is 30 days)
    HOST="0.0.0.0" # Change this to your host
    PORT=5000 # Change this to your port
    ```

4. Run the app
    ```bash
    python3 app/app.py
    ```

# FAQs

### Who can see my election?

Anyone you wish to share the `_id` of your election with can view your election and cast their votes. Additionally, if
the `anonymous` field is set to `False`, then anyone with the `_id` can view the ballots cast as well. Otherwise, only
the person who created the election can view the ballots.

### How does the app track different users?

The app uses IP addresses to track different users. This is used to map a user to their ballot and is used to update
votes (or prevent multiple votes). Every time you create an election or add a vote, your IP address is recorded and used
to identify you.

### Can I update my vote?

This behavior depends on the `update_votes` field. If this field is set to `True`, then you can update or remove your
vote from the election.

### Can I update my election details?

This currently is not supported. If you would like to update your election details, please contact the administrators.

### What data is being collected from me?

No data is being collected from you, except for your IP address. This is used to identify you and to prevent multiple
votes.

### Can the API be linked with an automated system like a bot?

No, the API cannot be *completely* linked with a bot. This is because the API uses IP addresses to identify users. If a
bot sends requests to the API, it will always be treated as the same user (with the bot's IP address), and hence there
will always be one voter, regardless of the number of people casting the vote through the bot.

However, the bot can be used to create elections, view election results, and construct a URL for a user to click and
vote.
