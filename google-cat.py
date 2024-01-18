from cat.mad_hatter.decorators import tool, hook, plugin
from typing import List, Union, Dict
from pydantic import BaseModel
from googlesearch import search

# Settings

default_web_search_threshold = 0.885
default_webpages_to_ingest = 3

class GoogleCatSettings(BaseModel):
    # API key
    required_Web_search_threshold: float = default_web_search_threshold
    required_Webpages_to_ingest: int = default_webpages_to_ingest


# Give your settings schema to the Cat.
@plugin
def settings_schema():
    return GoogleCatSettings.schema()

def google_search_urls(query, url_results):
    
    try:
        search_results = list(search(query, sleep_interval=5, num_results=url_results))
        return search_results
    except Exception as e:
        return []

def browse_the_web(tool_input, cat, get_results=default_webpages_to_ingest):
    
    num_results_to_fetch = get_results
    message = tool_input
    print("Searching google for " + message)
    cat.send_ws_message(content='Searching Google for ' + message, msg_type='chat_token')
    get_search_results = google_search_urls(message, num_results_to_fetch)
    print("Results from google search: " + str(get_search_results))
    cat.send_ws_message(content='Results for <b>' + message + '</b> from Google search:<br>' + str(get_search_results), msg_type='chat')
    cat.send_ws_message(content=f"The first <b>{num_results_to_fetch} URLs</b> will be ingested to the Cat's memory ...", msg_type='chat')

    for i, url in enumerate(get_search_results, start=1):
        if i > num_results_to_fetch:
            break
        try:
            cat.rabbit_hole.ingest_file(cat, url, 400, 100)
            print(str(i) + ". Ingestion of " + url + " Result: Ingested")
            cat.send_ws_message(content=str(i) + '. Ingestion of ' + url + ' Result: <b>Ingested</b>', msg_type='chat')
            
        except Exception as e:
            print(str(i) + ". Ingestion of " + url + " Result: NOT Ingested")
            cat.send_ws_message(content=str(i) + '. Ingestion of ' + url + ' Result: <b>NOT</b> Ingested', msg_type='chat')

    return "Browsing the web has <b>finished</b>."


@hook
def before_cat_reads_message(user_message_json: dict, cat):

    # Load the settings
    settings = cat.mad_hatter.get_plugin().load_settings()
    webpages_to_ingest = settings.get("required_Webpages_to_ingest")
    
    if (webpages_to_ingest == None) or (webpages_to_ingest < 1):
        webpages_to_ingest = default_webpages_to_ingest
    
    message = user_message_json["text"]
    
    if message.endswith('^'):

        message = message[:-1]
        
        result = browse_the_web(message, cat, get_results=webpages_to_ingest)
         
        print("Ingestion of URLs finished. Cheshire cat is thinking on " + message)
        cat.send_ws_message(content=result, msg_type='chat')
        cat.send_ws_message(content='Cheshire cat is thinking on ' + message + ' ...', msg_type='chat_token')
        user_message_json["text"] = message

    return user_message_json
    

@hook(priority=5)
def before_agent_starts(agent_input, cat) -> Union[None, Dict]:
    #cat.recall_relevant_memories_to_working_memory()

    # Load the settings
    settings = cat.mad_hatter.get_plugin().load_settings()
    webpages_to_ingest = settings.get("required_Webpages_to_ingest")
    web_search_threshold = settings.get("required_Web_search_threshold")

    if (webpages_to_ingest == None) or (webpages_to_ingest < 1):
        webpages_to_ingest = default_webpages_to_ingest
    
    if (web_search_threshold is None) or (web_search_threshold < 0) or (web_search_threshold > 1):
        web_search_threshold = default_web_search_threshold

    cat_declarative_memories = cat.working_memory["declarative_memories"]

    def do_the_web_search():
        if len(cat_declarative_memories) == 0:
            declarative_memory_score = str(0)
        else:
            declarative_memory_score = str(cat_declarative_memories[1][1])

        cat.send_ws_message(content='The highest score of the results from the <b>Declarative memory</b> is <b>' + declarative_memory_score + "</b> <br>The Web Search Threshold is set to <b>" + str(web_search_threshold) + "</b> in the Google Cat plugin <b>settings</b>. <br><br><b>Commencing Google Search ...</b>", msg_type='chat')
        cat.send_ws_message(content=browse_the_web(agent_input["input"], cat, get_results=webpages_to_ingest), msg_type='chat')
        cat.recall_relevant_memories_to_working_memory()
        cat.send_ws_message(content='Cheshire cat is thinking on ' + agent_input["input"] + ' ...', msg_type='chat_token')
    
    # Check if the index is in range
    if 0 <= 1 < len(cat_declarative_memories):
        if cat_declarative_memories[1][1] < web_search_threshold:
            do_the_web_search()        
    else:
        do_the_web_search()

    return agent_input
