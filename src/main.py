from enum import Enum
import logging
import os
from typing import Optional
from flask import Flask, request, jsonify
from db import create_mysql_connection, run_query_many
from gen import call_llm_api, generate_context_prompt, generate_primary_prompt
from enum import Enum

from dotenv import load_dotenv
load_dotenv()

log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
numeric_level = getattr(logging, log_level, None)
if not isinstance(numeric_level, int):
    raise ValueError(f'Invalid log level: {log_level}')
logging.basicConfig(level=numeric_level)

app = Flask(__name__)

class ErrorType(Enum):
    VALIDATION_ERROR = 400

class APIException(Exception):
    def __init__(self, error_type: ErrorType, path: Optional[str], message: str):
        self.error_type = error_type
        self.path = path
        self.message = message



class AppState:
    mysql_connection = create_mysql_connection()


@app.route('/questions', methods=['POST'])
def handle_questions():
    data = request.get_json()
    question = data.get('question')

    # input validation
    if not question:
        raise APIException(ErrorType.VALIDATION_ERROR, 'question', 'Question is required')

    logging.info('Received question: %s', question)
    context_prompt = generate_context_prompt(question)
    logging.info('Generated context prompt: %s', context_prompt)
    
    sql_generated = call_llm_api(context_prompt)
    logging.info("Model Generated SQL: %s", sql_generated)

    sql_output = "<error>"
    try:
        sql_output = run_query_many(sql_generated, 50, AppState.mysql_connection)
        logging.info("Returned SQL: %s", sql_output)
    except Exception as E:
        logging.error("Error running SQL: %s", E)
        # TODO: give the error back to the AI and let it fix it once, then try again
        return {
            "response": "Sorry, I couldn't understand your question. Please try again."
        }, 200
       
    primary_prompt = generate_primary_prompt(question, sql_generated, sql_output)
    logging.info('Generated primary prompt: %s', primary_prompt)

    final_response = call_llm_api(primary_prompt)
    logging.info('Model final response: %s', final_response)

    return {
        "response": final_response
    }, 200


@app.errorhandler(APIException)
def handle_custom_exception(error):
    response = jsonify({
        'kind': error.error_type.name,
        'path': error.path,
        'message': error.message
    })
    response.status_code = error.error_type.value
    return response

if __name__ == '__main__':
    app.run()




