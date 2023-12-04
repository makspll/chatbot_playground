from enum import Enum
import logging
import os
import sys
from typing import Optional
from flask import Flask, request, jsonify
from db import create_mysql_connection, run_query_many
from gen import call_llm_api, generate_context_prompt, generate_primary_prompt
from enum import Enum

from dotenv import load_dotenv
from typing import Tuple, Optional


app = Flask(__name__)

# optionally allow env_file arg

load_dotenv(os.environ.get("ENV_FILE", None))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)

file_handler = logging.FileHandler('logs.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)


logger.addHandler(file_handler)
logger.addHandler(stdout_handler)

class ErrorType(Enum):
    VALIDATION_ERROR = 400
    ERROR_GENERATING_ANSWER = 500

class APIException(Exception):
    def __init__(self, error_type: ErrorType, path: Optional[str], message: str):
        self.error_type = error_type
        self.path = path
        self.message = message

@app.errorhandler(APIException)
def handle_custom_exception(error):
    response = jsonify({
        'kind': error.error_type.name,
        'path': error.path,
        'message': error.message
    })
    response.status_code = error.error_type.value
    return response


@app.route('/questions', methods=['POST'])
def handle_questions():
    data = request.get_json()
    question = data.get('question')

    # input validation
    if not question:
        raise APIException(ErrorType.VALIDATION_ERROR, 'question', 'Question is required')
    if len(question) > 200:
        raise APIException(ErrorType.VALIDATION_ERROR, 'question', 'Question must be less than 200 characters')
    
    logging.info('Received question: %s', question)
    sql_generated,sql_output = iterate_sql_gen(question, max_tries=5)     
    primary_prompt = generate_primary_prompt(question, sql_generated, sql_output)
    logging.info('Generated primary prompt: %s', primary_prompt)

    try:
        final_response = call_llm_api(primary_prompt)
    except Exception as E:
        raise APIException(ErrorType.ERROR_GENERATING_ANSWER, None, 'Error calling LLM API, please try again later, we might have hit our free tier rate limit :)')
    logging.info('Model final response: %s', final_response)

    return {
        "response": final_response
    }, 200




def iterate_sql_gen(question: str, max_tries: int = 2) -> Tuple[Optional[str], Optional[str]]:
    sql_generated = None
    sql_output = None
    last_sql_generated = None
    while max_tries > 0:
        logging.info(f"Iterating on the sql generation, leftover tries: {max_tries}")
        context_prompt = generate_context_prompt(question, sql_generated, sql_output)
        logging.info('Generated context prompt: %s', context_prompt)
        
        try:
            logging.info("Calling LLM")
            sql_generated = call_llm_api(context_prompt)
        except Exception as E:
            logging.error(f"Error calling LLM: {E}")
            raise APIException(ErrorType.ERROR_GENERATING_ANSWER, None, 'Error calling LLM API, please try again later, we might have hit our free tier rate limit :)')
        if "valid" in sql_generated.lower():
            logging.info("Model is happy with the result")
            return last_sql_generated, f"Query:{last_sql_generated}, Summary: {sql_generated}, DB Output: {sql_output}"
        
        logging.info("Model Generated SQL: %s", sql_generated)

        try:
            logging.info("Running generated SQL")
            sql_output = run_query_many(sql_generated, 10, create_mysql_connection())
            logging.info("Returned SQL: %s", sql_output)
        except Exception as E:
            sql_output = f"An error happend when running your query: {str(E)}"
            logging.error("Error running SQL: %s", E)
        max_tries -= 1
        last_sql_generated = sql_generated

    return sql_generated, sql_output


if __name__ == '__main__':
    app.run()





