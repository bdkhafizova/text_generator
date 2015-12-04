#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from collections import defaultdict, deque
import re
import codecs
import cPickle as pickle
from scipy import stats


def create_dict():
    return defaultdict(float)


class Generator:

    def __init__(self, path, new_db_indicator):
        self.paths = path
        if (new_db_indicator):
            self._create_stats()
        else:
            self._load_stats()
        self.word_pattern =\
            re.compile(ur'[^\s!,?\-":.;()\u201c\u201d\u201e\u2018*0-9]+',
                       re.UNICODE)
        self.quotes_pattern =\
            re.compile(ur'["\u2019\u2018\u201d\u201e\u201c]?',
                       re.UNICODE)
        self.delim_pattern = re.compile(ur'[.!?,:;-]?', re.UNICODE)
        self.cache = deque()
        self.stats = defaultdict(create_dict)
        self.space = 0.0
        self.enter = 0.0
        self.total = 0.0
        self.counter = 0.0
        self.quote_state = False
        self.sentence_end = True
        self.recursion_depth = 0
        self.real_delims = [u'.', u'!', u'?']
        self.delims = [u'.', u'!', u'?', u',', u':', u';']
        self.quotes = [u'\'', u'"', u'\u2019', u'\u2018', u'\u201d', u'\u201e',
                       u'\u201c']
        self.quotes_observer = {u'"': False, u'\'': False}

    def _create_stats(self):
        self._process_text()
        self._calculate_params()
        self._normalize_stats()
        self._dump_stats()

    def _words(self, fileobj):
        for line in fileobj:
            if len(line) > 1:
                self.enter += 1
            for word in line.split():
                yield word

    def _process_word(self, word):
        pure_word = [w for w in self.word_pattern.findall(word) if w != '']
        if not pure_word:
            return list()
        quotes = [q for q in self.quotes_pattern.findall(word) if q != '']
        delims = [d for d in self.delim_pattern.findall(word) if d != '']
        final_words = list()
        if self.sentence_end and\
           (pure_word[0][0].isupper() or len(quotes) != 0):
            final_words.append('')
            self.sentence_end = False
        final_words.append(pure_word[0])
        for delim in delims:
            if delim in self.real_delims:
                self.total += 1
                self.sentence_end = True
            final_words.append(delim)
        for quote in quotes:
            if -1 < word.find(quote) < word.find(pure_word[0]):
                final_words.insert(1, quote if quote not in [u'\'', u'"']
                                   else u'\u201c')
            elif word.find(quote) > (word.find(pure_word[0]) + len(pure_word)):
                final_words.append(quote if quote not in [u'\'', u'"']
                                   else u'\u201d')
        return final_words

    def _push_to_stats(self, word):
        if len(self.cache) < 3:
            self.cache.append(word)
            if len(self.cache) == 1:
                pass
            elif len(self.cache) == 2:
                self.stats[self.cache[0]][self.cache[1]] += 1
            else:
                self.stats[self.cache[1]][self.cache[2]] += 1
        else:
            self.cache.popleft()
            self.cache.append(word)
            if self.cache[0] == '' or self.cache[1] == '':
                self.stats[self.cache[1]][self.cache[2]] += 1
            else:
                self.stats[(self.cache[0], self.cache[1])][self.cache[2]] += 1

    def _process_text(self):
        for directory in self.paths:
            for book in os.listdir(directory):
                with codecs.open(directory + '/' + book, encoding='utf8')\
                     as wordfile:
                    for raw_word in self._words(wordfile):
                        for word in self._process_word(raw_word):
                            self._push_to_stats(word)
                self._push_to_stats('')
                self.cache.clear()

    def _calculate_params(self):
        self.space = self.total - self.enter
        self.space /= self.total
        self.enter /= self.total

    def _normalize_stats(self):
        for beginning in self.stats:
            norm_factor = sum(self.stats[beginning][rest]
                              for rest in self.stats[beginning])
            for rest in self.stats[beginning]:
                self.stats[beginning][rest] /= norm_factor

    def _dump_stats(self):
        with open('stats', 'wb') as statfile:
            pickle.dump(self.stats, statfile)

    def _load_stats(self):
        with open(self.paths, 'rb') as statfile:
            self.stats = pickle.load(statfile)

    def generate_text(self, number):
        self.text_list = list()
        self.text = str()
        while (len(self.text_list) < number):
            sentence = self.generate_sentence()
            self.text_list.append(sentence)
        space_or_enter_gen =\
            stats.rv_discrete(name='space_or_enter_gen',
                              values=([0, 1], [self.space, self.enter]))
        for sentence in self.text_list:
            self.text += sentence
            delim = space_or_enter_gen.rvs(size=1)
            self.text += u'\n'.encode('utf-8') if delim[0]\
                         else u' '.encode('utf-8')
        print self.text

    def _generate_sentence(self):
        self.counter += 1
        sentence = list()
        sentence.append(self.generate_word(''))
        sentence.append(self.generate_word(sentence[0]))
        while (sentence[-1] != ''):
            sentence.append(self.generate_word((sentence[-2], sentence[-1])))
        return ' '.join(word.encode('utf-8') for word in sentence[:-1])\
               + sentence[-1].encode('utf-8')

    def _generate_word(self, previous):
        probabilities = list()
        self.recursion_depth += 1
        indexes = range(len(self.stats[previous]))
        match_dict = dict()
        for next_word, index in zip(self.stats[previous], indexes):
            probabilities.append(self.stats[previous][next_word])
            match_dict[index] = next_word
        if len(probabilities) == 0:
            raise RuntimeError('Invalid fields')
        local_generator = stats.rv_discrete(name='local_generator',
                                            values=(indexes, probabilities))
        r = local_generator.rvs(size=1)
        a = unicode()
        a = match_dict[r[0]]
        if a in self.quotes:
            if not self.quote_state and a == u'\u201c':
                self.quote_state = True
            elif self.quote_state and a == u'\u201d':
                self.quote_state = False
            else:
                if self.recursion_depth < 50:
                    a = self.generate_word(previous)
        self.recursion_depth = 0
        return a


g = Generator('')
g.process_text()
g.generate_text(100)
