# elasticsearch_backend_search.py

from elasticsearch import Elasticsearch

# Function to search Elasticsearch
def search_es(es, index, field, search_term):
    query = {
        "query": {
            "wildcard": {
                field: f"*{search_term}*"
            }
        },
        "size": 5
    }
    response = es.search(index=index, body=query)
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
index = "tg-bot-rag-index"  # Replace with your index name
field = "content"  # Replace with the field you want to search

# Perform the search
result = search_es(es, index, field, search_term)

# Print the search results in a Discord-friendly format
print("Search Results:")
for hit in result['hits']['hits']:
    print(f"Document ID: {hit['_id']}\nSnippet: {hit['_source'][field][:200]}...")  # Print the first 200 characters
    print("---")