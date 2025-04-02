import os
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from deepseek import DeepSeekAPI  # Import DeepSeek V3
import openai
from dotenv import load_dotenv
from openai import OpenAI

class Validation:
    def __init__(self, url, category, question, answer):
        self.url = url
        self.category = category
        self.question = question
        self.answer = answer
        load_dotenv()

    def check_url(self):
        prompt = (
        f"Analyze the URL provided and determine if it corresponds to a valid document "
        f"published in October 2023 or later, including future dates like 2025. "
        f"Ensure the response is accurate and does not dismiss valid future dates. "
        f"URL: {(self.url)}"
        f"Only answer with 'Valid' if the URL follows the instructions above and 'Invalid' if it is not. "
    )
        return Validation.ai_assistant("You are a helpful assistant.", prompt)

    def check_question(self):
        # check if the question follows the selected category
        category_requirements = {
            "A" : """
            difficulty: question is simple (don't require any calculations for things not already available in a 10-K or 10-Q or inferring information). For example, anything that asks about ratios for example requires some form of calculation of data which makes it not readily available, meaning it does not follow this category.
            specificity: question is about a single document (10-K or 10-Q) which the user has already uploaded and cannot be about more than that. It needs to also be asking about a single piece of information that is pulled from one part of the report.
            relevance: question asks about the document in the provided URL.
            time_bound: question is asking about information from that can be pulled from a 10-K/Q published from October 2023 onwards. 
            example: What was Apple's revenue in 2023?
            """,
            "B" : """
            difficulty: question is hard (either requires a calculation or pulling information from different parts of the uploaded 10-K/Q)
            specificity: question is about a single document (10-K or 10-Q) which the user has already uploaded and cannot be about more than that.
            relevance: question asks about the document in the provided URL.
            time_bound: question is asking about information from that can be pulled from a 10-K/Q published from October 2023 onwards. 
            example: What was Apple's current ratio in 2023? (requires calculation)
            """,
            "C" : """
            difficulty: question is hard (requires pulling data / calculations from multiple 10-K/Q documents uploaded by the user)
            specificity: question is more than one 10-K or 10-Q document which the user has already uploaded
            relevance: question asks about the documents in the provided URLs.
            time_bound: question is asking about information from that can be pulled from a 10-K/Q published from October 2023 onwards. 
            example: Compare Apple and Nvidia's gross profit margins in 2024 (requires calculation and pulling data from multiple reports)
            """
        }

        prompt = (
        f"Analyze the question provided and determine if it follows the requirementss of the selected category "
        f"The question should follow each metric given "
        f"URL: {(self.url)} "
        f"Category: {(self.category)} "
        f"Question: {(self.question)} "
        f"Requirements: {category_requirements[self.category]} "
        f"Only answer with 'Valid' if the question follows the instructions above and 'Invalid' if it is not. "
        )
        return Validation.ai_assistant("You're a helpful assisstant", prompt)

    
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
        # different categories have different answer fields
        # Category A: Document (e.g. Amazon 10-K), Page, Final Answer
        # Category B: Document, Page(s), Calculation, Final Answer
        # Category C: Documents, Pages, Calculation, Final Answer

        answer_requirements = {
            "A": """
            document: Include the document required to answer the question in the format: <Company Name> 10-K/Q. Example: Amazon 10-K".
            page: This part should only include a single page number where the answer can be found. For example, 10.
            final_answer: This part should only include the answer to the given question. For example, "274,515 Million" or "Epic Games sued Apple after alleging antitrust behavior". This has to answer the question given by the user and cannot do anything else.
            """,
            "B": """
            document: This part should only include the document that the answer can be found in. For example, "Amazon 10-K" or "Apple 10-Q".
            pages: This part should only include the page number(s) that the answer can be found on. For example: 26, 27. This has to be a number (or multiple) and cannot be anything else or ommitted.
            calculation: This is optional depending on if the question requires a calculation. If it does, this should show the correct calculation for that question's answer. For example, "Current ratio = 152,987 / 176,392".
            final_answer: This part should only include the answer to the given question. For example, "274,515 Million" or "Epic Games sued Apple after alleging antitrust behavior". This has to answer the question given by the user and cannot do anything else.
            """,
            "C": """
            documents: This part should only include the documents that the answer can be found in. For example, "Amazon 10-K, Nvidia 10-K"
            pages: This part should only include the page numbers that the answer can be found on. For example: 
            "
            Amazon: 15, 23
            Nvidia: 23, 31
            "
            This has to be at least a single number for each document required for the answer.
            calculations: This is optional depending on if the question requires a calculation (or multiple). If it does, this should show the correct calculation for that question's answer. For example, 
            "
            Amazon Current ratio = 152,987 / 176,392
            Nvidia Current ratio = 123,456 / 176,392"
            final_answer: This part should only include the final answer to the given question. For example, 
            "
            Amazon Current ratio = 0.87
            Nvidia Current ratio = 1.34
            "
            This has to answer the question given.
            """
        }

        prompt = (
        f"Analyze the answer provided and determine if it follows the requirements of the category? "
        f"The question should follow each metric given "
        f"URL: {(self.url)}"
        f"Category: {(self.category)}"
        f"Question: {(self.question)}"
        f"Answer: {(self.answer)}"
        f"Requirements: {answer_requirements[self.category]}"
        f"Only answer with 'Valid' if the question follows the instructions above and 'Invalid' if it is not. "
        )
        return Validation.ai_assistant("You're a helpful assisstant", prompt)

validation = Validation(
    "https://www.sec.gov/Archives/edgar/data/1045810/000104581025000023/nvda-20250126.htm", 
    "B",
    "What was Nvidia's current ratio in the fourth quarter of 2023?", 
    """"
    Document: Apple 10-K
    Page: N/A
    Expected Answer: 274,515 Million
    """)

url_validity = validation.check_url()
print(f"URL Validity: {url_validity}")
if url_validity == "Valid":
    question_validity = validation.check_question()
    print (f"Question Validity: {validation.check_question()}")
    if question_validity == "Valid":
        answer_validity = validation.check_answer()
        print(f"Answer Validity: {answer_validity}")
        if answer_validity == "Valid":
            print("All Valid")
    
        
#print(f"Answer Validity: {validation.check_answer()}")
