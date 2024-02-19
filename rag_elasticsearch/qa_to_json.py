# qa_to_json.py
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import json
import sys
from elasticsearch import Elasticsearch
from argparse import ArgumentParser

def parse_qa_text(file_path):
    qa_pairs = []
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    qa_blocks = content.split('###')
    for block in qa_blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
        current_pair = {'question': '', 'answer': '', 'references': ''}
        is_answer = False
        for line in lines:
            if line.startswith('> '):
                if current_pair['question'] and current_pair['answer']:
                    qa_pairs.append(current_pair)
                    current_pair = {'question': '', 'answer': '', 'references': ''}
                current_pair['question'] = line[2:].strip()
                is_answer = False
            elif line.startswith('>> '):
                is_answer = True
                if current_pair['answer']:
                    current_pair['answer'] += '\n'
                current_pair['answer'] += line[3:].strip()
            elif line.startswith('## '):
                current_pair['references'] = line[3:].strip()
            elif is_answer:
                current_pair['answer'] += '\n' + line.strip()
        if current_pair['question'] and current_pair['answer']:
            qa_pairs.append(current_pair)
    return qa_pairs

def add_to_index(es, index, qa_pairs):
    for pair in qa_pairs:
        es.index(index=index, body=pair)

def interactive_mode(es, index):
    qa_pairs = []
    while True:
        question = input("Enter your question (or type 'exit' to finish): ")
        if question == 'exit':
            break
        answer = input("Enter the answer: ")
        references = input("Enter any references (optional): ")
        print("\nQ&A pair generated:")
        print("<" + "-"*72 + ">")
        print("Q:", question)
        print("A:", answer)
        if references:
            print("Ref:", references)
        print("<" + "-"*72 + ">")

        confirm = input("Add to index (y/n)? ")
        if confirm.lower() == 'y':
            qa_pairs.append({'question': question, 'answer': answer, 'references': references})
    
    if qa_pairs:
        add_to_index(es, index, qa_pairs)
        print(f"Added {len(qa_pairs)} Q&A pairs to Elasticsearch index '{index}'.")
    else:
        print("No Q&A pairs were added.")

def main():
    parser = ArgumentParser(description="Parse Q&A text and optionally add to Elasticsearch index.")
    parser.add_argument("file_path", nargs='?', help="Path to the Q&A text file.", default=None)
    parser.add_argument("--addtoindex", action="store_true", help="If set, add parsed Q&A pairs to Elasticsearch index.")
    parser.add_argument("--index", default="tg-bot-rag-index", help="Elasticsearch index name. Default is 'tg-bot-rag-index'.")
    parser.add_argument("--interactive", action="store_true", help="Enable interactive mode to add Q&A pairs.")
    args = parser.parse_args()

    if args.interactive:
        es = Elasticsearch(["http://localhost:9200"])
        if not es.ping():
            print("Could not connect to Elasticsearch.")
            sys.exit(1)
        interactive_mode(es, args.index)
    elif args.file_path:
        parsed_data = parse_qa_text(args.file_path)
        if args.addtoindex:
            print("Q&A pairs generated:")
            for pair in parsed_data:
                print("<" + "-"*72 + ">")
                print("Q:", pair["question"])
                print("A:", pair["answer"])
                if pair["references"]:
                    print("Ref:", pair["references"])
                print("<" + "-"*72 + ">\n")

            confirm = input("Add to index (y/n)? ")
            if confirm.lower() != 'y':
                print("Operation cancelled by the user.")
                sys.exit(0)

            es = Elasticsearch(["http://localhost:9200"])
            if not es.ping():
                print("Could not connect to Elasticsearch.")
                sys.exit(1)
            add_to_index(es, args.index, parsed_data)
            print(f"Added {len(parsed_data)} Q&A pairs to Elasticsearch index '{args.index}'.")
        else:
            print(json.dumps(parsed_data, indent=4, ensure_ascii=False))
    else:
        print("Please provide a file path or enable interactive mode.")
        sys.exit(1)

if __name__ == "__main__":
    main()