# backup_database.py
# backup database into a json dump (recommended!)

import json
from elasticsearch import Elasticsearch, helpers
from datetime import datetime

# Connect to Elasticsearch
es = Elasticsearch(["http://localhost:9200"])
index_name = 'tg-bot-rag-index'

def backup_current_state(es, index_name):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f'current_backup_{timestamp}.json'
    
    query = {
        "query": {
            "match_all": {}
        },
        "size": 10000
    }
    
    response = es.search(index=index_name, body=query, scroll='2m')
    scroll_id = response['_scroll_id']
    hits = response['hits']['hits']
    
    all_hits = []
    all_hits.extend(hits)
    
    while len(hits) > 0:
        response = es.scroll(scroll_id=scroll_id, scroll='2m')
        scroll_id = response['_scroll_id']
        hits = response['hits']['hits']
        all_hits.extend(hits)
    
    # Collect all documents into a list
    all_documents = [hit["_source"] for hit in all_hits]
    
    # Write the list of documents to the backup file
    with open(backup_file, 'w', encoding='utf-8', errors='replace') as f:
        json.dump(all_documents, f, ensure_ascii=False, indent=4)
    
    print(f"Backup completed to {backup_file}")

backup_current_state(es, index_name)
