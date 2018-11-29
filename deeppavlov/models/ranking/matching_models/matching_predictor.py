# Copyright 2018 Neural Networks and Deep Learning lab, MIPT
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
from typing import List, Iterable

from deeppavlov.core.common.log import get_logger
from deeppavlov.core.models.component import Component
from deeppavlov.models.ranking.matching_models.tf_base_matching_model import TensorflowBaseMatchingModel
from deeppavlov.core.common.registry import register
from deeppavlov.core.data.utils import zero_pad_truncate

log = get_logger(__name__)


@register('matching_predictor')
class MatchingPredictor(Component):
    """The class for ranking of the response given N context turns
    using the trained SMN or DAM neural network in the ``interact`` mode.

    Args:
        num_context_turns (int): A number N of ``context`` turns in data samples.
        max_sequence_length (int): A maximum length of text sequences in tokens.
            Longer sequences will be truncated and shorter ones will be padded.
        *args, **kwargs: Other parameters.
    """

    def __init__(self,
                 model: TensorflowBaseMatchingModel,
                 num_context_turns: int = 10,
                 max_sequence_length: int = 50,
                 *args, **kwargs) -> None:

        super(MatchingPredictor, self).__init__()

        self.num_context_turns = num_context_turns
        self.max_sequence_length = max_sequence_length
        self.model = model

    def __call__(self, batch: Iterable[List[np.ndarray]]) -> List[str]:
        """
        Overrides __call__ method.

        Args:
            batch (Iterable): A batch of one sample, preprocessed, but not padded to ``num_context_turns`` sentences

        Return:
             list of verdict messages
        """
        sample = next(batch)
        try:
            next(batch)
            log.error("It is not intended to use the `%s` with the batch size greater then 1." % self.__class__)
        except StopIteration:
            pass

        batch_buffer_context = []       # [batch_size, 10, 50]
        batch_buffer_context_len = []   # [batch_size, 10]
        batch_buffer_response = []      # [batch_size, 50]
        batch_buffer_response_len = []  # [batch_size]

        preproc_sample = []
        for s in sample:
            preproc_sample.append(s.tolist())

        # # first, need to append expanded context
        # sent_list = preproc_sample[-(self.num_context_turns + 1):-1]
        # if len(sent_list) <= self.num_context_turns:
        #     tmp = sent_list[:]
        #     sent_list = [[0]*self.max_sequence_length] * (self.num_context_turns - len(sent_list))
        #     sent_list.extend(tmp)
        #
        # # second, adding response sentence
        # sent_list.append(preproc_sample[-1])  # sent_list has shape (num_context_turns+1, max_sequence_length)

        # context is already padded/truncated. It needs only to pad at the token-level
        sent_list = zero_pad_truncate(preproc_sample, self.max_sequence_length, pad='post', trunc='post')

        context_sentences = np.array(sent_list[:self.num_context_turns])
        response_sentences = np.array(sent_list[self.num_context_turns:])

        if len(context_sentences) != self.num_context_turns:
            log.error("Number of context sentences should be equal to %s" % self.num_context_turns)
            return ["Number of context sentences should be equal to %s" % self.num_context_turns]

        # format model inputs
        # word indices
        batch_buffer_context += [context_sentences for sent in response_sentences]
        batch_buffer_response += [response_sentence for response_sentence in response_sentences]
        # lens of sentences
        lens = []
        for context in [context_sentences for sent in response_sentences]:
            context_sentences_lens = []
            for sent in context:
                context_sentences_lens.append(len(sent[sent != 0]))
            lens.append(context_sentences_lens)
        batch_buffer_context_len += lens

        lens = []
        for context in [response_sentence for response_sentence in response_sentences]:
            lens.append(len(context[context != 0]))
        batch_buffer_response_len += lens

        y_pred = []
        if len(batch_buffer_context) >= self.model.batch_size:
            for i in range(len(batch_buffer_context) // self.model.batch_size):
                feed_dict = {
                    self.model.utterance_ph: np.array(batch_buffer_context[i * self.model.batch_size:(i + 1) * self.model.batch_size]),
                    self.model.all_utterance_len_ph: np.array(batch_buffer_context_len[i * self.model.batch_size:(i + 1) * self.model.batch_size]),
                    self.model.response_ph: np.array(batch_buffer_response[i * self.model.batch_size:(i + 1) * self.model.batch_size]),
                    self.model.response_len_ph: np.array(batch_buffer_response_len[i * self.model.batch_size:(i + 1) * self.model.batch_size])
                }
                yp = self.model.sess.run(self.model.y_pred, feed_dict=feed_dict)
                y_pred += list(yp[:, 1])
        lenb = len(batch_buffer_context) % self.model.batch_size
        if lenb != 0:
            feed_dict = {
                self.model.utterance_ph: np.array(batch_buffer_context[-lenb:]),
                self.model.all_utterance_len_ph: np.array(batch_buffer_context_len[-lenb:]),
                self.model.response_ph: np.array(batch_buffer_response[-lenb:]),
                self.model.response_len_ph: np.array(batch_buffer_response_len[-lenb:])
            }
            yp = self.model.sess.run(self.model.y_pred, feed_dict=feed_dict)
            y_pred += list(yp[:, 1])
        y_pred = np.asarray(y_pred)
        y_pred = np.reshape(y_pred, (1, len(response_sentences)))  # reshape to [batch_size, 10]

        # return ["The probability that the response is proper continuation of the dialog is {:.3f}".format(y_pred[0])]
        # return ["{:.5f}".format(y_pred[0])]
        return ["{:.5f}".format(v) for v in y_pred[0]]

    def reset(self) -> None:
        pass

    def process_event(self) -> None:
        pass