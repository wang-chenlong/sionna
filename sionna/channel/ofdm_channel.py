#
# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""
Layer for implementing an ideal OFDM channel response, i.e., single-tap
channel response in the frequency domain
"""

import tensorflow as tf
from tensorflow.keras.layers import Layer

from . import GenerateOFDMChannel, ApplyOFDMChannel

class OFDMChannel(Layer):
    # pylint: disable=line-too-long
    r"""OFDMChannel(channel_model, resource_grid, add_awgn=True, normalize_channel=False, return_channel=False, dtype=tf.complex64, **kwargs)

    Generate channel frequency responses and apply them to channel inputs
    assuming an OFDM waveform with no ICI nor ISI.

    This class inherits from the Keras `Layer` class and can be used as layer
    in a Keras model.

    For each OFDM symbol :math:`s` and subcarrier :math:`n`, the channel output is computed as follows:

    .. math::
        y_{s,n} = \widehat{h}_{s, n} x_{s,n} + w_{s,n}

    where :math:`y_{s,n}` is the channel output computed by this layer,
    :math:`\widehat{h}_{s, n}` the frequency channel response,
    :math:`x_{s,n}` the channel input ``x``, and :math:`w_{s,n}` the additive noise.

    For multiple-input multiple-output (MIMO) links, the channel output is computed for each antenna
    of each receiver and by summing over all the antennas of all transmitters.

    The channel frequency response for the :math:`s^{th}` OFDM symbol and
    :math:`n^{th}` subcarrier is computed from a given channel impulse response
    :math:`(a_{m}(t), \tau_{m}), 0 \leq m \leq M-1` generated by the ``channel_model``
    as follows:

    .. math::
        \widehat{h}_{s, n} = \sum_{m=0}^{M-1} a_{m}(s) e^{-j2\pi n \Delta_f \tau_{m}}

    where :math:`\Delta_f` is the subcarrier spacing, and :math:`s` is used as time
    step to indicate that the channel impulse response can change from one OFDM symbol to the
    next in the event of mobility, even if it is assumed static over the duration
    of an OFDM symbol.

    Parameters
    ----------
    channel_model : :class:`~sionna.channel.ChannelModel` object
        An instance of a :class:`~sionna.channel.ChannelModel` object, such as
        :class:`~sionna.channel.RayleighBlockFading` or
        :class:`~sionna.channel.tr38901.UMi`.

    resource_grid : :class:`~sionna.ofdm.ResourceGrid`
        Resource grid

    add_awgn : bool
        If set to `False`, no white Gaussian noise is added.
        Defaults to `True`.

    normalize_channel : bool
        If set to `True`, the channel is normalized over the resource grid
        to ensure unit average energy per resource element. Defaults to `False`.

    return_channel : bool
        If set to `True`, the channel response is returned in addition to the
        channel output. Defaults to `False`.

    dtype : tf.DType
        Complex datatype to use for internal processing and output.
        Defaults to tf.complex64.

    Input
    -----

    (x, no) or x:
        Tuple or Tensor:

    x :  [batch size, num_tx, num_tx_ant, num_ofdm_symbols, fft_size], tf.complex
        Channel inputs

    no : Scalar or Tensor, tf.float
        Scalar or tensor whose shape can be broadcast to the shape of the
        channel outputs:
        [batch size, num_rx, num_rx_ant, num_ofdm_symbols, fft_size].
        Only required if ``add_awgn`` is set to `True`.
        The noise power ``no`` is per complex dimension. If ``no`` is a scalar,
        noise of the same variance will be added to the outputs.
        If ``no`` is a tensor, it must have a shape that can be broadcast to
        the shape of the channel outputs. This allows, e.g., adding noise of
        different variance to each example in a batch. If ``no`` has a lower
        rank than the channel outputs, then ``no`` will be broadcast to the
        shape of the channel outputs by adding dummy dimensions after the last
        axis.

    Output
    -------
    y : [batch size, num_rx, num_rx_ant, num_ofdm_symbols, fft_size], tf.complex
        Channel outputs
    h_freq : [batch size, num_rx, num_rx_ant, num_tx, num_tx_ant, num_ofdm_symbols, fft_size], tf.complex
        (Optional) Channel frequency responses. Returned only if
        ``return_channel`` is set to `True`.
    """

    def __init__(self, channel_model, resource_grid, add_awgn=True,
                normalize_channel=False, return_channel=False,
                dtype=tf.complex64, **kwargs):
        super().__init__(trainable=False, dtype=dtype, **kwargs)

        self._cir_sampler = channel_model
        self._rg = resource_grid
        self._add_awgn = add_awgn
        self._normalize_channel = normalize_channel
        self._return_channel = return_channel

    def build(self, input_shape): #pylint: disable=unused-argument

        self._generate_channel = GenerateOFDMChannel(self._cir_sampler,
                                                     self._rg,
                                                     self._normalize_channel,
                                                     tf.as_dtype(self.dtype))
        self._apply_channel = ApplyOFDMChannel( self._add_awgn,
                                                tf.as_dtype(self.dtype))

    def call(self, inputs):

        if self._add_awgn:
            x, no = inputs
        else:
            x = inputs

        h_freq = self._generate_channel(tf.shape(x)[0])
        if self._add_awgn:
            y = self._apply_channel([x, h_freq, no])
        else:
            y = self._apply_channel([x, h_freq])

        if self._return_channel:
            return y, h_freq
        else:
            return y
