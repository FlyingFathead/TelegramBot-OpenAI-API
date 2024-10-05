# elasticsearch_find_and_delete_entry.py

# find and delete mistaken entries from the elasticsearch database

from elasticsearch import Elasticsearch

def search_qa_pairs(es, index_name, search_term):
    query = {
        "query": {
            "multi_match": {
                "query": search_term,
                "fields": ["question", "answer"]
            }
        }
    }
    response = es.search(index=index_name, body=query)
    return response['hits']['hits']

def delete_document(es, index_name, doc_id):
    response = es.delete(index=index_name, id=doc_id)
    return response

def main():
    es = Elasticsearch(["http://localhost:9200"])
    index_name = "tg-bot-rag-index"  # Adjust the index name as needed
    
    search_term = input("Enter a search term to find Q&A pairs: ")
    hits = search_qa_pairs(es, index_name, search_term)
    
    if hits:
        print("Found Q&A pairs:")
        for hit in hits:
            print(f"ID: {hit['_id']}, Question: {hit['_source']['question']}, Answer: {hit['_source']['answer']}")
        
        delete_id = input("Enter the ID of the document to delete (leave blank to cancel): ").strip()
        if delete_id:
            confirm = input(f"Are you sure you want to delete the document with ID {delete_id}? (y/n): ").strip().lower()
            if confirm == 'y':
                response = delete_document(es, index_name, delete_id)
                print(f"Document with ID {delete_id} has been deleted. Response: {response}")
            else:
                print("Deletion cancelled.")
    else:
        print("No Q&A pairs found with the given search term.")

if __name__ == "__main__":
    main()