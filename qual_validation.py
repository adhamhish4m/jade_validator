from flask import Flask, request, jsonify
import os
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from deepseek import DeepSeekAPI
import openai
from dotenv import load_dotenv
from openai import OpenAI
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

class Validation:
    def __init__(self, urls, category, question, answer=None):
        self.urls = urls
        self.category = category
        self.question = question
        self.answer = answer
        load_dotenv()

    def check_urls(self):
        prompt = (
        f"Analyze the list of URLs provided and determine if they are all valid SEC document URLs. "
        f"Each URL must meet both of the following criteria: "
        f"1. It must be from the official SEC website (i.e., the domain should be 'sec.gov'). "
        f"2. It must link to a document published on or after October 1, 2023. "
        f"Only consider URLs that point directly to documents such as filings or reports. "
        f"URLs: {self.urls} "
        f"If every URL in the list meets both criteria, respond with only '1'. "
        f"If any URL fails to meet the criteria, respond with only '0'."
    )
        return Validation.ai_assistant("You are a helpful assistant.", prompt)

    def check_question(self):
        # check if the question follows the selected category
        category_requirements = {
                "A": "The question must be simple, ask for a single, clearly stated data point from a single uploaded 10-K or 10-Q document. It should not require calculations, inference, or combining information from different sections. Example: 'What was Amazon’s total assets in 2024?'",
                "B": "The question must still refer to a single 10-K or 10-Q document but should involve a harder query. It must meet at least one of the following: require calculation (e.g., ratios), require inference, or require pulling multiple related data points from different sections of the same document. Example: 'What was Apple’s current ratio in 2023?' or 'What was Nvidia’s gross margin in 2022?'",
                "C": "The question must involve multiple 10-K or 10-Q documents, either from different companies or multiple reports from the same company. It should also meet the same complexity requirements as Category B (calculation, inference, or combining multiple data points). Example: 'Compare Amazon and Apple’s current ratios in 2023.' or 'What was Tesla’s gross profit compared to Nvidia and Apple in 2024?'"
        }
        prompt = (
            f"Evaluate whether the following question fits the requirements for Category {self.category}: "
            f"{category_requirements[self.category]} "
            f"Question: {self.question} "
            f"If the question meets all the requirements for Category {self.category}, respond with only 'Valid'. "
            f"If it does not meet the requirements, respond with only 'Invalid'."

        )
        return Validation.ai_assistant("You're a helpful assisstant", prompt)

    
    @staticmethod
    def ai_assistant(system_prompt, main_prompt):
        llm = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), base_url="https://api.deepseek.com")
        response = llm.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": f"{system_prompt}"},
                {"role": "user", "content" : f"{main_prompt}"},
            ],
            stream=False
        )
        return response.choices[0].message.content

    
    def check_answer(self):
        answer_requirements = {
            "A": """
            document: Include the document required to answer the question in the format: <Company Name> 10-K <year> if it's a 10-K, and <Company Name> 10-Q <qurater> <year> if it's a 10-Q. Example: Amazon 10-K 2024 OR Apple 10-Q Q2 2024".
            page: This part should only include a single page number where the answer can be found. For example, 10.
            final_answer: This part should only include the answer to the given question. For example, "274,515 Million" or "Epic Games sued Apple after alleging antitrust behavior". This has to answer the question given by the user and cannot do anything else.
            """,
            "B": """
            document: Include the document required to answer the question in the format: <Company Name> 10-K <year> if it's a 10-K, and <Company Name> 10-Q <qurater> <year> if it's a 10-Q. Example: Amazon 10-K 2024 OR Apple 10-Q Q2 2024".
            pages: This part should only include the page number(s) that the answer can be found on. For example: 26, 27. This has to be a number (or multiple) and cannot be anything else or ommitted.
            calculation: This is optional depending on if the question requires a calculation. If it does, this should show the correct equation and calculation for that question's answer. For example, "Equation: Current Assets / Current Liabilities \n Current ratio = 152,987 / 176,392".
            final_answer: This part should only include the answer to the given question. For example, "274,515 Million" or "Epic Games sued Apple after alleging antitrust behavior". This has to answer the question given by the user and cannot do anything else.
            """
        }

        prompt = (
        f"Analyze the answer provided and determine if it follows the requirements of the category? "
        f"The question should follow each metric given "
        f"URL: {(self.urls)}"
        f"Category: {(self.category)}"
        f"Question: {(self.question)}"
        f"Answer: {(self.answer)}"
        f"Requirements: {answer_requirements[self.category]}"
        f"Only answer with 'Valid' if the answer follows the instructions above and 'Invalid' if it does not. Do not include anything else or any explanations."
        )
        return Validation.ai_assistant("You're a helpful assisstant", prompt)

