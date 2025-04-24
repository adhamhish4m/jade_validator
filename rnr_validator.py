from flask import Flask, request, jsonify
from flask_cors import CORS
from project_validator import validate_urls, validate_question, validate_final_answer
import gspread # For Google Sheets API
from oauth2client.service_account import ServiceAccountCredentials  # Google Sheets authentication

app = Flask(__name__)
CORS(app)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(credentials)

try:
    # Admin dashboard - for flagged submissions
    admin_dashboard_sheet = client.open('Jade - Admin Dashboard').sheet1
    # High Quality Submissions dataset
    hqs_sheet = client.open('Jade - HQS').sheet1
    # Low Quality Submissions dataset
    lqs_sheet = client.open('Jade - LQS').sheet1
except gspread.SpreadsheetNotFound:
    print("Error: The specified Google Sheets were not found. Please check the sheet name sand permissions.")
    raise

rating_to_score = {
    "invalidURL": -10,
    "validURL": 1,
    "dontFollowCategory": -10,
    "followCategory": 1,
    "notCreative": 0,
    "somewhatCreative": 0.5,
    "veryCreative": 1,
    "incorrectDocument": -1,
    "correctDocumentButFormat": 1,
    "correctDocument": 2,
    "incorrectPages": -1,
    "correctPagesButFormat": 1,
    "correctPages": 2,
    "incorrectCalc": 0,
    "correctCalcButFormat": 0.5,
    "correctCalc": 1,
    "incorrectFinal": -10,
    "correctFinalButFormat": 1,
    "correctFinal": 1,

}

@app.route('/rnr_validator.py', methods=['POST'])
def validate_ratings():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Extract IDs and PII flag
        rater_id = data.get("rater_id")
        submission_id = data.get("submission_id")
        worker_id = data.get("worker_id")
        contains_pii = data.get("containsPII", False)

        # Handle PII submissions
        if contains_pii:
            message = "Low Quality Submission pushed to dataset"
            # Add to LQS dataset
            lqs_sheet.append_row([
                worker_id, submission_id, "Contains PII"
            ])
            return jsonify({"message": message}), 200

        # Calculate total score
        total_score = sum(rating_to_score.get(data.get(key, ""), 0) for key in [
            "urlRating",
            "questionRating",
            "questionCreativity",
            "documentRating",
            "answerPagesRating",
            "answerCalculationsRating",
            "finalAnswerRating"
        ])

        # Calculate validator score using an example question and answer
        validator_score = sum([
            int(validate_urls(data.get("urls", ["https://www.sec.gov/Archives/edgar/data/1018724/000101872425000004/amzn-20241231.htm",
                                                "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm",
                                                "https://www.sec.gov/Archives/edgar/data/1045810/000104581024000029/nvda-20240128.htm#i13eac97307cc485c971e826acbda8be7_97"])),),

            int(validate_question(data.get("question", "What was Amazon's debt to equity ratio compared with Apple and Nvidia in '24?"), data.get("category", "C"))),
            int(validate_final_answer(data.get("final_answer", "Amazon is 338924, Nvidia is 12,435 and Apple is 308030"), data.get("question", "What was Amazon's debt to equity ratio compared with Apple and Nvidia in '24?")))
        ])

        # Determine response message
        if total_score < 0 and validator_score < 0:
            message = "Low Quality Submission pushed to dataset"
            lqs_sheet.append_row([
                worker_id, submission_id
            ])
        elif (total_score <= 0 or validator_score <= 0) or (total_score > 0 and validator_score > 0):
            message = "Rater Flagged and Submission requires re-rating"
            admin_dashboard_sheet.append_row([
                rater_id, submission_id, worker_id
            ])
        else:
            message = "High Quality Submission pushed to dataset"
            hqs_sheet.append_row([
                worker_id, submission_id
            ])

        return jsonify({"rater_score": total_score, "validator_score": validator_score, "message": message}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)