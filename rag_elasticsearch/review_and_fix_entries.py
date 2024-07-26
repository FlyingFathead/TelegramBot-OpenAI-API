# review_and_fix_entries.py

import json
from elasticsearch import Elasticsearch, helpers

# Configuration
es = Elasticsearch(["http://localhost:9200"])
index_name = 'tg-bot-rag-index'
problematic_answer = "<[get_defcon_status]>"
backup_file = 'backup_before_correction.json'

def fetch_problematic_entries(es, index_name, problematic_answer):
    query = {
        "query": {
            "match": {
                "answer": problematic_answer
            }
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
    
    return all_hits

def save_backup(entries, backup_file):
    with open(backup_file, 'w', encoding='utf-8', errors='replace') as f:
        json.dump(entries, f, ensure_ascii=False, indent=4)
    print(f"Backup completed to {backup_file}")

def review_and_fix_entries(entries):
    corrected_entries = []
    index = 0

    while index < len(entries):
        entry = entries[index]
        print(f"\nQuestion: {entry['_source']['question']}")
        print(f"Answer: {entry['_source']['answer']}")
        action = input("Enter action (n = next, p = previous, s = skip, e = edit, d = delete): ").strip().lower()
        
        if action == 'e':
            new_answer = input("Enter the new answer: ").strip()
            entry['_source']['answer'] = new_answer
            corrected_entries.append(entry)
            print("Entry updated.")
            index += 1
        elif action == 's':
            index += 1
        elif action == 'd':
            confirm_delete = input("Are you sure you want to delete this entry? (y/n): ").strip().lower()
            if confirm_delete == 'y':
                entry['_source'] = None  # Mark for deletion
                corrected_entries.append(entry)
                print("Entry marked for deletion.")
            index += 1
        elif action == 'p':
            if index > 0:
                index -= 1
            else:
                print("You are at the first entry.")
        elif action == 'n':
            index += 1
        else:
            print("Invalid action. Please use n, p, s, e, or d.")

    return corrected_entries

def apply_corrections(es, index_name, entries):
    actions = []
    for entry in entries:
        if entry['_source'] is None:
            actions.append({
                "_op_type": "delete",
                "_index": index_name,
                "_id": entry['_id']
            })
        else:
            actions.append({
                "_op_type": "index",
                "_index": index_name,
                "_id": entry['_id'],
                "_source": entry['_source']
            })
    
    helpers.bulk(es, actions)
    print(f"Applied corrections to {len(entries)} entries in '{index_name}'.")

# Fetch problematic entries
problematic_entries = fetch_problematic_entries(es, index_name, problematic_answer)

# Save backup of problematic entries
save_backup(problematic_entries, backup_file)

# Review and fix entries
corrected_entries = review_and_fix_entries(problematic_entries)

# Apply corrections to Elasticsearch
apply_corrections(es, index_name, corrected_entries)
