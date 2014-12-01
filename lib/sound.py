import wave
import time
import logging
import pyaudio
import threading

class Sound():

    def __init__(self, path='sounds/peng.wav'):
        logging.debug("init sound object %s" % path)
        self.p = pyaudio.PyAudio()
        self.wf = wave.open(path, 'rb')
        self.stream = self.p.open(
            format=self.p.get_format_from_width(self.wf.getsampwidth()),
            channels=self.wf.getnchannels(),
            rate=self.wf.getframerate(),
            output=True,
            start=False,
            stream_callback=self.playCallback)
        self.loopThread = False
        self.loopExit = False

    def close(self):
        # Stop playing if there is any
        if self.loopThread:
            self.stopLoop()
        else:
            self.stop()
        # Close Stream and Filehandle
        self.stream.close()
        self.wf.close()

    def playCallback(self, in_data, frame_count, time_info, status):
        data = self.wf.readframes(frame_count)
        return (data, pyaudio.paContinue)

    def play(self):
        self.stop()
        self.wf.rewind()
        self.stream.start_stream()

    def loopCallback(self):
        while not self.loopExit:
            if not self.stream.is_active():
                self.play()
            time.sleep(0.2)

    def stop(self):
        if not self.stream.is_stopped():
            logging.debug("stopping stream")
            self.stream.stop_stream()
            logging.debug("stream stopped")

    def loop(self):
        self.loopThread = threading.Thread(target=self.loopCallback)
        self.loopThread.start()

    def stopLoop(self):
        logging.debug("stopping loop of sound object")
        if self.loopThread:
            self.loopExit = True
            logging.debug("stopping sound: join thread")
            self.loopThread.join()
            logging.debug("joined")
            time.sleep(0.3)
        self.stop()
        self.loopThread = False
        self.loopExit = False
        logging.debug("end stopLoop")


if __name__ == '__main__':

    theme = Sound("sounds/theme_sample.wav")
    theme.loop()

    # krach = Sound("sounds/krach.wav")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        theme.stopLoop()

    theme.loop()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        theme.close()
        print "Ciao..."

    # theme.play()
    # time.sleep(2)

    # s = Sound()
    # s.play()
    # time.sleep(1)
    # s.play()
    # time.sleep(1)
    # s.close()
