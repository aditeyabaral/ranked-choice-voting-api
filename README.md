# ranked-voting
Simple app for [ranked-choice voting](https://www.rankedvote.co/guides/understanding-ranked-choice-voting/how-does-ranked-choice-voting-work) in an election.

Ranked-voting is a Flask app that serves API endpoints for a ranked-choice voting, supporting both creation of elections, retrieval of results and casting of votes using HTTP requests.

# How to use ranked-voting

## Create an Election

Creation of elections is performed using a `POST` request. The request body is a JSON object with the following fields:

```json
{
    "election_id": {OPTIONAL} A custom ID for the election. If not provided, a random ID will be generated.
    "election_name": {OPTIONAL} The name of your election
    "start_time": {OPTIONAL} when does the election start?
    "end_time": {OPTIONAL} when does the election end?
    "description": {OPTIONAL} A short description of your election
    "anonymous": {OPTIONAL} true or false
    "candidates": ["candidate-1", "candidate-2", ...]
}
```

An example is provided below:

```bash
curl --location --request POST 'https://ranked-voter.herokuapp.com/add' \
--header 'Content-Type: application/json' \
--data-raw '{
    "election_name": "Food ranking",
    "description": "Rank your favourite foods!",
    "candidates": ["pancakes", "ice-cream", "waffles"],
    "anonymous": true
}'
```

Once you create an election, you will be shown the `ELECTION_ID`. Remember to use this ID when casting your votes and to access results.

## Retrieve Results

You can view your election results using a `GET` request to the `/ELECTION_ID` endpoint.

An example is provided below:


```bash
curl --location --request GET 'https://ranked-voter.herokuapp.com/ELECTION_ID'
```

## Cast your votes

You can cast your votes using a `GET` request to the `vote/ELECTION_ID` endpoint. Append the URL with the ordered candidates, separated with a ```/```. Remember to include all the candidates since this is a ranked-choice voting.

An example is provided below:

```bash
curl --location --request GET 'https://ranked-voter.herokuapp.com/vote/ELECTION_ID/pancakes/icecream/waffles'
```

## What is *currently* not supported?

1. Delete an election
2. Delete your vote
3. Better error handling

# How to setup ranked-voting

1. Clone the repository and navigate to the root directory
    ```bash
    git clone https://github.com/aditeyabaral/ranked-voting
    cd ranked-voting
    ```

2. Create a new Python3 environment and activate it
    ```bash
    virutalenv ranked-voting
    source ranked-voting/bin/activate
    ```

3. Install the requirements
    ```bash
    pip install -r requirements.txt
    ```

4. Create a `.env` file and add a database connection URL
    ```bash
    APP_DATABASE_URL="<YOUR-DATABASE-URL>"
    ```

5. Run the app
    ```bash
    python3 app/app.py
    ```
