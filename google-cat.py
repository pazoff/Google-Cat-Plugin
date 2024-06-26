from cat.mad_hatter.decorators import tool, hook, plugin
from typing import List, Union, Dict
from pydantic import BaseModel
from googlesearch import search
from cat.log import log
import threading
import requests
import json

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

# Function to perform a Google search and return a list of formatted URLs
def google_search_urls(query, url_results):
    try:
        search_results = list(search(query, sleep_interval=5, num_results=url_results))
        return search_results
    except Exception as e:
        log.error(f"Search error: {e}")
        return []

def get_title_from_url(url):
    """
    Get the title from the provided URL.

    Args:
        url (str): The URL from which to extract the title.

    Returns:
        str: The extracted title, or "" if the title tag is not found or if there's an error.
    """
    try:
        response = requests.get(url)
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Find the index of <title> tag
            start_index = response.text.find('<title>')
            end_index = response.text.find('</title>')
            # Extract the title from the HTML
            if start_index != -1 and end_index != -1:
                title = response.text[start_index + len('<title>'):end_index]
                return title.strip()
            else:
                log.warning(f"Title tag not found in the HTML content of {url}.")
                return ""
        else:
            log.error(f"Failed to fetch {url}. Status code:", response.status_code)
            return ""
    except Exception as e:
        log.error(f"An error occurred processing the URL({url}):", e)
        return ""

# Function to browse the web based on a search query
def browse_the_web(tool_input, cat, get_results=default_webpages_to_ingest):
    """
    Function to browse the web and ingest URLs in the background.

    Parameters:
    - tool_input: input message for the search
    - cat: instance of the Cat class
    - get_results: number of webpages to ingest (default value provided)

    Returns:
    - A message indicating the completion of browsing the web
    """
    
    # Function to ingest a single URL in the background
    def ingest_url(cat, url, url_index):
        """
        Ingests a URL and logs the result. 

        Args:
            cat: The category of the URL.
            url: The URL to be ingested.
            url_index: The index of the URL.

        Returns:
            None
        """
        try:
            cat.rabbit_hole.ingest_file(cat, url, 400, 100)
            #log.warning(f"{url_index}.URL: {url} - Ingested successfully.")
            url_title = get_title_from_url(url)
            cat.send_ws_message(content=f'<b>{url_index}. {url_title}</b> - URL: ' + url + ' - Ingested successfully.', msg_type='chat')
            #cat.send_ws_message(content=f'Ingesting URLs ...', msg_type='chat_token')
        except Exception as e:
            #log.error(f"URL not ingested:{url} - Error: {e}")
            print(f"ERROR: URL not ingested:{url} - ", e)
            #cat.send_ws_message(content='URL: ' + url + ' - <b>NOT</b> Ingested', msg_type='chat')
        
    
    num_results_to_fetch = get_results
    message = tool_input
    
    # Print and send messages about the ongoing search
    log.warning(f"Searching google for {message}")
    cat.send_ws_message(content='Searching Google for ' + message, msg_type='chat_token')
    
    # Perform the Google search and get results
    get_search_results = google_search_urls(message, num_results_to_fetch)
    results_from_google_search = [f"{i + 1}. {url}" for i, url in enumerate(get_search_results)]
    
    # Print and send messages about the search results
    formatted_results_message = "<br>".join(results_from_google_search)
    info_message = (
        f"Results for <b>{message}</b> from Google search:<br>{formatted_results_message}<br><br>"
        f"The first <b>{num_results_to_fetch} URLs</b> will be ingested to the Cat's memory."
    )
    cat.send_ws_message(content=info_message, msg_type='chat')

    # Create a list to store the ingestion threads
    ingestion_threads = []

    # Iterate over the search results and ingest them into Cat's memory in the background
    cat.send_ws_message(content=f'Ingesting URLs ...', msg_type='chat_token')
    for i, url in enumerate(get_search_results, start=1):
        if i > num_results_to_fetch:
            break
        
        # Create a new thread for each URL ingestion
        t = threading.Thread(target=ingest_url, args=(cat, url, i))
        
        # Start the thread
        t.start()
        
        # Add the thread to the list
        ingestion_threads.append(t)

    # Join all the threads to wait for all URLs to be ingested
    for t in ingestion_threads:
        t.join()
    
    cat.send_ws_message(content=f'Google Cat: Browsing the web has <b>finished</b>.', msg_type='chat')

    return "Google Cat: Browsing the web has <b>finished</b>."



