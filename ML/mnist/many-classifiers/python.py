#!/usr/bin/env python

"""Train classifiers to predict MNIST data."""

import numpy as np
import time

# Classifiers
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
from sklearn.neural_network import BernoulliRBM
from sklearn.pipeline import Pipeline
from sklearn import linear_model

import skflow


def dropout_model(x, y):
    """
    This is DNN with 500, 200 hidden layers, and dropout of 0.5 probability.
    """
    layers = skflow.ops.dnn(x, [500, 200], keep_prob=0.5)
    return skflow.models.logistic_regression(layers, y)


# Convolutional network, see
# https://github.com/tensorflow/skflow/blob/master/examples/mnist.py
import tensorflow as tf


def max_pool_2x2(tensor_in):
    """
    Max pooling of 2x2 patches with padding at the borders and stride of 2.
    """
    return tf.nn.max_pool(tensor_in,
                          ksize=[1, 2, 2, 1],
                          strides=[1, 2, 2, 1],
                          padding='SAME')


def conv_model(x, y):
    """
    Create a convolutional neural network model.

    Parameters
    ----------
    x : features
    y : labels

    Returns
    -------
    model object
    """
    x = tf.reshape(x, [-1, 28, 28, 1])
    with tf.variable_scope('conv_layer1'):
        h_conv1 = skflow.ops.conv2d(x, n_filters=32, filter_shape=[5, 5],
                                    bias=True, activation=tf.nn.relu)
        h_pool1 = max_pool_2x2(h_conv1)
    with tf.variable_scope('conv_layer2'):
        h_conv2 = skflow.ops.conv2d(h_pool1, n_filters=64, filter_shape=[5, 5],
                                    bias=True, activation=tf.nn.relu)
        h_pool2 = max_pool_2x2(h_conv2)
        h_pool2_flat = tf.reshape(h_pool2, [-1, 7 * 7 * 64])
    h_fc1 = skflow.ops.dnn(h_pool2_flat,
                           [1024],
                           activation=tf.nn.relu,
                           keep_prob=0.5)
    return skflow.models.logistic_regression(h_fc1, y)


def main():
    data = get_data()

    print("Got %i training samples and %i test samples." %
          (len(data['train']['X']), len(data['test']['X'])))

    logistic = linear_model.LogisticRegression()
    logistic.C = 6000.0

    # Get classifiers
    classifiers = [
        ('RBM 10', Pipeline(steps=[('rbm', BernoulliRBM(n_components=10)),
                                   ('logistic', logistic)])),
        ('RBM 100', Pipeline(steps=[('rbm', BernoulliRBM(n_components=100)),
                                    ('logistic', logistic)])),
        ('RBM 100, n_iter=20', Pipeline(steps=[('rbm',
                                                BernoulliRBM(n_components=100,
                                                             n_iter=20)),
                                               ('logistic', logistic)])),
        ('RBM 256', Pipeline(steps=[('rbm', BernoulliRBM(n_components=256)),
                                    ('logistic', logistic)])),
        ('RBM 512, n_iter=100', Pipeline(steps=[('rbm',
                                                 BernoulliRBM(n_components=512,
                                                              n_iter=10)),
                                                ('logistic', logistic)])),
        ('NN 20:5', skflow.TensorFlowDNNClassifier(hidden_units=[20, 5],
                                                   n_classes=data['n_classes'],
                                                   steps=500)),
        # ('NN 500:200 dropout',
        #  skflow.TensorFlowEstimator(model_fn=dropout_model,
        #                             n_classes=10,
        #                             steps=20000)),
        # ('CNN', skflow.TensorFlowEstimator(model_fn=conv_model,
        #                                    n_classes=10,
        #                                    batch_size=100,
        #                                    steps=20000,
        #                                    learning_rate=0.001)),
        ('SVM, adj.', SVC(probability=False,
                          kernel="rbf",
                          C=2.8,
                          gamma=.0073,
                          cache_size=200)),
        ('SVM, linear', SVC(kernel="linear", C=0.025, cache_size=200)),
        ('k nn', KNeighborsClassifier(3)),
        ('Decision Tree', DecisionTreeClassifier(max_depth=5)),
        ('Random Forest', RandomForestClassifier(n_estimators=50, n_jobs=10)),
        ('Random Forest 2', RandomForestClassifier(max_depth=5,
                                                   n_estimators=10,
                                                   max_features=1,
                                                   n_jobs=10)),
        ('AdaBoost', AdaBoostClassifier()),
        ('Naive Bayes', GaussianNB()),
        ('Gradient Boosting', GradientBoostingClassifier()),
        ('LDA', LinearDiscriminantAnalysis()),
        ('QDA', QuadraticDiscriminantAnalysis())
    ]

    # Fit them all
    classifier_data = {}
    for clf_name, clf in classifiers:
        print("#" * 80)
        print("Start fitting '%s' classifier." % clf_name)
        examples = 100000
        t0 = time.time()
        clf.fit(data['train']['X'][:examples], data['train']['y'][:examples])
        t1 = time.time()
        an_data = analyze(clf, data, t1 - t0, clf_name=clf_name)
        classifier_data[clf_name] = {'training_time': t1-t0,
                                     'testing_time': an_data['testing_time'],
                                     'accuracy': an_data['accuracy']}

    print_website(classifier_data)


