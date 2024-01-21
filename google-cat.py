from cat.mad_hatter.decorators import tool, hook, plugin
from typing import List, Union, Dict
from pydantic import BaseModel
from googlesearch import search
import threading

# Settings

# Default values for web search threshold and webpages to ingest
default_web_search_threshold = 0.5
default_webpages_to_ingest = 3


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
    
    # Function to ingest a single URL in the background
    def ingest_url(cat, url):
        try:
            cat.rabbit_hole.ingest_file(cat, url, 400, 100)
            print(url + " Result: Ingested")
            #cat.send_ws_message(content=url + ' Result: <b>Ingested</b>', msg_type='chat')
        except Exception as e:
            print(url + " Result: NOT Ingested")
            #cat.send_ws_message(content=url + ' Result: <b>NOT</b> Ingested', msg_type='chat')
        
    
    num_results_to_fetch = get_results
    message = tool_input
    
    # Print and send messages about the ongoing search
    print("Searching google for " + message)
    cat.send_ws_message(content='Searching Google for ' + message, msg_type='chat_token')
    
    # Perform the Google search and get results
    get_search_results = google_search_urls(message, num_results_to_fetch)
    
    # Print and send messages about the search results
    results_from_google_search = str(get_search_results)
    results_from_google_search = results_from_google_search[1:-1]
    print(f"Results from google search: {results_from_google_search}")
    cat.send_ws_message(content='Results for <b>' + message + '</b> from Google search:<br>' + results_from_google_search, msg_type='chat')
    cat.send_ws_message(content=f"The first <b>{num_results_to_fetch} URLs</b> will be ingested to the Cat's memory in the background ...", msg_type='chat')

    # Create a list to store the ingestion threads
    #ingestion_threads = []

    # Iterate over the search results and ingest them into Cat's memory in the background
    for i, url in enumerate(get_search_results, start=1):
        if i > num_results_to_fetch:
            break
        
        # Create a new thread for each URL ingestion
        t = threading.Thread(target=ingest_url, args=(cat, url))
        
        # Start the thread
        t.start()
        
        # Add the thread to the list
        #ingestion_threads.append(t)

    # Join all the threads to wait for all URLs to be ingested
    #for t in ingestion_threads:
        #t.join()

    return "Browsing the web has <b>finished</b>."



# Function for automatic web search based on settings
def automatic_web_search(search_term, cat):
    if search_term.endswith('*'):
        return False

    # Load settings
    settings = cat.mad_hatter.get_plugin().load_settings()
    auto_web_search = settings.get("auto_web_search")
    webpages_to_ingest = settings.get("required_Webpages_to_ingest")
    web_search_threshold = settings.get("required_Web_search_threshold")
    search_done = False

    # Set default values if not provided
    if auto_web_search is None:
        auto_web_search = True

    # Return if automatic web search is disabled
    if auto_web_search is False:
        return False

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
        info_message = (
        "The highest score of the results from the <b>Declarative memory</b> is "
        f"<b>{declarative_memory_score}</b><br>"
        f"The Web Search Threshold is set to <b>{str(web_search_threshold)}</b> in the Google Cat plugin <b>settings</b>. "
        "<br><br>"
        "<b>Commencing Google Search ...</b>"
        )

        cat.send_ws_message(content=info_message, msg_type='chat')
        
        # Initiate web search
        browse_the_web(search_term, cat, get_results=webpages_to_ingest)
        return True

    
    # Check if the index is in range and if the web search should be performed
    if 0 <= 1 < len(cat_declarative_memories):
        if cat_declarative_memories[1][1] < web_search_threshold:
            search_done = do_the_web_search()        
    else:
        search_done = do_the_web_search()

    return search_done

# Function for manual web search
def manual_web_search(u_message, cat):
    # Load settings
    settings = cat.mad_hatter.get_plugin().load_settings()
    webpages_to_ingest = settings.get("required_Webpages_to_ingest")
    
    # Set default value for missing or invalid setting
    if (webpages_to_ingest is None) or (webpages_to_ingest < 1):
        webpages_to_ingest = default_webpages_to_ingest

    # Perform manual web search
    browse_the_web(u_message, cat, get_results=webpages_to_ingest)

@hook(priority=5)
def agent_fast_reply(fast_reply, cat):
    return_direct = True

    # Get user message from the working memory
    message = cat.working_memory["user_message_json"]["text"]
    
    # Check if the message ends with '^' to trigger manual web search
    if message.endswith('^'):
        # Remove '^' and perform manual web search
        message = message[:-1]
        manual_web_search(message, cat)
        print("Google Cat manual web search has finished. You can continue using the Cat ...")
        return {"output": "Google Cat manual web search has <b>finished</b>. You can continue using the Cat ..."}
    else:
        # Perform automatic web search
        if automatic_web_search(message, cat):
            return {"output": "Google Cat automatic web search has <b>finished</b>. You can continue using the Cat ..."}

    return None
