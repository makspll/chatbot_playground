# Architecture

- user asks query
- query is run through first LLM prompt which generates context via valid SQL query
- query is improved by running the query and putting the SQL return values with the built query into another prompt for another LLM pass, where the model is asked to either fix any errors or improve the query
- this is done untill MAX_TRIES or the model returns something containing "valid"
- the output + query + user query are used combined into primary prompt which then generates the final response to the user

Pros:
- Great against hallucinations on the dataset
- Does not require fine-tuning, can be used with any LLM
- May not require as powerful of an LLM for the primary prompt

Cons:
- Cannot be used with sensitive data in the DB, basically assume users have full read only access to it
- Requires many LLM passes for good quality responses and can potentially cost a lot on expensive models
- Still requires pretty good LLM for the SQL gen + reflection.
- Pretty slow


# Usage

## Development
- needs an .env file in the root directory:
    ```bash
    MYSQL_ROOT_PASSWORD=pass
    MYSQL_DATABASE=prompt_db
    DB_HOST=localhost
    DB_USERNAME=user
    DB_PASSWORD=pass
    OPENAI_API_KEY=
    ```
- Run the SQL container using `docker compose up`
- The local DB requires user-login.txt and user-pass.txt in the root directory (same one as in .env file)

## Prod
Use gunicorn with `main:app` set timeout to high and pass ENV_FILE environment variable pointing to your .env file

