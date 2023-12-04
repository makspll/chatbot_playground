import datetime
import logging
import time
from typing import Any, Callable
from annotated_types import T
import openai
from openai import OpenAI
import threading

def generate_primary_prompt(user_prompt: str, context_sql: str, context_response: str) -> str:
    """ generates a primary prompt given the user prompt and the context response from the helper AI """
    chat_prompt = f"""
        System Prompt Begin. 
        - A user prompt will be provided below the system prompt,
        and you will need to answer the user prompt as best as you can with the help of the context section.
        - The context contains a valid SQL query that was generated by an AI based on the user prompt earlier.
        - The context section also contains the result of running this query
        - Use the information from the context section to answer the user prompt.
        - If the context section does not contain enough information to properly answer the query, this is not the user's fault.
        - If the context section requires improvements suggest changes to the user prompt to the user based on which this context is generated.
        the columns in order of appearance are: {generate_minimized_schema_prompt()}
        the sql used to generate the response was: 
        ```sql
        {context_sql}
        ```
        and the response was:
         {context_response},
        Context Section End.
        User Prompt Begin. {user_prompt} User Prompt End.

    """

    return chat_prompt

def generate_context_prompt(user_prompt :str, last_output = None, last_sql_result = None) -> str:
    """ embeds the given user prompt in an LLM prompt which will be used to generate a valid SQL query to give context to another AI in answering the prompt"""
    # BEGIN: Generate prompt for chatGPT

    if last_sql_result:
        main_prompt = f"""
            A user prompt will be provided below the system prompt, the below MySQL SQL query was used by you to generate the context for the next model, to answer the user prompt.
            Your job is to decide if the output is valid or not, and if not, then provide a better query.
            The last MySQL query generated by you was:
            ```sql
            {last_output}
            ```
            Which when run on the database gave the following result: `{last_sql_result}`
            - If this value is valid then YOU MUST reply with "VALID" followed by the summary of the query for the next model in maximum two sentences.
            - IF you are satisfied MAKE SURE TO INCLUDE YOUR SUMMARY AND "VALID" in the response.
            - If this value is an error or looks erroneous (or if it's 0 or NULL when expecting a value) then return an improved SQL Query.
        """
    else:
        main_prompt = f"""
            A user prompt will be provided below the system prompt,
            and you will need to provide a valid MySQL SQL query that answers the user prompt.
            Do not output anything other than a valid MySQL SQL query.
            The schema for the database is as follows: 
            ```sql
            {generate_schema_prompt()} 
            ```
        """

    chat_prompt = f"""
        System Prompt Begin. 
        {main_prompt}
        Avoid generating more than 10 rows, try to convey as much information with the least amount of rows.
        Ensure that the query is not biased, do not make assumptions about the data, 
        your query must allow the next AI to answer the user prompt as best as it can with least bias possible.
        If you return any data, label every column with a name, and make sure that the column names are descriptive.
        System Prompt End. 
        User Prompt Begin. {user_prompt} User Prompt End.
    """

    return chat_prompt


def generate_schema_prompt() -> str:
    """ Generates a schema prompt which explains our data to the context AI"""
    schema_prompt = """
        CREATE TABLE user_data (
            ID INT PRIMARY KEY,
            Year_Birth INT NOT NULL, 
            Education VARCHAR(255) NOT NULL, -- customer's level of education
            Marital_Status VARCHAR(255) NOT NULL,
            Income INT, -- customer's yearly household income
            NoOfKidsHome INT NOT NULL, -- number of small children in customer's household
            NoOfTeensHome INT NOT NULL, -- number of teenagers in customer's household
            Dt_Customer DATE NOT NULL, -- date of customer's enrollment with the company
            Recency INT NOT NULL, -- number of days since the last purchase
            MntWines INT NOT NULL, -- amount spent on wine in the last 2 years
            MntFruits INT NOT NULL, -- amount spent on fruits in the last 2 years
            MntMeatProducts INT NOT NULL, -- amount spent on meat in the last 2 years
            MntFishProducts INT NOT NULL, -- amount spent on fish in the last 2 years
            MntSweetProducts INT NOT NULL, -- amount spent on sweets in the last 2 years
            MntGoldProds INT NOT NULL, -- amount spent on gold in the last 2 years
            NumDealsPurchases INT NOT NULL, -- number of purchases made with a discount
            NumWebPurchases INT NOT NULL, -- number of purchases made through the company's web site
            NumCatalogPurchases INT NOT NULL, -- number of purchases made using a catalogue
            NumStorePurchases INT NOT NULL, -- number of purchases made directly in stores
            NumWebVisitsMonth INT NOT NULL, -- number of visits to company's web site in the last month
            AcceptedCmp1 BOOLEAN NOT NULL, -- customer accepted the offer in the 1st campaign
            AcceptedCmp2 BOOLEAN NOT NULL, -- customer accepted the offer in the 2nd campaign
            AcceptedCmp3 BOOLEAN NOT NULL, -- customer accepted the offer in the 3rd campaign
            AcceptedCmp4 BOOLEAN NOT NULL, -- customer accepted the offer in the 4th campaign
            AcceptedCmp5 BOOLEAN NOT NULL, -- customer accepted the offer in the 5th campaign
            Response BOOLEAN NOT NULL, -- customer accepted the offer in the last campaign
            Complain BOOLEAN NOT NULL, -- customer complained in the last 2 years
            Z_CostContact SMALLINT NOT NULL, 
            Z_Revenue SMALLINT NOT NULL
        );
    """
    return schema_prompt

