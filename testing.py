#import serial
from os import system, makedirs
from os.path import dirname, abspath, exists
from time import sleep
import unittest
import serialFinder
from config import baudRate, systemOut
port = serialFinder.port

here = dirname(abspath(__file__))


def msg(text):
    print ">>>>>>>>>>>>>>>", text, "<<<<<<<<<<<<<<<<<"




#port = "/dev/null"
msg("port is %s" % port)
board = "arduino:avr:mega"


def stripOutput(stdout):
    ignoreStrings = [
        "Loading configuration",
        "Initializing packages",
        "Preparing boards",
        "Sketch uses",
        "Global variables use",
        ]
    for l in stdout.split('\n'):
        isBad = False
        for bad in ignoreStrings:
            if bad in l or len(l.strip()) == 0:
                isBad = True
        if not isBad:
            print l
    

def verify(sketchName):
    return False
    cmd = "arduino --port %s --board %s" % (port, board)
    cmd += " --verify %s/%s/%s.ino"  % (here, sketchName, sketchName)
    
    stdout, status = systemOut(cmd.split(' '), sayCmd=False, giveStatus=True)
    if status:
        raise VerifyError
    else:
        stripOutput(stdout)
        return  status


def upload(sketchName):
    
    cmds = []
    cmds.append("cd %s/%s/" % (here, sketchName))
    cmds.append("make")
    cmds.append("make upload")
    
    from os import system
    system(" && ".join(cmds))
    

def monitor(testName):
    print "To exit the serial monitor, do \"Ctrl+a, k, y\"."
    #cmd = "gnome-terminal --disable-factory --command \"screen %s %s\" 2>&1 | grep -v \"format string\"" % (port, baudRate)
    cmd = "cd %s/%s && make monitor" % (here, testName)
    system(cmd)


def printInstructions(instructions):
    prefix = " >>>     "
    lines = instructions.split('\n')
    print "Inspection instructions:"
    for line in lines:
        print "%s %s" % (prefix, line.replace('\n', ''))


def yn(prompt):
    '''stackoverflow.com/questions/3041986
    raw_input returns the empty string for "enter"'''
    yes = set(['yes','y', 'ye'])
    no = set(['no','n'])
    print prompt
    while True:
        choice = raw_input().lower()
        if choice in yes:
            return True
        elif choice in no:
            return False
        else:
            print "Please respond with '[y]es' or '[n]o'."


class InspectionError(RuntimeError):
    pass


class UploadError(RuntimeError):
    pass


class VerifyError(RuntimeError):
    pass


def makeMakefiles(testName):
    template = open(here+"/Makefile.template").read()
    template = template.format(here + "/testSketch", here)
    
    f = open(here + "/%s/Makefile"%testName, "w")
    f.write(template)
    f.close()
    
    systemOut(["cp", "%s/avrdude.conf" % here, "%s/%s/" % (here, testName)])


class Sketch:
    '''Contains and places Arduino code for compilation and uploading.'''
    
    def __init__(self):
        self.instructions = None
        self.code = None
        self.madeFiles = False
    
    def getCode(self):
        return self.code
    
    def getInstructions(self):
        return self.instructions
    
    def makeFiles(self):
        sketchDir = here+'/testSketch'
        if not exists(sketchDir): makedirs(sketchDir)
        f = open(sketchDir+'/testSketch.ino', 'w')
        f.write(self.getCode())
        f.close()
        
        makeMakefiles('testSketch')
    
    def verify(self):
        return verify('testSketch')
            
    def upload(self):
        return upload('testSketch')

    def doTest(self, doMonitor=True):
        self.makeFiles()
        self.verify()
        out = self.upload()
        if doMonitor:
            printInstructions(self.instructions)
            monitor('testSketch')
            printInstructions(self.instructions)
            monitorPassed = yn("Did the test pass inspection?")
            if not monitorPassed:
                raise InspectionError
        return out
 
includes = '''
#include <Adafruit_Sensor.h>
#include <Adafruit_LSM303_U.h>
#include <Adafruit_L3GD20_U.h>
#include <Adafruit_9DOF.h>
#include <Wire.h>
#include <Servo.h>
#include <gunnar.h>'''
baseCode = includes + '''
Gunnar gunnar;

// Interrupt Service Routines
void doEncoder0()
{
    gunnar.encoder0.update();
}

void doEncoder1()
{
    gunnar.encoder1.update();
}

void setup()
{
    Serial.begin(BAUDRATE);
    gunnar.init();
    
    // Turn on pullup resistors on interrupt lines:
    pinMode(encoder0Int, INPUT_PULLUP);
    pinMode(encoder0Int, INPUT_PULLUP);
    attachInterrupt(0, doEncoder0, CHANGE);
    attachInterrupt(1, doEncoder1, CHANGE);
}'''

