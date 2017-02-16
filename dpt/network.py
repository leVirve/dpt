import tensorflow as tf
from keras.layers import Convolution2D, Dense, Dropout, Flatten, MaxPooling2D
from keras.models import Sequential
from tensorflow.python.layers import layers

from dpt.tools import tf_summary


class KerasCNN:

    NAME = 'KerasCNN'

    def __init__(self, image_shape=None):
        self.input_shape = image_shape
        self.model = self.build_model()

    def build_model(self):
        layers = [
            self.conv2d(32, *(5, 5), input_shape=self.input_shape),
            self.pool2d(),
            self.conv2d(64, *(5, 5)),
            self.pool2d(),
            Flatten(),
            Dense(1024, activation='relu'),
            Dropout(0.4),
            Dense(10, activation='softmax'),
        ]
        model = Sequential(layers=layers, name=self.NAME)
        return model

    def conv2d(self, *args, **kwargs):
        return Convolution2D(*args, border_mode='same', activation='relu', **kwargs)

    def pool2d(self, *args):
        return MaxPooling2D(pool_size=(2, 2))

    def compile(self):
        self.model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy'])
        return self


class TensorCNN:

    NAME = 'TensorCNN'
    ordered_op_names = ['loss', 'optimize', 'accuracy']

    def __init__(self, images, labels, step=0, is_train=True):
        self.images = images
        self.labels = labels
        self.step = step
        self.is_train = is_train

    def build_graph(self):
        self.prediction = self.build('model', wrapped=False)
        for op_name in self.ordered_op_names:
            setattr(self, op_name, self.build(op_name))

        self.summary = tf.summary.merge_all()
        self.train_op = [self.optimize, self.loss]
        return self

    def build(self, name, wrapped=True):
        builder = getattr(self, 'build_{}'.format(name))
        if wrapped:
            with tf.name_scope(name):
                return builder()
        return builder()

    def build_model(self):
        x = self.images
        tf.summary.image('input', x)
        x = self.conv2d(x, 32, [5, 5], name='conv1')
        x = self.pool2d(x, name='pool1')
        x = self.conv2d(x, 64, [5, 5], name='conv2')
        x = self.pool2d(x, name='pool2')
        x = self.flatten(x, [-1, 7 * 7 * 64], name='flatten')
        x = self.dense(x, 1024, activation=tf.nn.relu, name='fc1')
        x = self.dropout(x, 0.4, training=self.is_train, name='dropout')
        x = self.dense(x, 10, name='fc2')
        return x

    @tf_summary('histogram')
    def conv2d(self, *args, name=None):
        return layers.conv2d(*args, padding='same', activation=tf.nn.relu, name=name)

    @tf_summary('histogram')
    def pool2d(self, *args, name=None):
        return layers.max_pooling2d(*args, pool_size=[2, 2], strides=2, name=name)

    @tf_summary('histogram')
    def dropout(self, *args, training=None, name=None):
        return layers.dropout(*args, training=training, name=name)

    @tf_summary('histogram')
    def flatten(self, *args, name=None):
        return tf.reshape(*args, name=name)

    @tf_summary('histogram')
    def dense(self, *args, activation=None, name=None):
        return layers.dense(*args, activation=activation, name=name)

    @tf_summary(name='loss')
    def build_loss(self):
        param = {'labels': self.labels, 'logits': self.prediction}
        xentropy = tf.losses.sparse_softmax_cross_entropy(**param, scope='xentropy')
        return tf.reduce_mean(xentropy, name='mean_loss')

    def build_optimize(self):
        step = tf.Variable(self.step, name='global_step', trainable=False)
        return tf.train.AdamOptimizer(learning_rate=0.001).minimize(self.loss, global_step=step)

    @tf_summary(name='accuracy')
    def build_accuracy(self):
        pred_class = tf.cast(tf.argmax(self.prediction, 1, name='pred_class'), tf.int32)
        correct_pred = tf.equal(pred_class, self.labels)
        return tf.reduce_mean(tf.cast(correct_pred, tf.float32))
