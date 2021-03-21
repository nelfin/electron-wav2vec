import os
import sys
import json
import time
import socket

import torch
import torchaudio
# Example model:
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor


def debug(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)


class SocketSource(object):
    def __init__(self, input_stream):
        host, port = input_stream.split(':')
        self._lsock = socket.socket()
        self._lsock.bind((host, int(port)))
        self._lsock.listen(1)
        self._sock = None

    def accept(self):
        sock, addr = self._lsock.accept()  # wait for connection
        self._sock = sock

    def read(self, num_bytes):
        buf = self._sock.recv(num_bytes)
        debug(f'recv({num_bytes}) = {len(buf)}')
        return buf

    def seek(self, offset, whence):
        debug(f'seek({offset}, {whence})')
        return False

    def close(self):
        debug('shutting down socket')
        self._sock.shutdown(socket.SHUT_RDWR)
        self._sock.close()


class FileSource(object):
    def __init__(self, fn):
        self._file = open(fn, 'rb')

    def accept(self):
        return

    def read(self, num_bytes):
        buf = self._file.read(num_bytes)
        debug(f'recv({num_bytes}) = {len(buf)}')
        return buf

    def seek(self, offset, origin):
        whence = 1 if origin == miniaudio.SeekOrigin.CURRENT else 0
        debug(f'seek({offset}, {whence})')
        self._file.seek(offset, whence)
        return True

    def file(self):
        return self._file

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._file.close()


class FileSink(object):
    def __init__(self, output_fn):
        self._file = open(output_fn, 'wb')

    def send(self, start_ts, processing_time, words):
        jsonl = json.dumps({
            'start_ts': start_ts,
            'processing_time': processing_time,
            'words': words,
        })
        self._file.write(jsonl.encode('utf-8') + b'\n')
        self._file.flush()

    def close(self):
        self._file.close()


def main(input_pipe, output_pipe):
    debug('[+] loading processor')
    processor = Wav2Vec2Processor.from_pretrained('facebook/wav2vec2-base-960h')
    debug('[+] loading model')
    model = Wav2Vec2ForCTC.from_pretrained('facebook/wav2vec2-base-960h')

    source = SocketSource(input_pipe)
    sink = FileSink(output_pipe)
    try:
        debug('>>> waiting for connection')
        source.accept()
        start = time.time()
        # torchaudio seems to expect complete files so send small parts
        waveform, sample_rate = torchaudio.load(source)
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
    main(os.getenv('INPUT_PIPE', 'localhost:51234'), os.getenv('OUTPUT_PIPE', '/tmp/commands-out'))
