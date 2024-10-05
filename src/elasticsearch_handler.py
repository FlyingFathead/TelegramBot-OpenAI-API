# elasticsearch_handler.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

relevance_threshold = 19.5

import warnings
import logging

# Suppress Elasticsearch warnings
from elasticsearch import ElasticsearchWarning
warnings.filterwarnings("ignore", category=ElasticsearchWarning)

# Initialize the logger for this module
logger = logging.getLogger('TelegramBotLogger')  # Ensure this logger is configured in main.py

# Function to get Elasticsearch client
def get_elasticsearch_client(config):
    try:
        from elasticsearch import Elasticsearch
    except ImportError:
        logger.error("❌ 'elasticsearch' module not found. Please install it using 'pip install elasticsearch'.")
        return None

    try:
        es_host = config.get('Elasticsearch', 'ELASTICSEARCH_HOST', fallback='localhost').strip("'\"")
        es_port = config.getint('Elasticsearch', 'ELASTICSEARCH_PORT', fallback=9200)
        es_scheme = config.get('Elasticsearch', 'ELASTICSEARCH_SCHEME', fallback='http').strip("'\"")  # Add scheme
        es_username = config.get('Elasticsearch', 'ELASTICSEARCH_USERNAME', fallback=None)
        es_password = config.get('Elasticsearch', 'ELASTICSEARCH_PASSWORD', fallback=None)

        # Log the configuration being used
        logger.info(f"Elasticsearch Configurations: Host={es_host}, Port={es_port}, Scheme={es_scheme}, Username={'***' if es_username else 'None'}")

        es = Elasticsearch(
            hosts=[{'host': es_host, 'port': es_port, 'scheme': es_scheme}],  # Include 'scheme'
            http_auth=(es_username, es_password) if es_username and es_password else None,
            timeout=5
        )
        return es
    except Exception as e:
        logger.error(f"❌ Error initializing Elasticsearch client: {e}")
        return None

async def search_es_for_context(search_terms, config):
    es = get_elasticsearch_client(config)
    if es is None:
        logger.warning("⚠️ Elasticsearch client is not available. Skipping search.")
        return None

    if not es.ping():
        logger.warning("⚠️ Elasticsearch is enabled but not reachable.")
        return None

    index = "tg-bot-rag-index"

    # Adjust the search_terms to use only the first line or a set number of characters
    search_terms_adjusted = search_terms.split('\n', 1)[0][:256]  # Adjust 256 to your needs

    query = {
        "size": 1,  # Focus on the top hit
        "query": {
            "multi_match": {
                "query": search_terms_adjusted,
                "fields": ["question^2", "answer"],  # Boosting questions for relevance
                "type": "best_fields"  # Can also experiment with other types like "most_fields" or "cross_fields"
            }
        },
        "_source": ["question", "answer"],
    }

    try:
        response = es.search(index=index, body=query)
    except Exception as e:
        logger.error(f"❌ Error performing search on Elasticsearch: {e}")
        return None

    if response['hits']['hits']:
        hit = response['hits']['hits'][0]
        score = hit['_score']  # Extract the score of the hit

        # Log every score for monitoring and tuning purposes
        logger.info(f"Search term: '{search_terms}' | Score: {score} | Threshold: {relevance_threshold}")

        # Check if the score exceeds the relevance threshold
        if score > relevance_threshold:
            question = hit["_source"]["question"]
            answer = hit["_source"]["answer"]
            # Format for model context
            context_entry = f"{answer}"
            logger.info(f"✅ Result above relevance threshold: {relevance_threshold}. Included in context: {context_entry}")
            return context_entry
        else:
            logger.info(f"⚠️ Result below relevance threshold (score: {score}, threshold: {relevance_threshold}).")
            return None
    else:
        logger.info("ℹ️ No hits found in Elasticsearch search.")
        return None

# ## // (old method)
# # elasticsearch_handler.py
# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# # github.com/FlyingFathead/TelegramBot-OpenAI-API/
# # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# relevance_threshold = 19.5

# from elasticsearch import Elasticsearch, ElasticsearchWarning
# import warnings
# import logging

# # Suppress Elasticsearch warnings
# warnings.filterwarnings("ignore", category=ElasticsearchWarning)

# # Initialize the logger for this module
# logger = logging.getLogger('TelegramBotLogger')  # Ensure this logger is configured in main.py

# async def search_es_for_context(search_terms):
#     es = Elasticsearch(["http://localhost:9200"])
#     if not es.ping():
#         logging.error("Could not connect to Elasticsearch.")
#         return None

#     index = "tg-bot-rag-index"

#     # Adjust the search_terms to use only the first line or a set number of characters
#     search_terms_adjusted = search_terms.split('\n', 1)[0][:256]  # Adjust 256 to your needs

#     query = {
#         "size": 1,  # Focus on the top hit
#         "query": {
#             "multi_match": {
#                 # "query": search_terms,
#                 "query": search_terms_adjusted,
#                 "fields": ["question^2", "answer"],  # Boosting questions for relevance
#                 "type": "best_fields"  # Can also experiment with other types like "most_fields" or "cross_fields"
#             }
#         },
#         "_source": ["question", "answer"],
#     }

#     response = es.search(index=index, body=query)
#     if response['hits']['hits']:
#         hit = response['hits']['hits'][0]
#         score = hit['_score']  # Extract the score of the hit
        
#         # Log every score for monitoring and tuning purposes
#         # logging.info(f"Search term: '{search_terms}' | Score: {score} | Threshold: {relevance_threshold}")

#         # Check if the score exceeds the relevance threshold
#         if score > relevance_threshold:
#             question = hit["_source"]["question"]
#             answer = hit["_source"]["answer"]
#             # Format for model context
#             context_entry = f"{answer}"
#             logging.info(f"Result above relevance threshold: {relevance_threshold}. Included in context: {context_entry}")
#             return context_entry
#         else:
#             logging.info(f"Result below relevance threshold (score: {score}, threshold: {relevance_threshold}).")
#             return None
#     else:
#         return None

#     """ response = es.search(index=index, body=query)
#     if response['hits']['hits']:
#         hit = response['hits']['hits'][0]
#         question = hit["_source"]["question"]
#         answer = hit["_source"]["answer"]
#         # Format for model context
#         context_entry = f"Q: {question}\nA: {answer}"
#         return context_entry
#     else:
#         return None """
