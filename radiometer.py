from subprocess import Popen, PIPE
import time
from threading import Thread


class ADC(Thread):
    def __init__(self, channels, *, timeout=0.1, app='./ldevio'):
        Thread.__init__(self)
        self.daemon = True
        self.timeout = timeout
        self._channels = channels[:]
        self._channels_str = [str(channel) for channel in self._channels]
        self.voltages = [None] * len(self._channels)
        if max(self._channels) > 7:
            raise ValueError('There is no channel {}'.format(max(self._channels)))
        self._is_running = False
        self._p = Popen([app, str(max(self._channels)+1)], stdin=PIPE, stdout=PIPE)

    def stop(self):
        self._is_running = False

    def run(self):
        self._is_running = True
        try:
            while self._is_running and self._p.poll() is None:
                for index, channel in enumerate(self._channels_str):
                    self._p.stdin.write((channel + '\n').encode('ascii'))
                    self._p.stdin.flush()
                    r = self._p.stdout.readline().strip().decode('ascii').split(maxsplit=1)
                    if r and r[0] == channel:
                        self.voltages[index] = float(r[1])
                    else:
                        self.voltages[index] = None
                time.sleep(self.timeout)
            if not self._is_running:
                self._p.communicate(input=b'-1', timeout=3)
        except (KeyboardInterrupt, SystemExit):
            self._p.communicate(input=b'-1', timeout=3)
            return
