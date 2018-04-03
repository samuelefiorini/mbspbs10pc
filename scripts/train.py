#!/usr/bin/env python
"""Train bidirectional timestamp-guided attention model.

Train the keras model on the data extracted by `extract_sequences.py` and
matched by CEM (see `matching_step1.py` and `matching_step2.R`).
"""

from __future__ import print_function

import argparse
import os
import warnings
from datetime import datetime
import matplotlib

matplotlib.use('Agg')
warnings.filterwarnings('ignore')

import joblib as jl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from keras import optimizers as opt
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from keras.layers import CuDNNLSTM
from keras.preprocessing.sequence import pad_sequences
from keras.preprocessing.text import Tokenizer
from keras.utils import plot_model
from mbspbs10pc.model import build_model
from mbspbs10pc.plotting import plot_confusion_matrix, plot_history
from sklearn import metrics
from sklearn.model_selection import StratifiedShuffleSplit


def parse_arguments():
    """"Parse input arguments."""
    parser = argparse.ArgumentParser(description='MBS-PBS 10% data/labels '
                                                 'extraction.')
    parser.add_argument('-l', '--labels', type=str,
                        help='Path to the labels csv file generated by '
                             '`matching_step2.R`.',
                        default=None)
    parser.add_argument('-d', '--data', type=str,
                        help='Path to the data pkl file generated by '
                        '`extract_sequences.py`.',
                        default=None)
    parser.add_argument('-e', '--embedding', type=str,
                        help='Path to the embedding matrix csv file.',
                        default=None)
    parser.add_argument('-o', '--output', type=str,
                        help='Ouput file name root.',
                        default=None)
    args = parser.parse_args()
    return args


def init_main():
    """Initialize the main routine."""
    args = parse_arguments()

    if args.labels is None or not os.path.exists(args.labels):
        raise ValueError('{} labels file not found'.format(args.labels))

    if args.data is None or not os.path.exists(args.data):
        raise ValueError('{} data file not found'.format(args.data))

    # Check output filename
    if args.output is None:
        args.output = 'out_' + str(datetime.now())

    return args


def load_data_labels(data_filename, labels_filename):
    """Load data and labels.

    Parameters:
    --------------
    data_filename: string
        Data filename.

    labels_filename: string
        Labels filename.

    Returns:
    --------------
    dataset: pandas.DataFrame
        Input data.
    """
    labels = pd.read_csv(labels_filename, header=0).rename(
        {'Unnamed: 0': 'PIN'}, axis=1)[['PIN', 'CLASS']].set_index('PIN')

    data_pkl = jl.load(open(data_filename, 'rb')).loc[labels.index, 'seq']
    dataset = pd.DataFrame(columns=['Seq', 'Class'], index=labels.index)
    dataset.loc[:, 'Seq'] = data_pkl
    dataset.loc[:, 'Class'] = labels['CLASS']
    for idx in dataset.index:
        _tmp = dataset.loc[idx, 'Seq'].split(' ')
        dataset.loc[idx, 'mbs_seq'] = ' '.join(_tmp[::2])
        dataset.loc[idx, 'times_seq'] = ' '.join(_tmp[1::2])
    return dataset


def tokenize(data):
    """Tokenize input data.

    Parameters:
    --------------
    data: pandas.DataFrame
        The DataFrame created by `load_data_labels`.

    Returns:
    --------------
    padded_mbs_seq: array
        Padded sequence of MBS items.

    padded_timestamp_seq: array
        Padded sequence of timestamps.

    tokenizer: keras.preprocessing.text.Tokenizer
        The tokenizer object fit on the input data.
    """
    # Tokenization
    tokenizer = Tokenizer(char_level=False, lower=False, split=' ')

    # Fit on corpus and extract tokenized sequences
    tokenizer.fit_on_texts(data['mbs_seq'])
    seq = tokenizer.texts_to_sequences(data['mbs_seq'])

    # Pad tokenized sequences
    lengths = [len(x) for x in seq]
    maxlen = int(np.percentile(lengths, 95))
    padded_mbs_seq = pad_sequences(seq, maxlen=maxlen, padding='pre')

    # Pad timestamps
    t_seq = [map(int, data.loc[idx, 'times_seq'].split(' '))
             for idx in data.index]
    padded_timestamp_seq = pad_sequences(t_seq, maxlen=maxlen)

    return padded_mbs_seq, padded_timestamp_seq, tokenizer


def train_validation_test_split(data, labels, test_size=0.4,
                                validation_size=0.1, verbose=False):
    """Split the input dataset in three non overlapping sets.

    Parameters:
    --------------
    data: list
        A list made as follows `[padded_mbs_seq, padded_timestamp_seq]`

    labels: array
        Labels vector returned by `load_data_labels()`.

    test_size: numeric (default=0.4)
        Test set size.

    validation_size: numeric (default=0.1)
        Validation set size.

    verbose: bool
        Print verbose debug messages.

    Returns:
    --------------
    train_set: tuple
        A tuple like `(train_data, y_train)` where `train_data` is a list
        like [MBS training sequence, timestamp training sequence].

    validation_set: tuple
        Same as `train_set`, but for validation set.

    test_set: tuple
        Same as `train_set`, but for test set.
    """
    # Full dataset
    y = labels.values.ravel()
    X, X_t = data[0], data[1]

    # Learn / Test
    sss = StratifiedShuffleSplit(n_splits=1, test_size=test_size,
                                 random_state=42)
    learn_idx, test_idx = next(sss.split(X, y))

    X_learn, y_learn = X[learn_idx, :], y[learn_idx]
    X_test, y_test = X[test_idx, :], y[test_idx]

    X_learn_t = X_t[learn_idx, :]
    X_test_t = X_t[test_idx, :]

    if verbose:
        print('* {} learn / {} test'.format(len(y_learn), len(y_test)))

    # Training / Validation
    sss = StratifiedShuffleSplit(n_splits=1, test_size=validation_size,
                                 random_state=420)
    train_idx, valid_idx = next(sss.split(X_learn, y_learn))

    X_train, y_train = X_learn[train_idx, :], y_learn[train_idx]
    X_valid, y_valid = X_learn[valid_idx, :], y_learn[valid_idx]

    X_train_t = X_learn_t[train_idx, :]
    X_valid_t = X_learn_t[valid_idx, :]

    if verbose:
        print('* {} training / {} validation'.format(len(y_train),
                                                     len(y_valid)))
    # Packing output
    train_data = [X_train, X_train_t.reshape(len(y_train), X.shape[1], 1)]
    train_set = (train_data, y_train)

    validation_data = [X_valid, X_valid_t.reshape(len(y_valid), X.shape[1], 1)]
    validation_set = (validation_data, y_valid)

    test_data = [X_test, X_test_t.reshape(len(y_test), X.shape[1], 1)]
    test_set = (test_data, y_test)

    return train_set, validation_set, test_set