def print_website(data):
    """
    Print dictionary as HTML for website

    Parameters
    ----------
    data : dict
        Keys are names of classifiers
    """
    print("""<table class="table">
  <thead>
    <tr>
        <th>Classifier</th>
        <th>Accuracy</th>
        <th>Training Time</th>
        <th>Testing Time</th>
    </tr>
  </thead>
  <tbody>""")
    danger_msg = 'class="danger"'
    best_time = 10**10
    best_acc = -1
    for _, clf_data in sorted(data.items()):
        best_time = min(clf_data['testing_time'], best_time)
        best_acc = max(clf_data['accuracy'], best_acc)
    for clf_name, clf_data in sorted(data.items()):
        acc_msg = ''
        test_msg = ''
        if clf_data['accuracy'] < 0.9:
            acc_msg = danger_msg
        if clf_data['testing_time'] > 5:
            test_msg = danger_msg
        print("    <tr>")
        print("\t\t<td>%s</td>" % clf_name)
        if clf_data['accuracy'] == best_acc:
            print('\t\t<td align="right" %s><b>%0.2f%%</b></td>' %
                  (acc_msg, clf_data['accuracy']*100))
        else:
            print('\t\t<td align="right" %s>%0.2f%%</td>' %
                  (acc_msg, clf_data['accuracy']*100))
        print('\t\t<td align="right">%0.4fs</td>' % clf_data['training_time'])
        if clf_data['testing_time'] == best_time:
            print('\t\t<td align="right" %s><b>%0.4fs</b></td>' %
                  (test_msg, clf_data['testing_time']))
        else:
            print('\t\t<td align="right" %s>%0.4fs</td>' %
                  (test_msg, clf_data['testing_time']))
        print("    </tr>")
    print("</tbody>")
    print("</table>")


def analyze(clf, data, fit_time, clf_name=''):
    """
    Analyze how well a classifier performs on data.

    Parameters
    ----------
    clf : classifier object
    data : dict
    fit_time : float
    clf_name : str

    Returns
    -------
    dict
        accuracy and testing_time
    """
    results = {}

    # Get confusion matrix
    from sklearn import metrics
    t0 = time.time()
    predicted = np.array([])
    for i in range(0, len(data['test']['X']), 128):  # go in chunks of size 128
        predicted_single = clf.predict(data['test']['X'][i:(i + 128)])
        predicted = np.append(predicted, predicted_single)
    t1 = time.time()
    results['testing_time'] = t1 - t0
    print("Classifier: %s" % clf_name)
    print("Training time: %0.4fs" % fit_time)
    print("Testing time: %0.4fs" % results['testing_time'])
    print("Confusion matrix:\n%s" %
          metrics.confusion_matrix(data['test']['y'],
                                   predicted))
    results['accuracy'] = metrics.accuracy_score(data['test']['y'], predicted)
    print("Accuracy: %0.4f" % results['accuracy'])

    # Print example
    # try_id = 1
    # out = clf.predict(data['test']['X'][try_id])  # clf.predict_proba
    # print("out: %s" % out)
    # size = int(len(data['test']['X'][try_id])**(0.5))
    # view_image(data['test']['X'][try_id].reshape((size, size)),
    #            data['test']['y'][try_id])
    return results


def view_image(image, label=""):
    """
    View a single image.

    Parameters
    ----------
    image : numpy array
        Make sure this is of the shape you want.
    label : str
    """
    from matplotlib.pyplot import show, imshow, cm
    print("Label: %s" % label)
    imshow(image, cmap=cm.gray)
    show()


def get_data():
    """
    Get data ready to learn with.

    Returns
    -------
    dict
    """
    dataset = 'iris'
    if dataset == 'iris':
        import sklearn
        from sklearn.datasets import fetch_mldata
        from sklearn.utils import shuffle
        mnist = fetch_mldata('iris')

        x = mnist.data
        y = mnist.target

        le = sklearn.preprocessing.LabelEncoder()
        le.fit(y)
        y = le.transform(y)

        x, y = shuffle(x, y, random_state=0)

        from sklearn.cross_validation import train_test_split
        x_train, x_test, y_train, y_test = train_test_split(x, y,
                                                            test_size=0.33,
                                                            random_state=42)
        data = {'train': {'X': x_train,
                          'y': y_train},
                'test': {'X': x_test,
                         'y': y_test},
                'n_classes': len(np.unique(y_train))}
        scaler = sklearn.preprocessing.StandardScaler().fit(data['train']['X'])
        data['train']['X'] = scaler.transform(data['train']['X'])
        data['test']['X'] = scaler.transform(data['test']['X'])
    elif dataset == 'mnist_simple':
        # Load the simple, but similar digits dataset
        from sklearn.datasets import load_digits
        from sklearn.utils import shuffle
        digits = load_digits()
        x = [np.array(el).flatten() for el in digits.images]
        y = digits.target

        # Scale data to [-1, 1] - This is of mayor importance!!!
        x = x/255.0*2 - 1

        x, y = shuffle(x, y, random_state=0)

        from sklearn.cross_validation import train_test_split
        x_train, x_test, y_train, y_test = train_test_split(x, y,
                                                            test_size=0.33,
                                                            random_state=42)
        data = {'train': {'X': x_train,
                          'y': y_train},
                'test': {'X': x_test,
                         'y': y_test}}
    elif dataset == 'mnist':  # Load the original dataset
        from sklearn.datasets import fetch_mldata
        from sklearn.utils import shuffle
        mnist = fetch_mldata('MNIST original')

        x = mnist.data
        y = mnist.target

        # Scale data to [-1, 1] - This is of mayor importance!!!
        x = x/255.0*2 - 1

        x, y = shuffle(x, y, random_state=0)

        from sklearn.cross_validation import train_test_split
        x_train, x_test, y_train, y_test = train_test_split(x, y,
                                                            test_size=0.33,
                                                            random_state=42)
        data = {'train': {'X': x_train,
                          'y': y_train},
                'test': {'X': x_test,
                         'y': y_test}}
    else:
        raise NotImplemented()
    return data


if __name__ == '__main__':
    main()
