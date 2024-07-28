# elasticsearch_handler.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

relevance_threshold = 19.5

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

    # Adjust the search_terms to use only the first line or a set number of characters
    search_terms_adjusted = search_terms.split('\n', 1)[0][:256]  # Adjust 256 to your needs

    query = {
        "size": 1,  # Focus on the top hit
        "query": {
            "multi_match": {
                # "query": search_terms,
                "query": search_terms_adjusted,
                "fields": ["question^2", "answer"],  # Boosting questions for relevance
                "type": "best_fields"  # Can also experiment with other types like "most_fields" or "cross_fields"
            }
        },
        "_source": ["question", "answer"],
    }

    response = es.search(index=index, body=query)
    if response['hits']['hits']:
        hit = response['hits']['hits'][0]
        score = hit['_score']  # Extract the score of the hit
        
        # Log every score for monitoring and tuning purposes
        # logging.info(f"Search term: '{search_terms}' | Score: {score} | Threshold: {relevance_threshold}")

        # Check if the score exceeds the relevance threshold
        if score > relevance_threshold:
            question = hit["_source"]["question"]
            answer = hit["_source"]["answer"]
            # Format for model context
            context_entry = f"{answer}"
            logging.info(f"Result above relevance threshold: {relevance_threshold}. Included in context: {context_entry}")
            return context_entry
        else:
            logging.info(f"Result below relevance threshold (score: {score}, threshold: {relevance_threshold}).")
            return None
    else:
        return None

    """ response = es.search(index=index, body=query)
    if response['hits']['hits']:
        hit = response['hits']['hits'][0]
        question = hit["_source"]["question"]
        answer = hit["_source"]["answer"]
        # Format for model context
        context_entry = f"Q: {question}\nA: {answer}"
        return context_entry
    else:
        return None """
