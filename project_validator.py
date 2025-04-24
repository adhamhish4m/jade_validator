import os
from dotenv import load_dotenv
from openai import OpenAI

submission = {
    "urls": ["https://www.sec.gov/Archives/edgar/data/1018724/000101872425000004/amzn-20241231.htm",
"https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm",
"https://www.sec.gov/Archives/edgar/data/1045810/000104581024000029/nvda-20240128.htm#i13eac97307cc485c971e826acbda8be7_97"],
    "category": "A",
    "question": "What were Apple's net sales in 2024?",
    "documents":  [],
    "pages" : "",
    "calculations": "",
    "final_answer": "$400 million",
}

def ai_assistant(system_prompt, main_prompt):
        load_dotenv()
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

def validate_urls(urls):
    prompt = (
        f"Analyze the list of URLs provided and determine if they are all valid SEC document URLs. "
        f"Each URL must meet both of the following criteria: "
        f"1. It must be from the official SEC website (i.e., the domain should be 'sec.gov'). "
        f"2. It must link to a document published on or after October 1, 2023. "
        f"Only consider URLs that point directly to documents such as filings or reports. "
        f"URLs: {urls} "
        f"If every URL in the list meets both criteria, respond with only '1'. "
        f"If any URL fails to meet the criteria, respond with only '-10'."
    )
    return ai_assistant("You are a helpful assistant.", prompt)

def validate_question(question, category):
    category_requirements = {
                "A": "The question must be simple, ask for a single, clearly stated data point from a single uploaded 10-K or 10-Q document. It should not require calculations, inference, or combining information from different sections. Example: 'What was Amazon’s total assets in 2024?'",
                "B": "The question must still refer to a single 10-K or 10-Q document but should involve a harder query. It must meet at least one of the following: require calculation (e.g., ratios), require inference, or require pulling multiple related data points from different sections of the same document. Example: 'What was Apple’s current ratio in 2023?' or 'What was Nvidia’s gross margin in 2022?'",
                "C": "The question must involve multiple 10-K or 10-Q documents, either from different companies or multiple reports from the same company. It should also meet the same complexity requirements as Category B (calculation, inference, or combining multiple data points). Example: 'Compare Amazon and Apple’s current ratios in 2023.' or 'What was Tesla’s gross profit compared to Nvidia and Apple in 2024?'"
        }
    prompt = (
        f"Evaluate whether the following question fits the requirements for Category {category}: "
        f"{category_requirements[category]} "
        f"Question: {question} "
        f"If the question meets all the requirements for Category {category}, respond with only '1'. "
        f"If it does not meet the requirements, respond with only '-10'."

    )
    return ai_assistant("You are a helpful assistant.", prompt)

def validate_final_answer(final_answer, question):
     prompt = (
            f"Evaluate whether the final answer is relevant to the question provided. "
            f"The answer does not need to be factually accurate or detailed, but it must directly address the question being asked. "
            f"Concise answers (e.g., a single number or phrase) are acceptable if they match what the question is asking for. "
            f"If the final answer is relevant and attempts to answer the question appropriately, respond with only '1'. "
            f"If the final answer is unrelated, vague, or does not address the question meaningfully, respond with only '-10'. "
            f"Question: {question} "
            f"Final Answer: {final_answer}"

    )
     return ai_assistant("You are a helpful assistant.", prompt)
     

url_validity = validate_urls(submission["urls"])
question_validity = validate_question(submission["question"], submission["category"])
finally_answer_validity = validate_final_answer(submission["final_answer"], submission["question"])


if __name__ == "__main__":
    print ([url_validity, question_validity, finally_answer_validity])