class TestGunnar(unittest.TestCase):
    '''Upload various sketches. Manually check the behavior.'''

    def test_positionPID(self):
        sk = Sketch()
        sk.code = includes + '''
Gunnar gunnar;

// Interrupt Service Routines
void doEncoder0()
{
    gunnar.encoder0.update();
}

void doEncoder1()
{
    gunnar.encoder1.update();
}

// Test the motors, encoders, and PID control of position.
void setup() {
    
    Serial.begin(9600);
    gunnar.init();
    gunnar.sonarTask.active = false;
    
    // Turn on pullup resistors on interrupt lines:
    pinMode(encoder0Int, INPUT_PULLUP);
    pinMode(encoder0Int, INPUT_PULLUP);
    attachInterrupt(0, doEncoder0, CHANGE);
    attachInterrupt(1, doEncoder1, CHANGE);
    
    gunnar.controlledMotors.stop();
    gunnar.sensors.disableServos();
}

void sayPosition()
{
    Serial.print("Positions are (");
    Serial.print(gunnar.encoder0.position);
    Serial.print(", ");
    Serial.print(gunnar.encoder1.position);
    Serial.println(") ticks.");
}

void loop()
{
    Serial.println("Begin position PID control test loop.");
    gunnar.controlledMotors.go(100);
    gunnar.taskDriver.run(10L*1000L*1000L);
    sayPosition();
    gunnar.controlledMotors.go(-300);
    gunnar.taskDriver.run(10L*1000L*1000L);
    sayPosition();
    gunnar.controlledMotors.go(200);
    gunnar.taskDriver.run(10L*1000L*1000L);
    sayPosition();
    gunnar.controlledMotors.stop();
    delay(3000);
}'''
        sk.instructions = '''
0. Ensure that green activity switch is on.
1. Motors will run by control to several positions,
   given 10 seconds to get there.
   then declare what position they think they're at.
2. Assert that they don't run forever,
   and that the set points are reached expeditiously.
3. If ambitions, measure the distances traveled and assert that they are
   100 cm, -300 cm, and 200 cm.
4. After running to these positions, the motors will stop for 3 seconds.'''
        sk.doTest()
        
    def test_daguMotorBoard(self):
        sk = Sketch()
        sk.code = includes + '''
const int daguPwmPin1 = 11;
const int daguPwmPin2 = 12;

const int daguDirPin1 = 44;
const int daguDirPin2 = 45;

const int daguCurPin1 = A0;
const int daguCurPin2 = A1;

void setup()
{
    Serial.begin(9600);
    Serial.println("dagu motor board test");
    pinMode(daguPwmPin1, OUTPUT);
    pinMode(daguPwmPin2, OUTPUT);
    pinMode(daguDirPin1, OUTPUT);
    pinMode(daguDirPin2, OUTPUT);
    pinMode(daguCurPin1, INPUT);
    pinMode(daguCurPin2, INPUT);
}

void rampUpDown(boolean direction)
{
    
    Serial.print("Writing "); Serial.print(direction);
    Serial.print(" to pin "); Serial.print(daguDirPin1); Serial.println(".");
    Serial.print("Writing "); Serial.print(direction);
    Serial.print(" to pin "); Serial.print(daguDirPin2); Serial.println(".");

    digitalWrite(daguDirPin1, direction);
    digitalWrite(daguDirPin2, direction);
    
    uint8_t speed;

    for(speed=0; speed<255; speed++)
    {
        Serial.print("increasing: ");
        Serial.print(speed);
        Serial.print(" ");
        Serial.print(analogRead(daguCurPin1));
        Serial.print(" ");
        Serial.println(analogRead(daguCurPin2));
        analogWrite(daguPwmPin1, speed);
        analogWrite(daguPwmPin2, speed);
        delay(4);
    }
    
    for(speed=254; speed>=1; speed--)
    {
        Serial.print("decreasing: ");
        Serial.print(speed);
        Serial.print(" ");
        Serial.print(analogRead(daguCurPin1));
        Serial.print(" ");
        Serial.println(analogRead(daguCurPin2));
        analogWrite(daguPwmPin1, speed);
        analogWrite(daguPwmPin2, speed);
        delay(4);
    }  
}

void loop()
{
    rampUpDown(HIGH);
    rampUpDown(LOW);
}'''
        sk.instructions = '''
1. Let motors ramp up, then down twice.
2. Motors should go in opposite directions from each other at the same time.
3. Each motor should go first in one direction, then the other.'''
        sk.doTest()
        
    def test_motorObjectMovement(self):
        sk = Sketch()
        sk.code = includes + r'''
Gunnar gunnar;

void setup()
{
    Serial.begin(9600);
    gunnar.init();
}

void ramp(int start, int end)
{
    int i;
    Serial.print("ramp from ");
    Serial.print(start); Serial.print(" from "); Serial.print(end); Serial.println(".");
    
    if(start < end)
    {
        for(i=start; i<end; i++)
        {
            gunnar.motor1.setSpeed(i);
            gunnar.motor2.setSpeed(i);
            interruptibleDelay(4);
        }
    }
    else
    {
        for(i=start; i>end; i--)
        {
            gunnar.motor1.setSpeed(i);
            gunnar.motor2.setSpeed(i);
            interruptibleDelay(4);
        }
    }
    
}

void loop()
{
    ramp(0, 255);
    delay(500);
    ramp(255, -95);
    delay(500);
    ramp(-95, 0);
    gunnar.motor1.stop();
    gunnar.motor2.stop();
    delay(3000);
}'''
        sk.instructions = '''
1. Motors should ramp to a fast forward speed, then back to 0.
2. Motors should ramp to a slow reverse speed, then back to 0.
3. Repeats after a 3 second delay.'''
        sk.doTest()
        
    def test_encodersNoMotors(self):
        sk = Sketch()
        sk.code = includes + '''
// GLOBALS
Encoder encoder0;
Encoder encoder1;

void doEncoder0()
{
    encoder0.update();
}

void doEncoder1()
{
    encoder1.update();
}

const boolean explore = false;
// Test the motors and encoders.
void setup() {
    if(explore) // TODO: This is cruft.
    {
        Serial.begin(9600);
            
        boolean a = LOW;
        boolean b = LOW;
        
        uint8_t newStatus = a + 2*b;
        
        // backward looks like 0, 1, 2, 3
        // forward  looks like 0, 3, 2, 1
        
        int position = 0;
        uint8_t waveStatus = 2;
        
        switch(waveStatus)
        {
            case 0 :
                Serial.println("case 0");
                if(newStatus == 1)
                    position--;
                else
                    position++;
                break;
            case 1 :
                Serial.println("case 1");
                if(newStatus == 2)
                    position--;
                else
                    position++;
                break;
            case 2 :
                Serial.println("case 2");
                if(newStatus == 3)
                    position--;
                else
                    position++;
                break;
            case 3 :
                Serial.println("case 3");
                if(newStatus == 1)
                    position--;
                else
                    position++;
                break;
            default :
                break; // Should never reach here.
        }
        
        Serial.print("newStatus=");
        Serial.println(newStatus);
        Serial.print("position=");
        Serial.println(position);
    }
    else
    {
        Serial.begin(9600);
        
        encoder0.init(encoder0PinA, encoder0PinB, NULL);
        encoder1.init(encoder1PinA, encoder1PinB, NULL);
            
        // Turn on pullup resistors on interrupt lines:
        pinMode(encoder0Int, INPUT_PULLUP);
        pinMode(encoder1Int, INPUT_PULLUP);
        attachInterrupt(0, doEncoder0, CHANGE);
        attachInterrupt(1, doEncoder1, CHANGE);
        
        pinMode(PIN_ACTIVITYSWITCH, INPUT);
    }
}


void loop()
{
    if(explore)
    {
    }
    else
    {
        Serial.print(micros());
        Serial.print(", ");
        Serial.print(encoder0.getSpeed());
        Serial.print(", ");
        Serial.print(encoder1.getSpeed());
        Serial.print(", ");
        Serial.print(encoder0.position);
        Serial.print(", ");
        Serial.print(encoder1.position);
        Serial.print(", ");
        Serial.print(encoder0.trueUpdateDelay);
        Serial.print(", ");
        Serial.print(encoder1.trueUpdateDelay);
        Serial.println("");
        delayMicroseconds(1000000);
    }
}'''
        sk.instructions = '''
1. Push left and right treads independently forward and back.
2. Verify that the proper columns in the serial output go up and then go back down.
3. Make sure they can go into both positive and negative values.'''
        sk.doTest()
                
    def test_servos(self):
        sk = Sketch()
        sk.code = includes + '''
Servo tiltServo; 
Servo panServo;

int pos = 0;

void setup() 
{ 
  Serial.begin(BAUDRATE);
  Serial.println("SERVO TEST");
  tiltServo.attach(TILTSERVOPIN);
  panServo.attach(PANSERVOPIN);
} 


const int MAXPOS = 120;
const int MINPOS = 40;
void loop() 
{ 
  Serial.println("          [          ]");
  Serial.print("Tilt test: ");
  for(pos = MINPOS; pos < MAXPOS; pos += 1)
  {
    tiltServo.write(pos);
    delay(15);
    if(pos%((MAXPOS-MINPOS)/5) == 0)
      Serial.print("|");
  } 
  for(pos = MAXPOS; pos>=MINPOS+1; pos-=1)
  {                                
    tiltServo.write(pos);
    delay(15);
    if(pos%((MAXPOS-MINPOS)/5) == 0)
        Serial.print("|");
  }
  Serial.println(" done.");

  Serial.println("          [         ]");
  Serial.print("Pan test:  ");
  for(pos = MINPOS; pos < MAXPOS; pos += 1)
  {
    panServo.write(pos);
    delay(25);
    if(pos%((MAXPOS-MINPOS)/5) == 0)
      Serial.print("|");
  } 
  for(pos = MAXPOS; pos>=MINPOS+11; pos-=1)
  {
    panServo.write(pos);
    delay(25);
    if(pos%((MAXPOS-MINPOS)/5) == 0)
      Serial.print("|");
  } 
  Serial.println(" done.");
}'''
        sk.instructions = '''
1. Verify that servos pan when output says they should be, and same for tilting.
2. Verify that movement is centered.'''
        sk.doTest()
        
    def test_servoObjects(self):
        sk = Sketch()
        sk.code = baseCode + '''
void loop() 
{ 
    int8_t angles[] = {-90, 0, 90};
    for(uint8_t i=0; i<3; i++)
    {
        int8_t angle = angles[i];
        Serial.print("angle=");
        Serial.println(angle);
        gunnar.sensors.setPan(angle);
        gunnar.sensors.setTilt(angle);
        delay(3000);
    }
}'''
        sk.instructions = '''
0. Ensure that battery power is available.
1. Servos will go to -90 degrees with calibrated offset, and pause for 3 seconds.
2. Servos will go to 0   degrees with calibrated offset, and pause for 3 seconds.
3. Servos will go to +90 degrees with calibrated offset, and pause for 3 seconds.'''
        sk.doTest()

    def test_servoCenter(self):
        sk = Sketch()
        sk.code = includes + '''
Servo tiltServo; 
Servo panServo;

void setup() 
{ 
  Serial.begin(BAUDRATE);
  Serial.println("SERVO CENTERING TEST");
  tiltServo.attach(TILTSERVOPIN);
  panServo.attach(PANSERVOPIN);
} 

void loop() 
{ 
    uint8_t angles[] = {0, 90, 180};
    for(uint8_t i=0; i<3; i++)
    {
        uint8_t angle = angles[i];
        Serial.print("angle=");
        Serial.println(angle);
        panServo.write(angle);
        tiltServo.write(angle);
        delay(3000);
    }
}'''
        sk.instructions = '''
0. Ensure that battery power is available.
1. Servos will go to 0   degrees, and pause for 3 seconds.
2. Servos will go to 90  degrees, and pause for 3 seconds.
3. Servos will go to 180 degrees, and pause for 3 seconds.'''
        sk.doTest()
        
    def test_turn(self):
        sk = Sketch()
        sk.code = baseCode + '''
void loop()
{ 
    int angles[] = {-90, 135, -45};
    for(uint8_t i=0; i<3; i++)
    {
        int angle = angles[i];
        Serial.print("angle=");
        Serial.println(angle);
        gunnar.controlledMotors.stop();
        gunnar.controlledMotors.turn(angle);
        gunnar.sonarTask.active = false;
        gunnar.taskDriver.run(32L*1000L*1000L);
        gunnar.controlledMotors.stop();
        gunnar.sensors.disableServos();

    }
    //gunnar.controlledMotors.stop();
    Serial.println("Repeating in 3 seconds...");
    gunnar.taskDriver.run(3L*1000L*1000L);
}'''
        sk.instructions = '''
0. Ensure that battery power is available,
   and that the green activity switch is on.
1. Gunnar will turn -90  degrees.
2. Gunnar will turn +135 degrees.
3. Gunnar will turn -45  degrees.
4. Gunnar will stop for 3 seconds.'''
        sk.doTest()
        
    @classmethod
    def tearDownClass(cls):
        sk = Sketch()
        sk.code = '''void setup() {                
  ;
}

void loop() {
  ;
}'''
        sk.doTest(doMonitor=False)
        
if __name__=="__main__":
    if False:
        sk = Sketch()
        sk.code = baseCode + '''
            void loop()
            {
                Serial.println("Repeating in 3 seconds...");
                delay(3000);
            }'''
        sk.instructions = ""
        sk.doTest(doMonitor=True)
    else:
        unittest.main(verbosity=1000000)