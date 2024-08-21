import os
import re
from collections import Counter
import time
from tqdm import tqdm
from nltk.corpus import stopwords
import nltk

nltk.download('stopwords')

def get_text_files(folder_path):
    return [f for f in os.listdir(folder_path) if f.endswith('.txt')]

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def tokenize(text):
    stop_words = set(stopwords.words('english'))
    words = re.findall(r'\b\w+\b', text.lower())
    return [word for word in words if word not in stop_words]

def count_words(folder_path):
    word_counter = Counter()
    text_files = get_text_files(folder_path)

    for file_name in tqdm(text_files, desc="Processing files"):
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

    output_file = "least-common-words"
    with open(output_file, 'w') as f:
        f.write("Least common words:\n")
        for word, count in least_common_words:
            line = f"{word}: {count}\n"
            print(line, end='')
            f.write(line)
            time.sleep(0.01)  # Adds a delay to draw out the printing over time

if __name__ == "__main__":
    current_folder = os.getcwd()
    main(current_folder)