# Function for automatic web search based on settings
def automatic_web_search(search_term, cat):
    """
    Perform an automatic web search based on the given search term and settings.

    Parameters:
    - search_term: the term to be searched
    - cat: the category for the search

    Returns:
    - False if the search term ends with '*', else True if the automatic web search is performed successfully, else False
    """
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
        f"The Web Search Threshold is set to <b>{str(web_search_threshold)}</b> in the Google Cat plugin <b>settings</b>."
        )
        cat.send_ws_message(content='Google Cat Automatic Web Search', msg_type='chat')
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
    cat.send_ws_message(content='Google Cat Web Search', msg_type='chat')
    browse_the_web(u_message, cat, get_results=webpages_to_ingest)


def check_plugin_version():
    """
    Check the plugin version by reading the local plugin.json file and fetching the GitHub plugin.json file. 
    Compare the versions and return a message if a new version is available. 
    Return False if there is an error during the process.
    """
    try:
        # Read local plugin.json file
        with open('/app/cat/plugins/google-cat/plugin.json', 'r') as file:
            local_data = json.load(file)

        # Extract version from local data
        local_version = local_data.get('version')

        # Fetch GitHub plugin.json file
        github_url = 'https://raw.githubusercontent.com/pazoff/Google-Cat-Plugin/main/plugin.json'
        github_response = requests.get(github_url)

        # Check if GitHub request was successful
        github_response.raise_for_status()

        # Parse GitHub response
        github_data = github_response.json()
        github_version = github_data.get('version')

        # Compare versions
        if github_version and local_version != github_version:
            return f"<br>* A new version ({github_version}) of Google Cat is available. You have version {local_version}.<br>- https://github.com/pazoff/Google-Cat-Plugin"
        else:
            return False

    except requests.RequestException as e:
        #return f"Error: {str(e)}"
        return False
    except json.JSONDecodeError as e:
        #return f"Error decoding JSON: {str(e)}"
        return False
    except Exception as e:
        #return f"An unexpected error occurred: {str(e)}"
        return False


@hook(priority=5)
def agent_fast_reply(fast_reply, cat):
    #return_direct = True

    # Get user message from the working memory
    message = cat.working_memory["user_message_json"]["text"]
    
    # Check if the message ends with '^' to trigger manual web search
    if message.endswith('^'):
        # Remove '^' and perform manual web search
        message = message[:-1]
        
        #manual_web_search(message, cat)
        search_tr = threading.Thread(target=manual_web_search, args=(message, cat))
        search_tr.start()
        
        #info_message = "Google Cat web search has <b>finished</b>. You can continue using the Cat ..."
        #info_message = "Google Cat manual web search has <b>finished</b>."
        info_message = "Google Cat manual web search working in the background."
        
        version_check = check_plugin_version()
        if version_check:
            info_message = info_message + "<br>" + version_check
        
        log.warning(info_message)
        # cat.recall_relevant_memories_to_working_memory(query=message)
        # cat.send_ws_message(content=info_message, msg_type='chat')
        # cat.send_ws_message(content=f'The Cat is Thinking on {message}', msg_type='chat_token')
        return {"output": info_message}
    else:
        # Perform automatic web search
        if automatic_web_search(message, cat):
            cat.recall_relevant_memories_to_working_memory(query=message)
            cat.send_ws_message(content=f'Google Cat automatic web search has <b>finished</b>.', msg_type='chat')
            cat.send_ws_message(content=f'The Cat is Thinking on {message}', msg_type='chat_token')
            #return {"output": "Google Cat automatic web search has <b>finished</b>. You can continue using the Cat ..."}

    return fast_reply


# @tool(return_direct=False)
# def search_the_internet(tool_input, cat):
#     """Use only if the tool_input contains the term search or internet. Input is a string."""

#     manual_web_search(tool_input, cat)
#     cat.recall_relevant_memories_to_working_memory(query=tool_input)
