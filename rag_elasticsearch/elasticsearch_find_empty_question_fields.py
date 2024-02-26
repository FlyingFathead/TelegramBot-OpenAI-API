# elasticsearc_find_empty_question_fields.py

from elasticsearch import Elasticsearch

def find_empty_questions(index_name):
    es = Elasticsearch(["http://localhost:9200"])  # Adjust the connection details as necessary

    query = {
        "query": {
            "bool": {
                "should": [
                    {"bool": {"must_not": {"exists": {"field": "question"}}}},
                    {"term": {"question.keyword": ""}},
                    {"script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "if (doc['question'].size() == 0) return 1; return doc['question'].value == null || doc['question'].value.isEmpty() ? 1 : 0;",
                            "lang": "painless"
                        }
                    }}
                ],
                "minimum_should_match": 1
            }
        }
    }

    response = es.search(index=index_name, body=query)
    print(f"Found {response['hits']['total']['value']} documents with empty or missing 'question' fields.")

    # Example handling: Print out the document IDs
    for doc in response['hits']['hits']:
        print(f"Document ID: {doc['_id']}")

if __name__ == "__main__":
    index_name = "tg-bot-rag-index"  # Replace with your index
    # index_name = "your_index_name"  # Replace with your actual index name
    find_empty_questions(index_name)