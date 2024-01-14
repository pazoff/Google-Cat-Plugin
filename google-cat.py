from cat.mad_hatter.decorators import tool, hook, plugin
from googlesearch import search


def google_search_urls(query, num_results=3):
    
    try:
        search_results = list(search(query, sleep_interval=1, num_results=num_results))
        return search_results
    except Exception as e:
        return []



@hook
def before_cat_reads_message(user_message_json: dict, cat):
    
    message = user_message_json["text"]
    
    if message.endswith('^'):

     num_results_to_fetch = 3
     message = message[:-1]
     print("Searching google for " + message)
     cat.send_ws_message(content='Searching Google for <b>' + message + '</b> ...', msg_type='chat')
     get_search_results = google_search_urls(message, num_results_to_fetch)
     print("Results from google search: " + str(get_search_results))
     cat.send_ws_message(content='Results for <b>' + message + '</b> from Google search:<br>' + str(get_search_results), msg_type='chat')
     
     ingest_result = ""
     for i, url in enumerate(get_search_results, start=1):
        try:
            ingest_result = cat.rabbit_hole.ingest_file(cat, url, 400, 100)
            print(str(i) + ". Ingestion of " + url + " Result: Ingested")
            cat.send_ws_message(content=str(i) + '. Ingestion of ' + url + ' Result: <b>Ingested</b>', msg_type='chat')
            
        except Exception as e:
            print(str(i) + ". Ingestion of " + url + " Result: NOT Ingested")
            cat.send_ws_message(content=str(i) + '. Ingestion of ' + url + ' Result: <b>NOT</b> Ingested', msg_type='chat')

     
     
     user_message_json["text"] = message
     
     print("Ingestion of URLs finished. Cheshire cat is thinking on " + message)
     cat.send_ws_message(content='Ingestion of new data from Google search has finished.', msg_type='chat')
     cat.send_ws_message(content='Cheshire cat is thinking on <b>' + message + '</b> ...', msg_type='chat')

    
    return user_message_json


