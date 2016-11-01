import RPi.GPIO as GPIO
import numpy as np
import time

GPIO.setmode(GPIO.BOARD)

from sys import stderr
# def writeErr(s, endl=True):
#     stderr.write(s)
#     if endl:
#         stderr.write('\n')

class Motor(object):
    def __init__(self, spdPin, dirPin, curPin, hz=10000):
        self.pins = spdPin, dirPin, curPin
        GPIO.setup(spdPin, GPIO.OUT)
        self.p = GPIO.PWM(spdPin, hz)

        GPIO.setup(dirPin, GPIO.OUT)
        self.dp = GPIO.PWM(dirPin, 10)
        self.dp.start(0)

        self._isStarted = False
        self.frac = self.pct = 0
        
    def __repr__(self):
        return 'Motor(%d, %d, %d)' % self.pins
    
    def setFrac(self, frac, verbose=False):
        fwd = (frac > 0)
        
        if np.abs(frac) > 1.0:
            from warnings import warn
            warn("Capping motor frac from %s." % frac)
        
        # Bound frac within [-1, 1].
        frac = max(min(frac, 1.0), -1.0)
        
        # Get magnitude as a percent.
        pct = np.abs(frac * 100.0)
        
#         writeErr("Setting duty cycle percent to %s%%." % pct)

        if np.abs(frac) < .01:
#             writeErr('Stopping motor %s' % self)
            self.p.ChangeDutyCycle(0)
            self.stop()
        else:
            if verbose: print 'Setting frac to %f.' % frac
            if not self._isStarted:
                self.p.start(pct)
                self._isStarted = True
            else:
                self.p.ChangeDutyCycle(pct)
            if fwd:
#                 writeErr('Running %s forward.' % self)
                self.dp.ChangeDutyCycle(100)
            else:
#                 writeErr('Running %s backward.' % self)
                self.dp.ChangeDutyCycle(0)

        self.frac = frac
        self.pct = pct
    
    def stop(self):
        self.p.stop()
        self._isStarted = False

    def ramp(self, stop, start=None, duration=1.0, increment=.01, verbose=False):
        if start is None:
            start = self.frac
        nsteps = duration / increment
        for frac in np.linspace(start, stop, nsteps):
            time.sleep(increment)
            self.setFrac(frac, verbose=verbose)
 

class MotPair(object):
    
    def __init__(self, ml, mr):
        self._isStarted = False
        self.fracs = ml.frac, mr.frac
        self.motors = ml, mr
    
    def setFracs(self, fracs, verbose=False):
        for m, f in zip(self.motors, fracs):
            m.setFrac(f, verbose=verbose)

    def stop(self):
        for m in self.motors:
            m.stop()
    
    def ramp(self, stops, starts=None, duration=1.0, increment=.01, verbose=False):
        if starts is None:
            starts = self.fracs
        nsteps = duration / increment
        for fl, fr in zip(
                np.linspace(starts[0], stops[0], nsteps),
                np.linspace(starts[1], stops[1], nsteps)
            ):
            time.sleep(increment)
            self.setFracs((fl, fr), verbose=verbose)

class Encoder(object):
    
    def __init__(self, intPin, aPin, bPin):
        self.intPin = intPin
        self.wavePints = aPin, bPin
        for pin in intPin, aPin, bPin:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            
        GPIO.add_event_detect(intPin, GPIO.BOTH, callback=self.interruptCallback)
            
    def interruptCallback(self):
        print "Got interrupt."
    
if __name__ == '__main__':
    print 'motor.main'
    try:
        enc = Encoder(9, 10, 22)
        while True:
            time.sleep(.5)
            print 'Slept.'
    except KeyboardInterrupt:
        GPIO.cleanup()
    GPIO.cleanup()
    