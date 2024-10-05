# qa_to_json.py
# a part of the `elasticsearch_db` toolkit
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# github.com/FlyingFathead/TelegramBot-OpenAI-API/
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import os
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

def add_to_index(es, index, qa_pairs, backup_file):
    for pair in qa_pairs:
        es.index(index=index, body=pair)
    backup_to_json(backup_file, qa_pairs)

def interactive_mode(es, index, backup_file):
    while True:
        mode = input("Choose mode - [s]ingle question, [m]ulti-question, [b]atch input (or type 'exit' to finish): ")
        if mode.lower() == 'exit':
            break

        questions = []
        if mode.lower() == 's':
            question = input("Enter your question: ")
            if question.strip():
                questions.append(question)
        elif mode.lower() == 'm' or mode.lower() == 'b':
            prompt_text = "Enter your questions, one per line. When finished, press Enter on an empty line:" if mode.lower() == 'b' else "Enter your question (or type 'done' to finish questions): "
            print(prompt_text) if mode.lower() == 'b' else None
            while True:
                question = input() if mode.lower() == 'b' else input("Enter your question (or type 'done' to finish questions): ")
                if question == "" and mode.lower() == 'b':
                    break
                if question.lower() == 'done' and mode.lower() == 'm':
                    break
                if question.strip():
                    questions.append(question.strip())

        if not questions:
            print("No questions entered. Skipping to next entry.")
            continue

        answer = input("Enter the answer: ")
        references = input("Enter any references (optional): ")
        qa_pairs = [{'question': q, 'answer': answer, 'references': references} for q in questions]

        for pair in qa_pairs:
            print("\nQ&A pair generated:")
            print("<" + "-"*72 + ">")
            print("Q:", pair["question"])
            print("A:", pair["answer"])
            if references:
                print("Ref:", references)
            print("<" + "-"*72 + ">")

        confirm = input("Add to index (y/n)? ")
        if confirm.lower() == 'y':
            add_to_index(es, index, qa_pairs, backup_file)
            print(f"Added {len(qa_pairs)} Q&A pairs to Elasticsearch index '{index}' and backed up to JSON file.")
        else:
            print("No Q&A pairs were added.")

