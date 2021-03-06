import tensorflow as tf

def VAT(input_tensor, network, network_to_approximate=None, xi=1e-6, epsilon=2.0, weight=1.0, num_approximation=1, clip_value_min=1e-30, dtype=tf.float32):
    """
    https://arxiv.org/abs/1704.03976
    ===input===
    input_tensor           : input tensor of network
    network                : function that receives input_tensor and returns the logits (i.e., the output without softmax.)
    network_to_approximate : function only to approximate the virtual adversarial perturbation
                             this may be useful when you want network to behave differently from the usual training part at some points such like dropout.
                             if this is None (default), this is same as "network."
    xi                     : scale of perturbation that is used to approximate the virtual adversarial perturbation. (default: 1e-6)
    epsilon                : scale of virtual adversarial perturbation. results can be sensitive at this number. (default: 2.0)
    weight                 : weight of loss. (default: 1.0)
    num_approximation      : number of iteration to approximate the virtual adversarial perturbation. (default: 1)
    clip_value_min         : this is for clipping some values that is divisor or given to log. (default: 1e-30)
    dtype                  : dtype of tensors in this function. (default: tf.float32)

    ===output===
    vat_cross_entropy      : virtual adversarial loss
    vat_perturbation       : virtual adversarial perturbation

    """

    if network_to_approximate is None:
        network_to_approximate = network
        isSameNetwork = True
    else:
        isSameNetwork = False

    clipped = lambda x: tf.maximum(x, clip_value_min)

    axis_without_batch_size = tuple(range(1,len(input_tensor.get_shape())))
    if len(axis_without_batch_size) == 1: axis_without_batch_size = axis_without_batch_size[0]
    normalized = lambda x: x / clipped(tf.norm(x, axis=axis_without_batch_size, keep_dims=True))

    plain_softmax = tf.nn.softmax(network_to_approximate(input_tensor))
    perturbation = xi * normalized(tf.random_normal(shape=tf.shape(input_tensor), dtype=dtype))
    for i in range(num_approximation):
        softmax_accommodating_perturbation = tf.nn.softmax(network_to_approximate(input_tensor + perturbation))
        cross_entropy_accommodating_perturbation = -tf.reduce_sum(plain_softmax * tf.log(clipped(softmax_accommodating_perturbation)), reduction_indices=1) * weight
        adversarial_direction = tf.gradients(cross_entropy_accommodating_perturbation, [perturbation])[0]
        vat_perturbation = normalized(adversarial_direction)
        perturbation = xi * vat_perturbation

    current_softmax = tf.nn.softmax(network(input_tensor)) if not isSameNetwork else plain_softmax
    current_softmax = tf.stop_gradient(current_softmax)
    vat_perturbation = tf.stop_gradient(epsilon * vat_perturbation)
    vat_softmax = tf.nn.softmax(network(input_tensor + vat_perturbation))
    vat_cross_entropy = tf.reduce_sum(-tf.reduce_sum(current_softmax * tf.log(clipped(vat_softmax)), reduction_indices=1) * weight) / (tf.reduce_sum(weight)+1e-30)
    return vat_cross_entropy, vat_perturbation


