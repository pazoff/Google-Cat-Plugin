from cat.mad_hatter.decorators import tool, hook, plugin
from googlesearch import search
import time


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
     cat.send_ws_message(content='Searching Google for ' + message, msg_type='chat')
     get_search_results = google_search_urls(message, num_results_to_fetch)
     print("Results from google search: " + str(get_search_results))
     cat.send_ws_message(content='Results for ' + message + ' from Google search:<br>' + str(get_search_results), msg_type='chat')
     
     ingest_result = ""
     for i, url in enumerate(get_search_results, start=1):
        try:
            ingest_result = cat.rabbit_hole.ingest_file(cat, url, 400, 100)
            cat.send_ws_message(content=str(i) + '. Ingestion of ' + url + ' Result: OK', msg_type='chat')
            time.sleep(1)
        except Exception as e:
            pass
            #cat.send_ws_message(content='ERROR: ' + url + ' The error is: ' + str(e), msg_type='chat')

     
     time.sleep(1)
     user_message_json["text"] = message

    
    return user_message_json
