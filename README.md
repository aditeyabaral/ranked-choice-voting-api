# ranked-choice-voting-api
Simple API for [ranked-choice voting](https://www.rankedvote.co/guides/understanding-ranked-choice-voting/how-does-ranked-choice-voting-work) in an election.

Ranked-choice Voting is a Flask app that serves API endpoints for a ranked-choice voting, supporting both creation of elections, retrieval of results and casting of votes using HTTP requests.

# How does Ranked-Choice Voting Work?

```mermaid
graph TD
    A[Each voter ranks all candidates in order of preference] --> |Round r = 1 begins| B[Tally all first choices of all voters]
    B --> C{Does first choice have<br>simple majority?}
    C --> |Yes| D[First choice wins]
    C --> |No| E{Do all candidates share<br>the highest tallied vote?}
    E --> |No| F[Remove candidate with least votes]
    E --> |Tie-breaker needed| H["For each candidate ranked by a voter,<br>give them a score of (number of candidates - position on voter's list)"]
    H --> I["Tally aggregated scores of each candidate<br>and find the highest scoring candidate(s)"]
    I --> J{Do multiple candidates share<br>the same highest score?}
    J --> |Yes| K[Return any of the highest scoring candidates]
    J --> |No| L[Highest scoring candidate wins]
    F --> G[Move votes of supporters of the eliminated candidate<br>to their second choice candidate]
    G --> |Round r = r + 1 begins| B
```

If the above flowchart does not render, visit this [link](https://mermaid.live/view#pako:eNp9VE1z2jAU_CtvdGk6hUOvTJtOEyCEfhxSLh2bg7Ae9mssySPJdBjgv_dJhthkJuXgMfK-3fWu5IMorEIxEaWTTQWraW6Af1-zmSwq2NmADpw0zx5kXUMhjSIlA3ogA9Ypfmq30DjcokNT4BrG41s4PtnWKHDwGT7CBksy_gh32Yop9olnS84HKCpLBVMxQ1xMYn7dGbhLRPeHqWXAEA6V3OGnjbv1pJsaQcs_1lHYfzl1g_edg9_IktNsPpz8yz7WV6if9ggz1nj9cr6SLomEigWprJBZAoMIVfJ5UZv1PPPsCbXdYc_DgqGCGiUPx6GL-HloRTjeOJTPHKJBVKiOsMhyMbcOMKbfE8UGWHnD6XUxjaK5kliNHWpe9YV1GJO8Ma3edLUMXmgMjfUUyHJrpqN456EmH97n4mxrkWw9soNzUWXpsORx1bGnoq6NRRd8zwXxZZhVHCBT9sgb3ws9JqFlzF23daBY41vhe6mvWV-iXw6K_sbZh9YZkGYfXf7XyqWGZd_d92zxFnq4a-Zp4iH7EWtOjUYx3zaNdXHvXqSxJk0mJXcVVbDxMTnwWFhO7LwvXzBnmYfXh8jBh-FB6lDxKkZCo9OSFJ_gQ1zJRdwQmIsJ3yrcSg44F7k5MbRtoshMUbBOTIJrcSRkG-yvvSku_zvMlCR_D3S3ePoHL9pnVg) to view the flowchart. You can also view it [here](https://raw.githubusercontent.com/aditeyabaral/ranked-choice-voting-api/main/img/ranked-choice-voting-algorithm.jpg).

# How to use ranked-choice-voting-api

## Create an Election

Creation of elections is performed by sending either a `GET` or `POST` request. 

### ```GET```

A `GET` request is the quickest way to setup a ranked-choice election, but offers no customization options since all fields take their default values. Create an election by appending a `/` separated list of candidates to the `/add` endpoint. 

```bash
curl --location --request GET 'https://ranked-voter.herokuapp.com/add/pancakes/waffles/ice-cream'
```

### ```POST```

You can also create an election by sending a `POST` request. This is the most flexible way to create an election, but requires you to specify the fields you wish to customize.

The request body is a JSON object with the following fields:

| Field         	| Optional 	| Default      	| Description                                                                                       	|
|---------------	|----------	|--------------	|---------------------------------------------------------------------------------------------------	|
| `election_id`   	| Yes      	| Random       	| A custom ID for your election                                                                     	|
| `election_name` 	| Yes      	| NULL         	| The name of your election                                                                         	|
| `start_time`    	| Yes      	| Current time 	| The timestamp at which your election starts. Votes made only after the start time will be counted 	|
| `end_time`      	| Yes      	| NULL         	| The timestamp at which your election ends. Votes made only before the end time will be counted    	|
| `description`   	| Yes      	| NULL         	| A short description about your election                                                           	|
| `anonymous`     	| Yes      	| False        	| A boolean value indicating whether votes cast in your election are publicly viewable              	|
| `update_votes`  	| Yes      	| True         	| A boolean value indicating whether a voter can update or delete their vote                        	|
| `allow_ties`    	| Yes      	| False        	| A boolean value indicating whether your election can have a tied winner                           	|
| `candidates`    	| No       	| -            	| A list of unique strings where each element represents a candidate                                	|

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

### Response Format

| Field   	| Description                                                                      	|
|---------	|----------------------------------------------------------------------------------	|
| `status`  	| A boolean indicating whether the request succeeded or failed                 	|
| `message` 	| A feedback on the action that was requested                                      	|
| `data`    	| A key-value map of your election's configuration, returned only if `status` returns `true`   	|
| `error`   	| The exception that occurred at the server, returned only if `status` returns false 	|

If your election creation request is successful, you will be able to access your election's `election_id` stored in the `data` field. Remember to use this ID when casting your votes and to access results.

## Retrieve Results

You can view your election results by sending a `GET` request to the `/election_id` endpoint.

An example is provided below:


```bash
curl --location --request GET 'https://ranked-voter.herokuapp.com/election_id'
```

### Response Format

| Field   	| Description                                                                      	|
|---------	|----------------------------------------------------------------------------------	|
| `status`  	| A boolean indicating whether the request succeeded or failed                 	|
| `message` 	| A feedback on the action that was requested                                      	|
| `data`    	| A key-value map of your election's data including configuration and votes cast, returned only if `status` returns `true`   	|
| `error`   	| The exception that occurred at the server, returned only if `status` returns false 	|

## Remove an Election

You can remove an election by sending a `GET` request to the `/vote/election_id` endpoint. Note that this action is irreversible and can only be performed by the person who created the election.

```bash
curl --location --request GET 'https://ranked-voter.herokuapp.com/remove/election_id'
```

### Response Format

| Field   	| Description                                                                      	|
|---------	|----------------------------------------------------------------------------------	|
| `status`  	| A boolean indicating whether the request succeeded or failed                 	|
| `message` 	| A feedback on the action that was requested                                      	|
| `data`    	| A key-value map of your election's data including configuration and votes cast, returned only if `status` returns `true`   	|
| `error`   	| The exception that occurred at the server, returned only if `status` returns false 	|

## Cast your votes

You can cast your votes by sending a `GET` request to the `vote/election_id` endpoint. Append the URL with the ordered candidates, separated with a ```/```. Remember to include all the candidates since this is a ranked-choice voting.

An example is provided below:

```bash
curl --location --request GET 'https://ranked-voter.herokuapp.com/vote/election_id/pancakes/icecream/waffles'
```

### Response Format

| Field   	| Description                                                                      	|
|---------	|----------------------------------------------------------------------------------	|
| `status`  	| A boolean indicating whether the request succeeded or failed                 	|
| `message` 	| A feedback on the action that was requested                                      	|
| `error`   	| The exception that occurred at the server, returned only if `status` returns `false` 	|

## Remove your vote

You can remove your vote by sending a `GET` request to the `/unvote/election_id` endpoint. Note that this action will remove only your vote, not all votes.

```bash
curl --location --request GET 'https://ranked-voter.herokuapp.com/unvote/election_id'
```

### Response Format

| Field   	| Description                                                                      	|
|---------	|----------------------------------------------------------------------------------	|
| `status`  	| A boolean indicating whether the request succeeded or failed                 	|
| `message` 	| A feedback on the action that was requested                                      	|
| `error`   	| The exception that occurred at the server, returned only if `status` returns `false` 	|

# How to setup the app

## Using Docker-Compose

The easiest way to setup the app is to use Docker-Compose. Run the following command:
    
```bash
docker-compose -f ./docker/docker-compose.yml --project-name ranked-choice-voting-api up -d
```

## Using a Python Environment

Alternatively, you can also use the following commands to setup the app:

1. Create a new Python3 environment and activate it
    ```bash
    virutalenv ranked-choice-voting-api
    source ranked-choice-voting-api/bin/activate
    ```

2. Install the requirements
    ```bash
    pip install -r requirements.txt
    ```

3. Modify the `.env` file and add your database connection URL. For example, if you have setup PostgreSQL locally, you can use the following:
    ```bash
    APP_DATABASE_URL=postgresql://user:password@localhost:5432/db_name
    ```

4. Run the app
    ```bash
    python3 app/app.py
    ```

# FAQs

### Who can see my election?

Anyone you wish to share the `election_id` with can view your election and cast their votes. Additionally, if the `anonymous` field is set to `False`, then anyone with the `election_id` can view your election results as well. Otherwise, only the person who created the election can view the results.

### How does the app track different users?

The app uses IP addresses to track different users. This is used to map a user to their vote, and is used to update votes (or prevent multiple votes). Everytime you create an election or add a vote, your IP address is recorded and used to identify you.

### Can I update my vote?

This behaviour depends on the `update_votes` field. If this field is set to `True`, then you can update or remove your vote from the election.

### Can I update my election details?

This currently is not supported. If you would like to update your election details, please contact the administrators.

### What data is being collected from me?

No data is being collected from you, except for your IP address. This is used to identify you and to prevent multiple votes.

### Can the API be linked with an automated system like a bot?

No, the API cannot be *completely* linked with a bot. This is because the API uses IP addresses to identify users. If a bot sends requests to the API, it will always be treated as the same user (with the bot's IP address), and hence there will always be one voter, regardless of the number of people casting the vote thorugh the bot.

However, the bot can be used to create elections, view election results, and construct a URL for a user to click and vote.
