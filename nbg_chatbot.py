# -*- coding: utf-8 -*-
"""NBG_ChatBot.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1IJmH4oVNaJ5HMd6YkyBBXLAmC2m93Hfv

# NGB ChatBot

## Setup
"""

from google.colab import drive
drive.mount('/content/mnt/', force_remount=True)

ngb_path='/content/mnt/My Drive/ngb'

from os import listdir
for i in listdir(ngb_path): print(i)

"""## Libraries required"""

# pip install wmd

# pip install -U spacy

# Commented out IPython magic to ensure Python compatibility.
# %matplotlib inline
import pandas as pd
import numpy as np
from sklearn import preprocessing
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.manifold import TSNE
import re
import unicodedata
from collections import Counter
import tarfile
import nltk
import spacy
import wmd

with tarfile.open(f'{ngb_path}/en_core_web_lg-2.3.1.tar.gz', 'r:gz') as tref:
    tref.extractall()

nlp = spacy.load('en_core_web_lg-2.3.1/en_core_web_lg/en_core_web_lg-2.3.1')
# nlp.add_pipe(wmd.WMD.SpacySimilarityHook(nlp), last=True)
stop_words = nlp.Defaults.stop_words

"""## Data Preprocessing"""

df = pd.read_csv(f'{ngb_path}/ngb_data.csv', encoding='utf8')

df_numpy = df.to_numpy()
data = [unicodedata.normalize("NFKD", str(doc[0]).lower()) for doc in df_numpy]
for doc in data[:5]: print(doc)

def  remove_stopwords(corpus):
    for i,doc in enumerate(corpus) :
        text = ''
        for token in nlp(doc):
            word = token.text
            if word not in stop_words and len(word)>1: 
                text = text + ' ' + word
        corpus[i] = text.strip()

    return corpus

def remove_punctuations(corpus):
    # symbols = "!\"#$%&()*+-./:;,<=>?@[\]^_`{|}~\n"
    # table = str.maketrans('', '', symbols)
    for i, doc in enumerate(corpus):
        sent = doc
        sent = re.sub(r'[^\w\s]', ' ', sent)
        sent = re.sub('\s*\\n+', ' ', sent)
        sent = re.sub('ngb\s*living', 'ngbliving', sent)
        corpus[i] = sent.strip()
        # corpus[i] = doc.translate(table)

    return corpus

def lemmatize(corpus):
    for i, doc in enumerate(corpus):
        tokens = nlp(doc)
        text = ''
        for token in tokens:
            if (token.text).isspace() or len(token.text)<3: continue
            text += token.lemma_ + ' '
        corpus[i] = text.strip()

    return corpus

def preprocess(corpus):
    corpus = remove_stopwords(corpus)
    corpus = remove_punctuations(corpus)
    corpus = lemmatize(corpus)

    return corpus

def get_vocab(data):
    wc = {}
    for doc in data:
        for token in nlp(doc):
            word = token.text
            try: wc[word] += 1
            except: wc[word] = 1

    return wc

def get_oov(data, wc):
    oov = {}
    for doc in data:
        for token in nlp(doc):
            if not token.has_vector and token.text not in oov: 
                oov[token.text] =  wc[token.text]

    return oov

pdata = data[:]
pdata = preprocess(pdata)

data[1], pdata[1]

wc = get_vocab(pdata)
oov = get_oov(pdata, wc)
wc_top = sorted(wc.items(), key=lambda x: x[1])[::-1]
oov_top = sorted(oov.items(), key=lambda x: x[1])[::-1]

wc_top[:10]

"""## TF-IDF"""

docs = [[token.text for token in nlp(doc) if not (token.text).isspace()] for doc in pdata]

"""### DF"""

DF = {}
for i, doc in enumerate(docs):
    for word in doc:
        try:
            DF[word].add(i)
        except:
            DF[word] = {i}

for i in DF: DF[i] = len(DF[i])

vocab = [w for w in DF]
print('total vocab:', len(vocab))

"""### TF and IDF"""

tf_idf = {}
N = len(docs)
for i, doc in enumerate(docs):
    counter = Counter(doc)
    for term in set(doc):
        tf = counter[term]/len(doc)
        df = DF[term]
        idf = np.log(N/(df+1))
        tf_idf[i, term] = tf * idf

for k in list(tf_idf)[:5]: print(k, tf_idf[k])

"""### Vectorization"""

docs_vector = np.zeros((N, len(vocab)))
for score in tf_idf:
    idx = vocab.index(score[1])
    docs_vector[score[0]][idx] = tf_idf[score]
 
docs_vector.shape

"""## GloVe (tf-idf weighted averaged document vector)"""

def getWeightedVec(sent, i=0, q=False, tfidf=0):
    weights, vectors = [], []
    doc = nlp(sent)
    for token in doc:
        if token.has_vector:
            term = token.text
            if len(term) < 3: continue
            # if  q is False: 
            #     weight = tf_idf[i, term]
            # else: 
            #     weight = tfidf
            # weights.append(weight)
            vectors.append(token.vector)
    
    # try: doc_vec = np.average(vectors, weights=weights, axis=0)
    try: doc_vec = np.average(vectors, axis=0)
    except: return doc.vector

    return doc_vec

def getSentVectors(data):
    vectors = []
    for i, sent in enumerate(data):
        vector = getWeightedVec(sent, i)
        vectors.append(vector)

    return vectors

sent_vec = getSentVectors(pdata)
len(sent_vec)

"""## Cosine Similarity"""

def cosine_sim(a, b):
    cos_sim = np.dot(a, b)/(np.linalg.norm(a)*np.linalg.norm(b))
    return cos_sim

print(f'1. {data[1]} \n2. {data[61]}')
print('\ncosine similarity: ', cosine_sim(sent_vec[1], sent_vec[61]))

"""## Query Handler"""

def get_query_tfidf(pquery):
    N = len(pdata)
    tokens = [token.text for token in nlp(pquery[0]) if not (token.text).isspace()]
    counter = Counter(tokens)
    for term in set(tokens):
        tf = counter[term]/len(tokens)
        try: df = DF[term]
        except: df = 0
        idf = np.log((N+1)/(df + 1))
    
    return tf * idf

"""### TF-IDF Query"""

def get_query_vector(pquery):
    q_vector = np.zeros((len(vocab)))
    tf_idf = get_query_tfidf(pquery)
    
    try:
        idx = vocab.index(term)
        q_vector[idx] = tf * idf
    except: pass
    
    return q_vector

def get_top_responses(q_vector, k=5):
    if k > len(pdata): k = len(pdata)
    scores = []
    for i, d_vec in enumerate(sent_vec):
        cos_score = cosine_sim(q_vector, d_vec)
        scores.append((cos_score, i))
    scores.sort(reverse=True)

    return [scores[i] for i in range(k)]

"""## Test Query"""

print('Please input a query> ')
query = input()
pquery = preprocess([''.join(query)])
print('pquery:', pquery)
q_tfidf = get_query_tfidf(pquery)
q_vector = getWeightedVec(sent=pquery[0], i=0, tfidf=q_tfidf, q=True)
responses = get_top_responses(q_vector)
top_doc_id = responses[0][1]

print(f'Answer> {df_numpy[top_doc_id][0]}\n')
print(responses)

# res = nlp(pdata[20])
# q = nlp('room key lost')
# cosine_sim(q.vector, res.vector)

pdata[60]