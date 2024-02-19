# elasticsearch_handler.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

from elasticsearch import Elasticsearch, ElasticsearchWarning
import warnings
import logging

# Suppress Elasticsearch warnings
warnings.filterwarnings("ignore", category=ElasticsearchWarning)

# Add the necessary import at the top of your Elasticsearch handler file
from api_perplexity_search import query_perplexity  # Adjust the import path as necessary

async def search_es_for_context(search_terms):
    es = Elasticsearch(["http://localhost:9200"])
    if not es.ping():
        logging.error("Could not connect to Elasticsearch.")
        return None

    index = "tg-bot-rag-index"
    query = {
        "size": 1,  # Focus on the top hit
        "query": {
            "multi_match": {
                "query": search_terms,
                "fields": ["question^2", "answer"],  # Boosting questions for relevance
            }
        },
        "_source": ["question", "answer"],
    }

    response = es.search(index=index, body=query)
    if response['hits']['hits']:
        hit = response['hits']['hits'][0]
        question = hit["_source"]["question"]
        answer = hit["_source"]["answer"]
        # Format for model context
        context_entry = f"Q: {question}\nA: {answer}"
        return context_entry
    else:
        return None