def generate_minimized_schema_prompt() -> str:
    return "ID,Year_Birth,Education,Marital_Status,Income,NoOfKidsHome,NoOfTeensHome,Dt_Customer,Recency,MntWines,MntFruits,MntMeatProducts,MntFishProducts,MntSweetProducts,MntGoldProds,NumDealsPurchases,NumWebPurchases,NumCatalogPurchases,NumStorePurchases,NumWebVisitsMonth,AcceptedCmp1,AcceptedCmp2,AcceptedCmp3,AcceptedCmp4,AcceptedCmp5,Response,Complain,Z_CostContact,Z_Revenue"

class BlockingRateLimiter:
    """ A rate limiter preventing access to the open AI API more than the specified number of times per minute (without sliding window)"""

    lock = threading.Lock()
    last_call_time : datetime.datetime = datetime.datetime.min
    calls_this_minute = 0
    def __init__(self, max_calls_per_minute: int):
        self.max_calls_per_minute = max_calls_per_minute

    def call(self, f: Callable[[OpenAI], T]) -> T:
        BlockingRateLimiter.calls_this_minute += 1
        BlockingRateLimiter.last_call_time = datetime.datetime.now()
        client = OpenAI(max_retries=0)
        return f(client)
        
    def __enter__(self):
        # lock to prevent other flask threads from calling the API too much
        logging.info("Trying to acquire openAI client lock")
        BlockingRateLimiter.lock.acquire(blocking=True, timeout=-1)
        logging.info(f"Last call time: {BlockingRateLimiter.last_call_time}, calls_this_minute: {BlockingRateLimiter.calls_this_minute}")

        while True:
            time_since_last_call = (datetime.datetime.now() - BlockingRateLimiter.last_call_time).seconds
            logging.info(f"Time since last call: {time_since_last_call}s")
            if time_since_last_call >= 60:
                logging.info("A minute passed since last call, resetting counter")
                BlockingRateLimiter.calls_this_minute = 0
            if BlockingRateLimiter.calls_this_minute < self.max_calls_per_minute:
                logging.info("calls_this_minute < self.max_calls_per_minute, entering context")
                break
            sleep_time = 60 - time_since_last_call
            if sleep_time > 0:
                logging.info(f"Sleeping for {sleep_time}s")
                time.sleep(sleep_time)
        return self
     
    def __exit__(self, exception_type, exception_value, exception_traceback):
        logging.info("Releasing openAI client lock")
        BlockingRateLimiter.lock.release()



def call_llm_api(prompt: str) -> str:
    """ Calls the LLM API with the given prompt and returns the response, due to low rate limits,
    throw exceptions if the API was already called 3 times this minute """

    with BlockingRateLimiter(3) as limiter:
        def call(client: OpenAI) -> str:
            logging.info("Calling open AI API for completions")
            raw_output = client.chat.completions.create(
                messages=[  
                    # gpt-3.5 doesn't really care about the system prompt
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="gpt-3.5-turbo",
            )
            return "\n".join([c.message.content for c in raw_output.choices])
        return limiter.call(call)