@app.route('/validate', methods=['POST'])
def validate_question():
    data = request.json
    url = data.get("urls")
    category = data.get("category")
    question = data.get("question")
    answer = data.get("answer", {})

    if not url or not category or not question:
        return jsonify({"status": "Invalid", "error": "Missing required fields"}), 400

    validation = Validation(url, category, question, answer)
    question_validity = validation.check_question()
    answer_validity = validation.check_answer()

    if question_validity == "Valid" and answer_validity == "Valid":
        status = "Valid Submission - user granted access to main project"
    else:
        status = {
            "category": category,
            "question_status": question_validity,
            "answer_status": answer_validity
        }

    response = jsonify({"status": status})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Methods", "POST")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    return response

@app.route('/validate-answer', methods=['POST'])
def validate_answer():
    data = request.json

    # Extract data from the incoming JSON
    urls = data.get("urls")
    questions = data.get("questions", [])

    if not urls or not questions:
        return jsonify({"status": "Invalid", "error": "Missing required fields"}), 400

    results = []
    all_valid = True
    for question_data in questions:
        category = question_data.get("category")
        question = question_data.get("question")
        answer = question_data.get("answer", {})

        # Extract answer fields
        documents = answer.get("documents")
        pages = answer.get("pages")
        calculations = answer.get("calculations", None)
        final_answer = answer.get("final_answer")

        # Validate required fields for each question
        if not category or not question or not documents or not pages or not final_answer:
            results.append({
                "category": category,
                "question_status": "Invalid",
                "answer_status": "Invalid",
                "error": "Missing required fields"
            })
            all_valid = False
            continue

        validation = Validation(
            urls=urls,
            category=category,
            question=question,
            answer={
                "documents": documents,
                "pages": pages,
                "calculations": calculations,
                "final_answer": final_answer
            }
        )

        # Perform question and answer validation
        question_validity = validation.check_question()
        answer_validity = validation.check_answer()
        if question_validity != "Valid" or answer_validity != "Valid":
            all_valid = False
        results.append({
            "category": category,
            "question_status": question_validity,
            "answer_status": answer_validity
        })

    if all_valid:
        response = jsonify({"status": "Valid Submission - user granted access to main project"})
    else:
        response = jsonify({"results": results})

    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Methods", "POST")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    return response

@app.route('/upload-report', methods=['POST'])
def upload_report():
    try:
        if 'report_upload' not in request.files:
            return jsonify({"status": "Invalid", "error": "No file part in the request"}), 400

        file = request.files['report_upload']
        if file.filename == '':
            return jsonify({"status": "Invalid", "error": "No selected file"}), 400

        if file and file.filename.endswith('.pdf'):
            uploads_dir = os.path.join(os.getcwd(), "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            file.save(os.path.join(uploads_dir, file.filename))
            response = jsonify({"status": "Success", "message": "File uploaded successfully"})
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response, 200
        else:
            return jsonify({"status": "Invalid", "error": "Only PDF files are allowed"}), 400
    except Exception as e:
        return jsonify({"status": "Error", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
