from cat.mad_hatter.decorators import tool, hook, plugin
from typing import List, Union, Dict
from pydantic import BaseModel
from googlesearch import search

# Settings

# Default values for web search threshold and webpages to ingest
default_web_search_threshold = 0.5
default_webpages_to_ingest = 3

# Define a Pydantic model for Google Cat settings
class GoogleCatSettings(BaseModel):
    auto_web_search: bool = True
    required_Web_search_threshold: float = default_web_search_threshold
    required_Webpages_to_ingest: int = default_webpages_to_ingest

# Give your settings schema to the Cat.
@plugin
def settings_schema():
    return GoogleCatSettings.schema()

# Function to perform a Google search and return a list of URLs
def google_search_urls(query, url_results):
    try:
        search_results = list(search(query, sleep_interval=5, num_results=url_results))
        return search_results
    except Exception as e:
        return []

# Function to browse the web based on a search query
def browse_the_web(tool_input, cat, get_results=default_webpages_to_ingest):
    num_results_to_fetch = get_results
    message = tool_input
    
    # Print and send messages about the ongoing search
    print("Searching google for " + message)
    cat.send_ws_message(content='Searching Google for ' + message, msg_type='chat_token')
    
    # Perform the Google search and get results
    get_search_results = google_search_urls(message, num_results_to_fetch)
    
    # Print and send messages about the search results
    print("Results from google search: " + str(get_search_results))
    cat.send_ws_message(content='Results for <b>' + message + '</b> from Google search:<br>' + str(get_search_results), msg_type='chat')
    cat.send_ws_message(content=f"The first <b>{num_results_to_fetch} URLs</b> will be ingested to the Cat's memory ...", msg_type='chat')

    # Iterate over the search results and ingest them into Cat's memory
    for i, url in enumerate(get_search_results, start=1):
        if i > num_results_to_fetch:
            break
        try:
            cat.send_ws_message('The Cat is ingesting ' + url + ' ...', msg_type='chat_token')
            cat.rabbit_hole.ingest_file(cat, url, 400, 100)
            print(str(i) + ". Ingestion of " + url + " Result: Ingested")
            cat.send_ws_message(content=str(i) + '. Ingestion of ' + url + ' Result: <b>Ingested</b>', msg_type='chat')
        except Exception as e:
            print(str(i) + ". Ingestion of " + url + " Result: NOT Ingested")
            cat.send_ws_message(content=str(i) + '. Ingestion of ' + url + ' Result: <b>NOT</b> Ingested', msg_type='chat')

    return "Browsing the web has <b>finished</b>."

# Function for automatic web search based on settings
def automatic_web_search(search_term, cat):
    if search_term.endswith('*'):
        return 

    # Load settings
    settings = cat.mad_hatter.get_plugin().load_settings()
    auto_web_search = settings.get("auto_web_search")
    webpages_to_ingest = settings.get("required_Webpages_to_ingest")
    web_search_threshold = settings.get("required_Web_search_threshold")

    # Set default values if not provided
    if auto_web_search is None:
        auto_web_search = True

    # Return if automatic web search is disabled
    if auto_web_search is False:
        return

    # Set default values for missing or invalid settings
    if (webpages_to_ingest is None) or (webpages_to_ingest < 1):
        webpages_to_ingest = default_webpages_to_ingest
    
    if (web_search_threshold is None) or (web_search_threshold < 0) or (web_search_threshold > 1):
        web_search_threshold = default_web_search_threshold

    cat_declarative_memories = cat.working_memory["declarative_memories"]

    def do_the_web_search():
        # Determine the declarative memory score
        if len(cat_declarative_memories) == 0:
            declarative_memory_score = str(0)
        else:
            declarative_memory_score = str(cat_declarative_memories[1][1])

        # Send messages about starting the web search
        cat.send_ws_message(content='The highest score of the results from the <b>Declarative memory</b> is <b>' + declarative_memory_score + "</b> <br>The Web Search Threshold is set to <b>" + str(web_search_threshold) + "</b> in the Google Cat plugin <b>settings</b>. <br><br><b>Commencing Google Search ...</b>", msg_type='chat')
        
        # Initiate web search and update Cat's memory
        cat.send_ws_message(content=browse_the_web(search_term, cat, get_results=webpages_to_ingest), msg_type='chat')
        cat.recall_relevant_memories_to_working_memory()
        cat.send_ws_message(content='Cheshire cat is thinking on ' + search_term + ' ...', msg_type='chat_token')
    
    # Check if the index is in range and if the web search should be performed
    if 0 <= 1 < len(cat_declarative_memories):
        if cat_declarative_memories[1][1] < web_search_threshold:
            do_the_web_search()        
    else:
        do_the_web_search()

# Function for manual web search
def manual_web_search(u_message, cat):
    # Load settings
    settings = cat.mad_hatter.get_plugin().load_settings()
    webpages_to_ingest = settings.get("required_Webpages_to_ingest")
    
    # Set default value for missing or invalid setting
    if (webpages_to_ingest is None) or (webpages_to_ingest < 1):
        webpages_to_ingest = default_webpages_to_ingest

    # Perform manual web search and update Cat's memory
    result = browse_the_web(u_message, cat, get_results=webpages_to_ingest)
    
    # Print and send messages about the finished ingestion
    print("Ingestion of URLs finished. Cheshire cat is thinking on " + u_message)
    cat.send_ws_message(content=result, msg_type='chat')
    cat.send_ws_message(content='Cheshire cat is thinking on ' + u_message + ' ...', msg_type='chat_token')
        
    cat.recall_relevant_memories_to_working_memory()

# Hook function executed before Cat reads a message
@hook
def before_cat_reads_message(user_message_json: dict, cat):
    message = user_message_json["text"]
    
    # Check if the message ends with '^' to trigger manual web search
    if message.endswith('^'):
        # Remove '^' and perform manual web search
        message = message[:-1]
        manual_web_search(message, cat)
        user_message_json["text"] = message
    else:
        # Perform automatic web search
        automatic_web_search(message, cat)

    return user_message_json
