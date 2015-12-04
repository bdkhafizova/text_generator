#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from collections import defaultdict, deque
import re
import codecs
import cPickle as pickle
from scipy import stats


dirs = ['test_test']

def create_dict():
    return defaultdict(float)

class Generator:

    def __init__(self, path):             
        self.word_pattern =\
                re.compile(ur'[^\s!,?"\:.;()\u201c\u201d\u201e\u2018*0-9]+', 
                           re.UNICODE)
        self.quotes_pattern =\
                re.compile(ur'[\'"\u2019\u2018\u201d\u201e\u201c]?',
                           re.UNICODE)
        self.delim_pattern = re.compile(ur'[.!?,:]?', re.UNICODE)
        self.cache = deque()
        self.stats = defaultdict(create_dict)
        self.space = 0.0
        self.enter = 0.0
        self.quote = 0.0
        self.non_quote = 0.0
        self.total = 0.0
        self.counter = 0.0
        self.quote_state = False
        self.delims = [u'.', u'!', u'?']
        self.quotes = [u'\'', u'"', u'\u2019', u'\u2018', u'\u201d', u'\u201e', u'\201c']
        

    def words(self, fileobj):
        for line in fileobj:
            if len(line) > 1:
                self.enter += 1
            for word in line.split():
                yield word

    def process_word(self, word):
        pure_word = [w for w in self.word_pattern.findall(word) if w != '']
        if not pure_word:
            return list()
        quotes = [q for q in self.quotes_pattern.findall(word) if q != '']
        delims = [d for d in self.delim_pattern.findall(word) if d != '']
        final_words = list()
        final_words.append(pure_word)
        real_delimiter = False
        for delim in delims:
            if delim in self.delims:
                self.total += 1
                real_delimiter = True
            final_words.append(delim)
        for quote in quotes:
            if -1 < word.find(quote) < word.find(pure_word[0]):
                final_words.insert(0, quote)
            elif word.find(quote) > (word.find(pure_word[0]) + len(pure_word)):
                if real_delimiter:
                    self.quote += 1
                else:
                    final_words.append(quote)
        return final_words

    def q(self, word):
        #if word in self.quotes:
        #    if word == u'\u201c' or word == u'\u201d':
        #        return word
        #    else:
        #        return u'\u201c'
        return word

    def push_to_stats(self, word):
        if len(self.cache) < 3:
            self.cache.append(word)
            if len(self.cache) == 1:
                self.stats[''][self.q(self.cache[0])] += 1
            elif len(self.cache) == 2:
                self.stats[self.q(self.cache[0])][self.q(self.cache[1])] += 1
            else:
                self.stats[(self.q(self.cache[0]), self.q(self.cache[1]))][self.q(self.cache[2])] += 1
        else:
            self.cache.popleft()
            self.cache.append(word)
            if (self.cache[0] in self.delims and not self.cache[1] in self.quotes):
                self.stats[self.q(self.cache[1])][self.q(self.cache[2])] += 1
            elif (self.cache[0] in self.delims and self.cache[1] in self.quotes):
                self.stats[''][self.q(self.cache[0])] += 1
            elif (self.cache[1] in self.delims):
                self.stats[''][self.q(self.cache[2])] += 1
            else:
                self.stats[(self.q(self.cache[0]),self.q(self.cache[1]))][self.q(self.cache[2])] += 1


    def process_text(self):
        for directory in dirs:     
            for book in os.listdir(directory):
                with codecs.open(directory + '/' + book, encoding='utf8') as wordfile:
                    wordgen = self.words(wordfile)
                    for raw_word in wordgen:
                        #print raw_word
                        for word in self.process_word(raw_word):
                            #print unicode(word[0])
                            self.push_to_stats(unicode(word[0]))
                self.cache.clear()
            print self.enter
            print self.total
            self.space = self.total - self.enter
            self.space /= self.total
            self.enter /= self.total
            self.non_quote = self.total - self.quote
            self.non_quote /= self.total
            self.quote /= self.total
            #self.dump_stats(directory)
            #with codecs.open('stats_' + book, 'w', encoding='utf8') as statfile:
            #    for stat in self.stats.items():
            #        key_stat, enum_stat = stat
            #        if isinstance(key_stat, tuple):
            #            statfile.write(u', '.join(item for item in key_stat) + '\n')
            #        for values in enum_stat.items():
            #            ww, cc = values
            #            statfile.write(ww + ' ' + str(cc) + '\n')
        for beginning in self.stats:
            norm_factor = sum(self.stats[beginning][rest] for rest in self.stats[beginning])
            for rest in self.stats[beginning]:
                self.stats[beginning][rest] /= norm_factor
        with codecs.open('stats_new', 'w', encoding='utf8') as statfile:
            for stat in self.stats.items():
                key_stat, enum_stat = stat
                if isinstance(key_stat, tuple):
                    statfile.write(u', '.join(item for item in key_stat) + '\n')
                for values in enum_stat.items():
                    ww, cc = values
                    statfile.write(ww + ' ' + str(cc) + '\n')

    def dump_stats(self):
        with open('stats', 'wb') as statfile:
            pickle.dump(self.stats, statfile)
            
    def load_stats(self):
        with open('stats', 'rb') as statfile:
            self.stats = pickle.load(statfile)

    def generate_text(self, number):
        self.text_list = list()
        self.text = str()
        while (len(self.text_list) < number):
            sentence = self.generate_sentence()
            #print sentence
            self.text_list.append(sentence)
        
        vals = [0,1]
        space_or_enter_gen = stats.rv_discrete(name = 'space_or_enter_gen',
                values = (vals, [self.space, self.enter]))
        for sentence in self.text_list:
            self.text += sentence
            delim = space_or_enter_gen.rvs(size=1)
            self.text += u'\n'.encode('utf-8') if delim[0] else u' '.encode('utf-8')
        print self.text

    def generate_sentence(self):
        self.counter += 1
        print self.counter
        sentence = list()
        sentence.append(self.generate_word(''))
        sentence.append(self.generate_word(sentence[0]))
        while (sentence[-1] not in self.delims):
            sentence.append(self.generate_word((sentence[-2], sentence[-1])))
        if self.quote_state:
            quote_gen = stats.rv_discrete(name = 'quote_gen', values = ([0,1], [self.quote, self.non_quote]))
            quote_char = u'' if quote_gen.rvs(size=1)[0] else u'\u201d'
            self.quote_state = True if quote_char == u'' else False
            return ' '.join(word.encode('utf-8') for word in sentence[:-1]) + sentence[-1].encode('utf-8') + quote_char.encode('utf-8')
        else:
            return ' '.join(word.encode('utf-8') for word in sentence[:-1]) + sentence[-1].encode('utf-8')

    def generate_word(self, previous):
        probabilities = list()

        if isinstance(previous, tuple):
            prev1 = unicode()
            prev2 = unicode()
            prev1, prev2 = previous
            #print 'Searching for' + prev1.encode('utf-8') + ' ' + prev2.encode('utf-8')
        else:
            pass
            #print 'Searching for' + previous.encode('utf-8')
        indexes = range(len(self.stats[previous]))
        match_dict = dict()
        for next_word, index in zip(self.stats[previous], indexes):
            probabilities.append(self.stats[previous][next_word])
            match_dict[index] = next_word
        if len(probabilities) == 0:
            raise RuntimeError('Invalid fields{}'.format(previous.encode('utf-8')))
        local_generator = stats.rv_discrete(name = 'local_generator', values = (indexes, probabilities))
        r = local_generator.rvs(size = 1)
        a = unicode()
        a = match_dict[r[0]]
        if a in self.quotes:
            if not self.quote_state and a == u'\u201c':
                self.quote_state = True
                a = self.q(a)
            elif self.quote_state and a == u'\u201d':
                self.quote_state = False
            else:
                a = self.generate_word(previous)
        #print a.encode('utf-8')
        return a


g = Generator('')
g.process_text()
g.generate_text(10)
#g.dump_stats()
