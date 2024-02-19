# elasticsearch_test_search.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

from elasticsearch import Elasticsearch

# Function to search Elasticsearch
def search_es(es, index, field, search_term):
    query = {
        "query": {
            "bool": {
                "should": [
                    {"match_phrase": {field: {"query": search_term, "slop": 50}}},
                    {"match": {field: {"query": search_term, "operator": "or"}}}
                ]
            }
        },
        "highlight": {
            "fields": {
                field: {
                    "fragment_size": 200,
                    "number_of_fragments": 5,
                    "max_analyzed_offset": 1000000  # Adjust this value as needed
                }
            },
            "pre_tags": ["["],
            "post_tags": ["]"]
        }
    }
    response = es.search(index=index, body=query, size=10)
    return response

# Connect to Elasticsearch
es = Elasticsearch(["http://localhost:9200"])

# Check the connection
if es.ping():
    print("Connected to Elasticsearch!")
else:
    print("Could not connect to Elasticsearch.")
    exit(1)

# Ask user for search term
search_term = input("Enter search term: ")

# Define the index and field to search on
index = "tg-bot-rag-index"  # Replace with your index
field = "content"  # Replace with the field you want to search

# Perform the search
result = search_es(es, index, field, search_term)

# Print the search results
print("Search Results:")
for hit in result['hits']['hits']:
    # print("Document ID:", hit["_id"])
    # print("Score:", hit["_score"])  # Optional: Display the relevance score
    if "highlight" in hit:
        print("Highlighted Snippets:")
        for highlight in hit["highlight"][field]:
            print(highlight)
    print("---\n")