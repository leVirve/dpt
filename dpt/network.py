import tensorflow as tf
from keras.layers import Convolution2D, Dense, Dropout, Flatten, MaxPooling2D
from keras.models import Sequential
from tensorflow.python.layers import layers


class KerasCNN:

    NAME = 'KerasCNN'

    def __init__(self, image_shape=None):
        self.input_shape = image_shape
        self.model = self.build_model()

    def build_model(self):
        layers = [
            Convolution2D(32, *(5, 5), border_mode='same', activation='relu', input_shape=self.input_shape),
            MaxPooling2D(pool_size=(2, 2)),
            Convolution2D(64, *(5, 5), border_mode='same', activation='relu'),
            MaxPooling2D(pool_size=(2, 2)),
            Flatten(),
            Dense(1024, activation='relu'),
            Dropout(0.4),
            Dense(10, activation='softmax'),
        ]
        model = Sequential(layers=layers, name=self.NAME)
        return model

    def compile(self):
        self.model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy'])
        return self


class TensorCNN:

    NAME = 'TensorCNN'

    def __init__(self, images, labels, step=0, is_train=True, is_sparse=False):
        self.images = images
        self.labels = labels
        self.step = step
        self.is_train = is_train
        self.is_sparse = is_sparse

    def build_graph(self):
        self.step = tf.Variable(self.step, name='global_step', trainable=False)
        self.prediction = self.build('model', wrapped=False)
        ordered_op_names = ['loss', 'optimize', 'accuracy']
        for op_name in ordered_op_names:
            setattr(self, op_name, self.build(op_name))
        self.summary = tf.summary.merge_all()
        self.train_op = [self.optimize, self.loss, self.summary]
        return self

    def build(self, name, wrapped=True):
        builder = getattr(self, 'build_{}'.format(name))
        if wrapped:
            with tf.name_scope(name):
                return builder()
        return builder()

    def build_model(self):
        tf.summary.image('input', self.images)
        conv1 = layers.conv2d(self.images, 32, [5, 5], padding='same', activation=tf.nn.relu, name='conv1')
        tf.summary.histogram('conv1-result', conv1)
        pool1 = layers.max_pooling2d(conv1, pool_size=[2, 2], strides=2, name='pool1')
        conv2 = layers.conv2d(pool1, 64, [5, 5], padding='same', activation=tf.nn.relu, name='conv2')
        tf.summary.histogram('conv2-result', conv2)
        pool2 = layers.max_pooling2d(conv2, pool_size=[2, 2], strides=2, name='pool2')
        flat1 = tf.reshape(pool2, [-1, 7 * 7 * 64], name='flatten')
        dense = layers.dense(flat1, units=1024, activation=tf.nn.relu, name='fc1')
        tf.summary.histogram('fc1-result', dense)
        dropout = layers.dropout(dense, rate=0.4, training=self.is_train, name='dropout')
        logits = layers.dense(dropout, units=10, name='fc2')
        tf.summary.histogram('fc2-result', logits)
        return logits

    def build_loss(self):
        cross_entropy = (
            tf.losses.sparse_softmax_cross_entropy
            if self.is_sparse else
            tf.losses.softmax_cross_entropy)
        kwarg = {'labels' if self.is_sparse else 'onehot_labels': self.labels}
        xentropy = cross_entropy(logits=self.prediction, **kwarg, scope='xentropy')
        loss = tf.reduce_mean(xentropy, name='mean_loss')
        tf.summary.scalar('loss', loss)
        return loss

    def build_optimize(self):
        return tf.train.AdamOptimizer(learning_rate=0.001).minimize(self.loss, global_step=self.step)

    def build_accuracy(self):
        pred_class = tf.argmax(self.prediction, 1, name='pred_class')
        if self.is_sparse:
            correct_pred = tf.equal(tf.cast(pred_class, tf.int32), self.labels)
        else:
            correct_pred = tf.equal(pred_class, tf.argmax(self.labels, 1))
        accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))
        tf.summary.scalar('accuracy', accuracy)
        return accuracy
