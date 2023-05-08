def update_election_with_new_data(new_election_data):
    election_id = new_election_data["election_id"]
    created_by = (
        request.headers.getlist("X-Forwarded-For")[0]
        if request.headers.getlist("X-Forwarded-For")
        else request.remote_addr
    )
    current_election_data = election_db.get_election_data_by_id_and_creator(
        election_id, created_by
    )
    for key in new_election_data:
        if key in current_election_data:
            if key == "candidates":
                if set(current_election_data["candidates"]) != set(
                        new_election_data["candidates"]
                ):
                    current_election_data["votes"] = None
                    current_election_data["round_number"] = None
                    current_election_data["winner"] = None
                    current_election_data["candidates"] = new_election_data[
                        "candidates"
                    ]
                    logging.warning(
                        "Candidates changed. Resetting votes, round_number, winner"
                    )
            elif key in [
                "election_id",
                "created_at",
                "created_by",
                "votes",
                "round_number",
                "winner",
            ]:
                logging.warning(
                    f"Attempt to update {key} not allowed for election {election_id}"
                )
                continue
            else:
                current_election_data[key] = new_election_data[key]

    start_time = current_election_data["start_time"]
    try:
        start_time = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    except:
        start_time = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S.%f")

    end_time = current_election_data["end_time"]
    try:
        end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    except:
        end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S.%f")

    if start_time >= end_time:
        end_time = start_time + datetime.timedelta(days=7)

    current_election_data["end_time"] = end_time
    current_election_data["start_time"] = start_time

    election_db.update_election_details(current_election_data)
    logging.debug(f"Updated election {election_id} with new data")
    return current_election_data


@app.route("/unvote/<election_id>", methods=["GET"])
def remove_vote(election_id):
    try:
        if not election_db.check_election_id_exists(election_id):
            raise Exception("Election ID does not exist")
    except Exception as e:
        logging.error(f"Exception occurred while removing vote from {election_id}: {e}")
        output = {
            "status": False,
            "message": f"Error occurred while removing vote. This might also be due to an invalid election ID.",
            "error": str(e),
        }
        return jsonify(output), 400

    http_prefix = "https" if request.is_secure else "http"
    ip_address = (
        request.headers.getlist("X-Forwarded-For")[0]
        if request.headers.getlist("X-Forwarded-For")
        else request.remote_addr
    )
    logging.debug(f"Unvoting for {ip_address} from election {election_id}")
    output = dict()
    try:
        election_db.remove_vote(election_id, ip_address)
        output["status"] = True
        output["message"] = "Vote removed successfully."
        response_code = 200
    except Exception as e:
        logging.error(f"Exception occurred while unvoting: {e}")
        output["status"] = False
        output[
            "message"
        ] = "Error occurred while removing vote. This might also be due to a database error. Contact the administrators for more information."
        output["error"] = str(e)
        response_code = 400
    return jsonify(output), response_code


@app.route("/update", methods=["POST"])
def update_election():
    new_election_data = request.get_json()
    logging.debug(f"New election data: {new_election_data}")
    output = dict()
    if new_election_data:
        try:
            updated_election_data = update_election_with_new_data(new_election_data)
            output["status"] = True
            output["message"] = "Election updated successfully."
            output["data"] = updated_election_data
            response_code = 200
        except Exception as e:
            logging.error(f"Exception occurred while updating election: {e}")
            output["status"] = False
            output["message"] = "Error occurred while updating election."
            response_code = 400

    return jsonify(output), response_code
