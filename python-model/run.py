import io
import os
import sys
import json
import time
from subprocess import Popen, PIPE

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

    def signal_ready(self):
        self._sock.send_json({'isReady': True})

    def send(self, start_ts, processing_time, words):
        self._sock.send_json({
            'start_ts': start_ts,
            'processing_time': processing_time,
            'words': words,
        })

    def close(self):
        self._sock.close()


def webm_to_wav(webm):
    # Chromium doesn't support encoding WAV natively so we're stuck with FFMPEG
    cmd = 'ffmpeg -f webm -c:a opus -i pipe:0 -c:a pcm_s16le -ac 1 -ar 16000 -f wav pipe:1'.split()
    proc = Popen(cmd, stdin=PIPE, stdout=PIPE)
    wav, _ = proc.communicate(webm)
    return wav


def main(input_pipe, output_pipe):
    source = ZeroMQSource(input_pipe)
    sink = ZeroMQSink(output_pipe)

    debug('[+] loading processor')
    processor = Wav2Vec2Processor.from_pretrained('facebook/wav2vec2-base-960h')
    debug('[+] loading model')
    model = Wav2Vec2ForCTC.from_pretrained('facebook/wav2vec2-base-960h')

    sink.signal_ready()
    try:
        while True:
            debug('>>> waiting for connection')
            # torchaudio seems to expect complete files so send small parts
            buf = io.BytesIO(source.recv())
            start = time.time()
            debug('[+] converting audio')
            wav = io.BytesIO(webm_to_wav(buf.read()))
            waveform, sample_rate = torchaudio.load(wav)
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