def fit_model(model, training_set, validation_set, outputfile):
    # Start training
    print('* Training model...')
    callbacks = [ReduceLROnPlateau(monitor='val_loss',
                                   factor=0.5, patience=7,
                                   min_lr=1e-6, verbose=1),
                 EarlyStopping(monitor='val_loss', patience=15),
                 ModelCheckpoint(filepath=outputfile+'_weights.h5',
                                 save_best_only=True, save_weights_only=True)]

    history = model.fit(x=training_set[0], y=training_set[1],
                        epochs=200,
                        callbacks=callbacks,
                        batch_size=128,
                        validation_data=validation_set)

    print('* Saving training history...', end=' ')
    plt.figure(dpi=100)
    plot_history(history)
    plt.savefig(outputfile+'_loss_history.png')
    print(u'\u2713')
    return model


def main():
    """Main train.py routine."""
    print('-------------------------------------------------------------------')
    print('MBS - PBS 10% dataset utility: train.py')
    print('-------------------------------------------------------------------')
    args = init_main()

    # Load data
    print('* Loading {} and {}...'.format(args.data, args.labels), end=' ')
    dataset = load_data_labels(args.data, args.labels)
    print(u'\u2713')

    # Load embedding matrix
    print('* Loading {}...'.format(args.embedding), end=' ')
    embedding_matrix = pd.read_csv(
        args.embedding, header=0, index_col=0).values
    print(u'\u2713')

    # Tokenize and pad
    print('* Preparing data...', end=' ')
    padded_mbs_seq, padded_timestamp_seq, _ = tokenize(dataset)
    maxlen = padded_mbs_seq.shape[1]

    # Split in training, validation, test sets
    tr_set, v_set, ts_set = train_validation_test_split(
        [padded_mbs_seq, padded_timestamp_seq], dataset['Class'],
        test_size=0.4, validation_size=0.1,
        verbose=False)
    print(u'\u2713')

    # Build the model
    print('* Building model...', end=' ')
    model = build_model(mbs_input_shape=(maxlen,),
                        timestamp_input_shape=(maxlen, 1),
                        vocabulary_size=embedding_matrix.shape[0],
                        embedding_size=embedding_matrix.shape[1],
                        recurrent_units=64,
                        dense_units=128,
                        bidirectional=True,
                        LSTMLayer=CuDNNLSTM)

    # Initialize the embedding matrix
    model.get_layer('mbs_embedding').set_weights([embedding_matrix])
    model.get_layer('mbs_embedding').trainable = True

    # Compile the model
    model.compile(optimizer=opt.RMSprop(lr=0.005),
                  loss='binary_crossentropy',
                  metrics=['acc'])
    print(u'\u2713')

    # Print the summary to file
    print('* Saving model summary and graph structure...', end=' ')
    filename = args.output+'_summary.txt'
    with open(filename, 'w') as f:
        model.summary(print_fn=lambda x: f.write(x + '\n'))

    # Save the model dotfile
    plot_model(model, show_shapes=True, to_file=args.output+'_dot.png')
    print(u'\u2713')

    # Fit the model
    model = fit_model(model, tr_set, v_set, outputfile=args.output)

    # Test set evaluation
    print('* Evaluate on test set...')
    model.load_weights(args.output+'_weights.h5')
    y_test = ts_set[1]
    y_pred = model.predict(ts_set[0]).ravel()

    # Plot non-normalized confusion matrix
    cnf_matrix = metrics.confusion_matrix(y_test, y_pred > 0.5)
    plt.figure(dpi=100)
    plot_confusion_matrix(cnf_matrix, classes=['METONLY', 'METX'],
                          title='Confusion matrix', cmap=plt.cm.Blues)
    plt.savefig(args.output+'_cm.png')

    # Save stats
    loss = metrics.log_loss(y_test, y_pred)
    acc = metrics.accuracy_score(y_test, y_pred > 0.5)
    prec = metrics.precision_score(y_test, y_pred > 0.5)
    rcll = metrics.recall_score(y_test, y_pred > 0.5)
    auc = metrics.roc_auc_score(y_test, y_pred)
    print('Test scores:\n * Log-Loss\t{:1.5f}\n * Accuracy:\t{:1.5f}\n '
          '* Precision:\t{:1.5f}\n * Recall:\t{:1.5f}\n * AUC:'
          '\t{:1.5f}'.format(loss, acc, prec, rcll, auc),
          file=open(args.output+'_stats.txt', 'w'))


################################################################################


if __name__ == '__main__':
    main()
