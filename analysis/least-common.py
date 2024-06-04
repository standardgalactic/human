import os
import re
from collections import Counter

def get_text_files(folder_path):
    return [f for f in os.listdir(folder_path) if f.endswith('.txt')]

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def tokenize(text):
    # Remove non-alphanumeric characters and split by whitespace
    return re.findall(r'\b\w+\b', text.lower())

def count_words(folder_path):
    word_counter = Counter()
    text_files = get_text_files(folder_path)

    for file_name in text_files:
        file_path = os.path.join(folder_path, file_name)
        text = read_file(file_path)
        words = tokenize(text)
        word_counter.update(words)

    return word_counter

def get_least_common_words(word_counter, n=50000):
    return word_counter.most_common()[:-n-1:-1]

def main(folder_path):
    word_counter = count_words(folder_path)
    least_common_words = get_least_common_words(word_counter)

    print("Least common words:")
    for word, count in least_common_words:
        print(f"{word}: {count}")

if __name__ == "__main__":
    current_folder = os.getcwd()
    main(current_folder)