def backup_to_json(file_path, qa_pairs):
    try:
        data = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        data.extend(qa_pairs)
        
        # Validate JSON data before writing
        try:
            json.dumps(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data: {e}")

        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Failed to backup Q&A pairs to JSON: {e}")

def main():

    backup_file = "./backup_file.json"

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
        interactive_mode(es, args.index, backup_file)
    elif args.file_path:
        parsed_data = parse_qa_text(args.file_path)
        
        # Validate parsed data before proceeding
        try:
            json.dumps(parsed_data)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON data: {e}")
            sys.exit(1)

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
            add_to_index(es, args.index, parsed_data, backup_file)
            print(f"Added {len(parsed_data)} Q&A pairs to Elasticsearch index '{args.index}'.")
        else:
            print(json.dumps(parsed_data, indent=4, ensure_ascii=False))
    else:
        print("Please provide a file path or enable interactive mode.")
        sys.exit(1)

if __name__ == "__main__":
    main()


# import os
# import json
# import sys
# from elasticsearch import Elasticsearch
# from argparse import ArgumentParser

# def parse_qa_text(file_path):
#     qa_pairs = []
#     with open(file_path, 'r', encoding='utf-8') as file:
#         content = file.read()
#     qa_blocks = content.split('###')
#     for block in qa_blocks:
#         lines = block.strip().split('\n')
#         if len(lines) < 2:
#             continue
#         current_pair = {'question': '', 'answer': '', 'references': ''}
#         is_answer = False
#         for line in lines:
#             if line.startswith('> '):
#                 if current_pair['question'] and current_pair['answer']:
#                     qa_pairs.append(current_pair)
#                     current_pair = {'question': '', 'answer': '', 'references': ''}
#                 current_pair['question'] = line[2:].strip()
#                 is_answer = False
#             elif line.startswith('>> '):
#                 is_answer = True
#                 if current_pair['answer']:
#                     current_pair['answer'] += '\n'
#                 current_pair['answer'] += line[3:].strip()
#             elif line.startswith('## '):
#                 current_pair['references'] = line[3:].strip()
#             elif is_answer:
#                 current_pair['answer'] += '\n' + line.strip()
#         if current_pair['question'] and current_pair['answer']:
#             qa_pairs.append(current_pair)
#     return qa_pairs

# def add_to_index(es, index, qa_pairs, backup_file):
#     for pair in qa_pairs:
#         es.index(index=index, body=pair)
#     backup_to_json(backup_file, qa_pairs)  # Call backup function after adding to Elasticsearch

# def interactive_mode(es, index, backup_file):
#     while True:
#         mode = input("Choose mode - [s]ingle question, [m]ulti-question, [b]atch input (or type 'exit' to finish): ")
#         if mode.lower() == 'exit':
#             break

#         questions = []
#         if mode.lower() == 's':
#             question = input("Enter your question: ")
#             if question.strip():  # Ensure the question is not empty or whitespace
#                 questions.append(question)
#         elif mode.lower() == 'm' or mode.lower() == 'b':
#             prompt_text = "Enter your questions, one per line. When finished, press Enter on an empty line:" if mode.lower() == 'b' else "Enter your question (or type 'done' to finish questions): "
#             print(prompt_text) if mode.lower() == 'b' else None
#             while True:
#                 question = input() if mode.lower() == 'b' else input("Enter your question (or type 'done' to finish questions): ")
#                 if question == "" and mode.lower() == 'b':  # End input for batch mode on empty line
#                     break
#                 if question.lower() == 'done' and mode.lower() == 'm':  # End input for multi-question mode on 'done'
#                     break
#                 if question.strip():  # Ignore empty or whitespace-only lines
#                     questions.append(question.strip())

#         if not questions:
#             print("No questions entered. Skipping to next entry.")
#             continue

#         answer = input("Enter the answer: ")
#         references = input("Enter any references (optional): ")
#         qa_pairs = [{'question': q, 'answer': answer, 'references': references} for q in questions]

#         for pair in qa_pairs:
#             print("\nQ&A pair generated:")
#             print("<" + "-"*72 + ">")
#             print("Q:", pair["question"])
#             print("A:", pair["answer"])
#             if references:
#                 print("Ref:", references)
#             print("<" + "-"*72 + ">")

#         confirm = input("Add to index (y/n)? ")
#         if confirm.lower() == 'y':
#             add_to_index(es, index, qa_pairs, backup_file)
#             print(f"Added {len(qa_pairs)} Q&A pairs to Elasticsearch index '{index}' and backed up to JSON file.")
#         else:
#             print("No Q&A pairs were added.")
            
# # backup generated Q&A pairs to a JSON file
# def backup_to_json(file_path, qa_pairs):
#     try:
#         data = []
#         if os.path.exists(file_path):
#             with open(file_path, 'r', encoding='utf-8') as file:
#                 data = json.load(file)
#         data.extend(qa_pairs)
#         with open(file_path, 'w', encoding='utf-8') as file:
#             json.dump(data, file, indent=4, ensure_ascii=False)
#     except Exception as e:
#         print(f"Failed to backup Q&A pairs to JSON: {e}")

# def main():

#     # define the backup file for q&a's created
#     backup_file = "./backup_file.json"

#     parser = ArgumentParser(description="Parse Q&A text and optionally add to Elasticsearch index.")
#     parser.add_argument("file_path", nargs='?', help="Path to the Q&A text file.", default=None)
#     parser.add_argument("--addtoindex", action="store_true", help="If set, add parsed Q&A pairs to Elasticsearch index.")
#     parser.add_argument("--index", default="tg-bot-rag-index", help="Elasticsearch index name. Default is 'tg-bot-rag-index'.")
#     parser.add_argument("--interactive", action="store_true", help="Enable interactive mode to add Q&A pairs.")
#     args = parser.parse_args()

#     if args.interactive:
#         es = Elasticsearch(["http://localhost:9200"])
#         if not es.ping():
#             print("Could not connect to Elasticsearch.")
#             sys.exit(1)
#         interactive_mode(es, args.index, backup_file)
#     elif args.file_path:
#         parsed_data = parse_qa_text(args.file_path)
#         if args.addtoindex:
#             print("Q&A pairs generated:")
#             for pair in parsed_data:
#                 print("<" + "-"*72 + ">")
#                 print("Q:", pair["question"])
#                 print("A:", pair["answer"])
#                 if pair["references"]:
#                     print("Ref:", pair["references"])
#                 print("<" + "-"*72 + ">\n")

#             confirm = input("Add to index (y/n)? ")
#             if confirm.lower() != 'y':
#                 print("Operation cancelled by the user.")
#                 sys.exit(0)

#             es = Elasticsearch(["http://localhost:9200"])
#             if not es.ping():
#                 print("Could not connect to Elasticsearch.")
#                 sys.exit(1)
#             add_to_index(es, args.index, parsed_data)
#             print(f"Added {len(parsed_data)} Q&A pairs to Elasticsearch index '{args.index}'.")
#         else:
#             print(json.dumps(parsed_data, indent=4, ensure_ascii=False))
#     else:
#         print("Please provide a file path or enable interactive mode.")
#         sys.exit(1)

# if __name__ == "__main__":
#     main()

# # old code for reference =>
# """ def interactive_mode(es, index):
#     qa_pairs = []
#     while True:
#         question = input("Enter your question (or type 'exit' to finish): ")
#         if question == 'exit':
#             break
#         answer = input("Enter the answer: ")
#         references = input("Enter any references (optional): ")
#         print("\nQ&A pair generated:")
#         print("<" + "-"*72 + ">")
#         print("Q:", question)
#         print("A:", answer)
#         if references:
#             print("Ref:", references)
#         print("<" + "-"*72 + ">")

#         confirm = input("Add to index (y/n)? ")
#         if confirm.lower() == 'y':
#             qa_pairs.append({'question': question, 'answer': answer, 'references': references})
    
#     if qa_pairs:
#         add_to_index(es, index, qa_pairs)
#         print(f"Added {len(qa_pairs)} Q&A pairs to Elasticsearch index '{index}'.")
#     else:
#         print("No Q&A pairs were added.") """    