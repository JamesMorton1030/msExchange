"""The TextGenerator module contains functions for generating text based on
an input file. This is used for generating content to write into word based
on wikipedia articles, or replying to emails with content generated from
reddit comments.
"""

import glob
import json
import random
import re
from os import path


class TextGenerator:
    """Used to generate text for whatever you need
    USAGE:
        text_gen = TextGenerator()
        text_gen.gen_text(num_of_paragraphs)
    For loading a specific file
    USAGE:
        text_gen = TextGenerator()
        text_gen.read_file(<path_to_file>)
        text_gen.gen_text(num_of_paragraphs)
    """

    def __init__(self, client, order=2, max_words=50):
        self.client = client
        self.corpus = {}
        self.order = order
        self.max_words = max_words

    def get_file(self):
        """A method to retrieve a random wikipedia article from the API. If an article
        cannot be retrieved from the API, a random one is opened from the wiki directory.
        """
        # Attempt to retrieve an article from the API
        request = self.client.connection.request(
            "post", "/api/resources/wikipedia_article", json={}
        )

        if request is not None and request.status_code == 200:
            # Process response
            article = request.json()

            self._process_line(article["text"])
        else:
            # Something went wrong getting a url list, load from a file
            self.client.logger.debug("Failed to retrieve Wikipedia article from API, status code: {}".format(request.status_code))
            
            self.read_random_file()

    def read_random_file(self, filepath=path.join(path.dirname(__file__), "wiki")):
        """A method to choose a random file from the 'wiki'
        directory. This is used when not specifying which file to read.
        """
        # get random txt file from the specified directory
        outfile_dir = filepath + "\\*.txt"
        filename = random.choice(glob.glob(outfile_dir))
        # print(f'file: {filename}') # useful for debugging

        # read selected file into the 'corpus'
        self.read_file(filename)

    def read_file(self, filename, file_encoding="utf-8"):
        """A method to open a file and grab a random line (wikipedia article)
        This then passes the chosen line to be processed into a 'corpus', which
        is then used to generate text
        """
        with open(filename, "r", encoding=file_encoding) as file:
            # choose a random line from file, each line contains a
            # JSON encoded wikipedia article
            article = random.choice(file.read().splitlines())
        line = json.loads(article)
        # print(f'article: {line["title"]}') # useful for debugging
        self._process_line(line["text"])

    def _process_line(self, line):
        """A method used to process a section of text into a 'corpus' which can be
        used to generate text.
        """
        # split the text into sentences, based on '.', '?' and '!'
        # NOTE: This can create some issues where '.' is used differently, for example: e.g. dr.
        # this can be remedied by creating a function that accomodates for these,
        # however I feel we can deal with having random 'g.'s in our paragraphs for now
        sentences = re.split(r"\. |\?|\!", line)

        for sentence in sentences:
            # split the sentence into words
            tokens = sentence.split()
            key_list = []

            # setdefault: https://docs.python.org/3/library/stdtypes.html#dict.setdefault
            # try to return value of key '#BEGIN#' otherwise return []
            self.corpus.setdefault("#BEGIN#", []).append(tokens[0 : self.order])

            for item in tokens:
                # markov chains 'order' is how many previous words are checked
                # to determine the next word. default is 2
                if len(key_list) < self.order:
                    key_list.append(item)
                    continue

                # try to return value of tuple(key_list) otherwise return []
                self.corpus.setdefault(tuple(key_list), []).append(item)

                # remove first element in key_list and append the current item
                key_list.pop(0)
                key_list.append(item)

    def gen_sentence(self):
        """A method used to generate a sentence using a generated corpus.
        It is called multiple times so should be as efficient as possible.
        """
        # if the corpus doesn't already exist, load a random wiki article
        if not self.corpus:
            self.get_file()

        # choose a random starting key from the corpus
        key = list(random.choice(self.corpus["#BEGIN#"]))
        gen_str = " ".join(key)
        for _ in range(self.max_words):
            # get list of potential candidate words based on the current previous words
            # if no words can be found, return '#END#'
            candiates = self.corpus.setdefault(tuple(key), "#END#")
            if candiates == "#END#":
                break

            # choose random word and add it to the sentence
            next_key = random.choice(candiates)
            gen_str += " " + next_key

            # cycle current key to get new list of candidate words
            key.pop(0)
            key.append(next_key)

        return gen_str + "."

    def gen_paragraph(self, max_sentences=2):
        """A method used to generate a set of sentences to form a paragraph.
        """
        gen_str = ""
        for _ in range(max_sentences):
            gen_str += self.gen_sentence() + " "
        return gen_str

    def gen_text(self, max_paragraphs=2):
        """A method used to generate a set of paragraphs to form a text.
        """
        gen_str = ""
        for _ in range(max_paragraphs):
            gen_str += self.gen_paragraph(random.randint(4, 12)) + "\n"
        return gen_str
