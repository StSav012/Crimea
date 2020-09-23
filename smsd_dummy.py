import smsd


class Motor(smsd.Motor):
    def __init__(self, device, microstepping_mode=smsd.MicrosteppingMode.SINGLE, speed=90, ratio=1.):
        smsd.Motor.__init__(self, device, microstepping_mode=microstepping_mode, speed=speed, ratio=ratio)

    def _do(self, cmd):
        return True

    def open(self, device=None):
        return
