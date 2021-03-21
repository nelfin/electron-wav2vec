import io
import os
import sys
import json
import time
import socket

import zmq
import torch
import torchaudio
# Example model:
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor


def debug(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


class ZeroMQSource(object):
    def __init__(self, input_stream):
        self._ctx = zmq.Context.instance()
        self._sock = self._ctx.socket(zmq.SUB)
        self._sock.set(zmq.SUBSCRIBE, b'')
        self._sock.bind(input_stream)

    def recv(self):
        buf = self._sock.recv()
        return buf

    def close(self):
        debug('[+] shutting down socket')
        self._sock.close()


class ZeroMQSink(object):
    def __init__(self, output_stream):
        self._ctx = zmq.Context.instance()
        self._sock = self._ctx.socket(zmq.PUB)
        self._sock.bind(output_stream)

    def send(self, start_ts, processing_time, words):
        jsonl = json.dumps({
            'start_ts': start_ts,
            'processing_time': processing_time,
            'words': words,
        })
        self._sock.send_json(jsonl)

    def close(self):
        self._sock.close()


def main(input_pipe, output_pipe):
    debug('[+] loading processor')
    processor = Wav2Vec2Processor.from_pretrained('facebook/wav2vec2-base-960h')
    debug('[+] loading model')
    model = Wav2Vec2ForCTC.from_pretrained('facebook/wav2vec2-base-960h')

    source = ZeroMQSource(input_pipe)
    sink = ZeroMQSink(output_pipe)
    try:
        while True:
            debug('>>> waiting for connection')
            # torchaudio seems to expect complete files so send small parts
            buf = io.BytesIO(source.recv())
            start = time.time()
            waveform, sample_rate = torchaudio.load(buf)
            waveform = waveform[0]  # Wav2Vec2Processor expects mono 16kHz audio
            debug('[+] input_values')
            input_values = processor(waveform, sampling_rate=sample_rate, return_tensors='pt').input_values
            debug('[+] logits')
            logits = model(input_values).logits
            debug('[+] predicted_ids')
            predicted_ids = torch.argmax(logits, dim=-1)
            debug('[+] transcription')
            transcription = processor.batch_decode(predicted_ids)[0]
            duration = time.time() - start
            sink.send(start, duration, transcription)
    finally:
        source.close()
        sink.close()


if __name__ == '__main__':
    main(os.getenv('AUDIO_STREAM', 'ipc:///tmp/audio-in'),
         os.getenv('COMMANDS_STREAM', 'ipc:///tmp/commands-out'))
