#!/usr/bin/env python
from time import sleep

from gunnar.robot import GunnarCommunicator
import rospy
from std_msgs.msg import Float32

class ResettableRate(rospy.Rate):
    
    def reset(self):
        self.last_time = rospy.rostime.get_rostime()
        
    def remainingSeconds(self):
        return self.remaining().to_sec()
    
    def past(self):
        return self.remainingSeconds() <= 0

class Gunnar(object):
    def __init__(self):
        self._spds = [0, 0]
        self.robotSpeedsStr = ''
        self.rate = rospy.get_param("~rate", 10)
        self.speedSetRate = ResettableRate(self.rate)
        self.communicator = GunnarCommunicator()
        rospy.loginfo('Set speedSet rate at %s Hz.' % (1./self.speedSetRate.sleep_dur.to_sec(),))

    def stop(self):
        self.spds = [0, 0]

    @property
    def spds(self):
        return list(self._spds)

    @spds.setter
    def spds(self, twoList):
        if self.speedSetRate.past() and (
             twoList[0] != self.spds[0] or twoList[1] != self.spds[1]
             ):
            self.speedSetRate.reset()
            self._spds = twoList
            self.cmdSetSpeeds(twoList[0], twoList[1])
        
    def cmdSetSpeeds(self, a, b):
        self.communicator.speedSet(a, b)
        self.robotSpeedsStr = "(%.1f, %.1f)." % (a, b)

    def spinOnce(self):
        self.communicator.loopOnce()
        
class VtargetListener(Gunnar):
    
    def __init__(self):
        rospy.init_node('arduino_driver', log_level=rospy.DEBUG)
        super(VtargetListener, self).__init__()
        rospy.loginfo('Begin VtargetListener init.')
        rospy.Subscriber('/lwheel_vtarget', Float32, self.lwheelCallback)
        rospy.Subscriber('/rwheel_vtarget', Float32, self.rwheelCallback)
        rospy.loginfo('Done with VtargetListener init.')
        print 'Done with VtargetListener init.'
        
    def lwheelCallback(self, data):
#         rospy.logdebug('got left wheel data %s' % data.data)
        self.spds = [data.data, self.spds[1]]
        
    def rwheelCallback(self, data):
#         rospy.logdebug('got right wheel data %s' % data.data)
        self.spds = [self.spds[0], data.data]
        
    def spin(self):
        r = rospy.Rate(self.rate)
        idle = rospy.Rate(10)
        while not rospy.is_shutdown():
            # Time per loop iteration will be max(ts, tr, ti), where ts, tr,
            # and ti are the duration of the spin code, rate period, and idle
            # period, respectively. That is, the period will strive to match the
            # slower of the two Rates, but might be a longer if the spin takes
            # longer.
            #
            # This doesn't clarify why an idle is useful, rather than just using
            # a slower rate.
            self.spinOnce()
            r.sleep()
            idle.sleep()
        
def main():
    listener = VtargetListener()
    listener.spin()

if __name__ == "__main__":
    main()
