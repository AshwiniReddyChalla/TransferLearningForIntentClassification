import tensorflow as tf
import numpy as np

import data_helper
import word_embedding

class AtisData(object):
  def __init__(self,
                data_folder,
                vocab_size,
                max_in_seq_len,
                max_data_size,
                embed_size = -1):

    self.max_in_seq_len = max_in_seq_len
    self.max_data_size = max_data_size
    self.batch_index = 0;

    data = data_helper.get_tokenized_data(data_folder, vocab_size)
    tokenized_in_seq_path_train, tokenized_label_path_train = data[0]
    tokenized_in_seq_path_dev, tokenized_label_path_dev = data[1]
    tokenized_in_seq_path_test, tokenized_label_path_test = data[2]
    in_vocab_path, label_vocab_path = data[3]

    self.in_seq_train = self.read_data_into_memory(tokenized_in_seq_path_train);
    self.labels_train = self.read_data_into_memory(tokenized_label_path_train);
    self.in_seq_dev = self.read_data_into_memory(tokenized_in_seq_path_dev);
    self.labels_dev = self.read_data_into_memory(tokenized_label_path_dev);
    self.in_seq_test = self.read_data_into_memory(tokenized_in_seq_path_test);
    self.labels_test = self.read_data_into_memory(tokenized_label_path_test);
    self.in_vocab_path = in_vocab_path;
    self.vocab_size = self.get_vocab_size();

    if(len(self.in_seq_train) != len(self.labels_train)) :
       raise ValueError("Number of train labels != Number of train inputs : %d != %d",len(self.in_seq_train), len(self.labels_train))

    if(len(self.in_seq_dev) != len(self.labels_dev)) :
       raise ValueError("Number of dev labels != Number of dev inputs : %d != %d",len(self.in_seq_dev), len(self.labels_dev))

    if(len(self.in_seq_test) != len(self.labels_test)) :
       raise ValueError("Number of test labels != Number of test inputs : %d != %d",len(self.in_seq_test), len(self.labels_test))

    self.no_of_class_labels = self.get_number_of_labels();
    self.embed_size = embed_size
    self.word_embedding = None
    
    if embed_size > 0:
      self.word_embedding = word_embedding.WordEmbedding(
                        self.in_seq_train,
                        self.vocab_size,
                        embed_size,
                        2,
                        1)

  def get_vocab_size(self):
    with tf.gfile.GFile(self.in_vocab_path, mode="r") as source_file:
      lines = source_file.readlines()
      return len(lines)

  def get_number_of_labels(self):
    unique_labels = []
    [unique_labels.extend(label) for label in self.labels_train] 
    return len(set(unique_labels)) 
  
  def read_data_into_memory(self, file_path):
    data = []
    with tf.gfile.GFile(file_path, mode="r") as source_file:
      lines = source_file.readlines()
      if len(lines) > self.max_data_size:
        lines = lines[:self.max_data_size]
      for line in lines:
        line = line.strip();
        data.append([int(x) for x in line.split()]);
    return data

  def set_max_in_seq_len(self, max_in_seq_len):
    self.max_in_seq_len = max_in_seq_len

  def get_padded_data(self, input):
    padded_inputs = []

    for i in range(len(input)):
      data = input[i]
      if len(data) < self.max_in_seq_len:
        pad = [data_helper.PAD_ID for _ in range(self.max_in_seq_len - len(data))]
        data.extend(pad);
      else:
        data = data[:self.max_in_seq_len]
      padded_inputs.append(np.array(data, np.int32))

    return np.array(padded_inputs)

  def get_one_hot_encoded_labels(self, labels):
    one_hot_encoded_labels = []
    for label in labels:
      data = [0 for _ in range(self.no_of_class_labels)]
      data[label[0]-1] = 1
      one_hot_encoded_labels.append(np.array(data, np.int32))

    return np.array(one_hot_encoded_labels)

  def get_embedded_data(self, data):
    if not self.word_embedding:
      return data
    embedded_data = np.ndarray((len(data), self.max_in_seq_len*self.embed_size), dtype=np.int32)
    for i in range(len(data)):
      e_d = []
      line = data[i]
      for j in range(self.max_in_seq_len):
        e_d.extend(self.word_embedding.get_embedding(line[j]))
      embedded_data[i] = e_d
    
    return embedded_data

  def get_test_data(self):
    return (self.get_embedded_data(self.get_padded_data(self.in_seq_test)), self.get_one_hot_encoded_labels(self.labels_test))

  def get_next_batch(self, batch_size):
    train_input = []
    train_labels = []
    counter = 0
    train_data_size = len(self.in_seq_train)
    last_index = self.batch_index + batch_size
    if last_index <= train_data_size:
      train_input = self.in_seq_train[self.batch_index : last_index]
      train_labels = self.labels_train[self.batch_index : last_index]
      if last_index == train_data_size:
        self.batch_index = 0
      else:
        self.batch_index = last_index
    else:
        train_input = self.in_seq_train[self.batch_index :]
        train_labels = self.labels_train[self.batch_index :]
        self.batch_index = batch_size - len(train_input) 
        train_input.extend(self.in_seq_train[: self.batch_index])
        train_labels.extend(self.labels_train[: self.batch_index])

    padded_data = self.get_padded_data(train_input)
    return (self.get_embedded_data(padded_data), self.get_one_hot_encoded_labels(train_labels))
