#!/usr/bin/python

import os
import sys
import glob
import curses
import locale
import random
import logging
import string
import threading
import time
import math
from configparser import ConfigParser

# Change working directory to the file directory
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# setup log file to subdir
logging.basicConfig(filename='log/error.log', level=logging.DEBUG,
                    format='%(levelname)8s - %(asctime)s: %(message)s')


# Catch stderr and create log messages...
class StderrToHandler(object):
    def __init__(self, logger=None):
        self.logger = logger or logging
        self._buffer = ''

    def flush(self):
        pass

    def write(self, msg):
        if not isinstance(msg, str):
            msg = str(msg)
            self._buffer += msg
        if msg.endswith("\n"):
            logger.warning(self._buffer.rstrip())
            self._buffer = ''

#sys.stderr = StderrToHandler()


sys.path.append("./lib")

from sound import Sound
from botComm import BotComm

locale.setlocale(locale.LC_ALL, "")

screen = None
inp = None
################################################################################
# HELPER FUNCTIONS
################################################################################

def getFromFile(fileName):
    # f = codecs.open("./objects/" + fileName + ".txt", 'r', "utf-8")
    f = open(fileName, 'r')
    #content = f.read().decode('utf-8')
    content = f.read()
    signsArray = []
    for line in content.split("\n"):
        signsArray.append(line)
    return signsArray


# ################################################################################
# OBJECT CLASS AND CHILDS
################################################################################

class Object(object):
    objects = []
    stdSpeed = 2

    def __init__(self, game, coords=None, signs=None, speed=None, color=None, signsArray=[], switchSignsTime=None):
        self.game            = game
        self.coords          = coords
        self.signs           = signs
        self.color           = color
        self.startTime       = game.time
        self.signsArray      = signsArray
        self.switchSignsTime = switchSignsTime

        if speed is None:
            self.speed = random.randint(
                Object.stdSpeed, Object.stdSpeed * 2)
        else:
            self.speed = speed

        Object.objects.append(self)

        if len(signsArray) > 0:
            self.currentSigns = 0
            self.signs = signsArray[0]

        self.info = {}
        self.info['maxHeight']  = len(signs)
        self.info['rHeight']    = (len(signs) - 1)//2

        tmp  = []
        for line in signs:
            tmp.append(len(line))

        self.info['maxWidth']   = max(tmp)
        self.info['rWidth']     = (self.info['maxWidth'] - 1)//2


    def setRandomXPos(self, output, y=None):
        if y is None:
            y = 0
        x = random.randint(
            2 + self.info['rWidth'], output.fieldSize[0] - 2 - self.info['rWidth'])
        self.coords = (x, y)


    def getPosArray(self):
        posArray = []
        x, y = self.getMapCoords()
        # for i, width in enumerate(self.info["widths"]):
        #    for j in range(width):
        #        posArray.append((x - (width - 1)/2 + j, y - self.info["rHeight"] + i))
        for i, line in enumerate(self.signs):
            py = y - self.info['rHeight'] + i
            for j, sign in enumerate(line):
                if sign != " ":
                    px = x - self.info['rWidth'] + j
                    posArray.append((px, py))

        return posArray

    def check(self):
        if len(set(self.getPosArray()).intersection(self.game.spaceShip.getPosArray())) > 0:
            try:
                Object.objects.remove(self)
            except ValueError as e:
                pass
            self.collision()

    def collision(self):
        pass

    def getMapCoords(self):
        return (self.coords[0], self.coords[1] + (self.game.time - self.startTime) // self.speed)

    def draw(self, output):
        x, y = self.getMapCoords()

        if y > output.fieldSize[1] + self.info['rHeight']:
            Object.objects.remove(self)
            return

        if y < -10:
            Object.objects.remove(self)
            return

        if len(self.signsArray) > 0:
            if self.game.time % self.switchSignsTime == 0:
                self.currentSigns += 1
                self.currentSigns = self.currentSigns % len(self.signsArray)
                self.signs = self.signsArray[self.currentSigns]


        for i, line in enumerate(self.signs):
            py = y - self.info['rHeight'] + i

            if py <= output.fieldSize[1] and py >= 0:
                for j, sign in enumerate(line):
                    if sign != " ":
                        px = x - self.info['rWidth'] + j
                        logging.debug("FFFF %s %s", self.info['rHeight'], self.info['rWidth'])
                        output.addSign((px, py), sign, field = True, color = self.color)
            #py = y - (len(self.signs) - 1)/2 + i
            #if py <= output.fieldSize[1] and py >= 0:
            #    output.addSign((x - (len(line) - 1)/2, py), line, field = True, color = self.color)



class Shoot(Object):
    soundShooting   = None
    soundCollision  = None
    lastStartTime   = 0
    diffBetween     = 15
    def __init__(self, game, **args):
        logging.debug("init Shoot")
        if Shoot.lastStartTime > game.time - Shoot.diffBetween:
            return

        Shoot.lastStartTime = game.time

        args["signs"] = getFromFile("./objects/shoot.txt")
        args["color"] = 2
        args["speed"] = 1
        Sound.play(Shoot.soundShooting)
        super(Shoot, self).__init__(game, **args)

    def getMapCoords(self):
        return (self.coords[0], self.coords[1] - (self.game.time - self.startTime) // self.speed)

    def check(self):
        for o in Object.objects:
            if isinstance(o, Obstacle) or isinstance(o, Goody):
                if len(set(self.getPosArray()).intersection(o.getPosArray())) > 0:
                    Object.objects.remove(o)
                    Object.objects.remove(self)
                    Sound.play(Shoot.soundCollision)
                    break


class Obstacle(Object):
    obstacles   = []
    cSpaceship  = None

    def collision(self):
        if not self.game.spaceShip.blinking:
            Sound.play(Obstacle.cSpaceship)
            self.game.lifeLost()


    def __init__(self, game, **args):
        if "signs" not in args:
            i = random.randint(0, len(Obstacle.obstacles) - 1)
            args["signs"] = getFromFile(Obstacle.obstacles[i])
            args["color"] = Obstacle.color
        super(Obstacle, self).__init__(game, **args)



class Goody(Object):
    types       = []
    cSpaceship  = None
    portion     = None
    volume      = None
    generateT   = None

    def collision(self):
        Sound.play(Goody.cSpaceship)
        self.game.status['ml']    += Goody.portion * Goody.types[self.type]["factor"]
        for i in range(Goody.types[self.type]["factor"]):
            self.game.status['goodies'].append(self.type)
        self.game.status['count'] += 1

        if self.game.robot is not None:
            self.game.robot.pourBottle(Goody.types[self.type]["arduino"], Goody.portion * Goody.types[self.type]["factor"])
        if self.game.status['ml'] >= Goody.volume:
            self.game.full()

    def __init__(self, game, **args):
        self.type = self.getNextGoodyType(game.status["goodies"])

        args["signs"] = getFromFile(Goody.types[self.type]["design"])
        args["color"] = Goody.types[self.type]["color"]

        super(Goody, self).__init__(game, **args)

    def getNextGoodyType(self, collectedGoodies):
        #return random.randint(0, len(Goody.types) - 1)


        weights = [4096] * len(Goody.types)
        # for i, wGoody in enumerate(Goody.types):
        #     if wGoody['category'] == "A":
        #         weights[i] = 4096
        #     else:
        #         weights[i] = 8192


        # for goody in collectedGoodies:
        #     cat = Goody.types[goody]['category']
        #     for i, wGoody in enumerate(Goody.types):
        #         if cat == "A":
        #             if wGoody['category'] == "A" and i != goody:
        #                 weights[i] = weights[i]/4
        #             if i == goody:
        #                 weights[i] = weights[i]*2
        #         elif cat == "N":
        #             if wGoody['category'] == "N" and i != goody:
        #                 weights[i] = weights[i]/2


        #         if Goody.types[wGoody]['category'] == cat

        if Goody.generateT:
            if Goody.generateT == "N":
                for i, wGoody in enumerate(Goody.types):
                    if wGoody['category'] != "N":
                        weights[i] = 0
            if Goody.generateT == "A":
                for i, wGoody in enumerate(Goody.types):
                    if wGoody['category'] != "A":
                        weights[i] = 0


        t = random.randint(0, sum(weights))

        s = 0
        for i in range(len(weights)):
            s = s + weights[i]
            if t <= s:
                return i


class SpaceShip(Object):
    design  = getFromFile("./objects/spaceShip.txt")
    designArray = []
    color   = None
    blinkColor = 2
    def __init__(self, game, **args):
        if "signs" not in args:
            args["signs"] = getFromFile(SpaceShip.design)
            signsArray = []
            for design in SpaceShip.designArray:
                signsArray.append(getFromFile(design))
            args["signsArray"] = signsArray
            args["color"] = SpaceShip.color
            args["switchSignsTime"] = 10
            self.switchBlinkTime = 8
            self.switchBlinkDuration = 50
            self.blinking = False
        super(SpaceShip, self).__init__(game, **args)

    def getMapCoords(self):
        return (self.coords[0], self.coords[1])

    def check(self):
        if self.blinking:
            if self.blinkTime % self.switchBlinkTime == 0:
                if self.blinkTime > self.switchBlinkDuration:
                    self.color, self.blinkColor = self.orgColor, self.orgBlinkColor
                    self.blinking = False
                else:
                    self.color, self.blinkColor  = self.blinkColor, self.color
            self.blinkTime += 1

    def blink(self):
        self.orgColor, self.orgBlinkColor = self.color, self.blinkColor
        self.blinkTime = 0
        self.blinking = True






################################################################################
# OUTPUT CLASSES
################################################################################

class Output(object):
    statusWidth = 28

    def __init__(self):
        screen.nodelay(1)
        curses.curs_set(0)
        curses.start_color()

        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, -1)

        logging.warning("Possible number of different colors: %s" %
                        curses.COLORS)

        self.screenSize = screen.getmaxyx()
        y, x = self.screenSize
        y -= 3
        x -= 3 + Output.statusWidth
        self.fieldPos = (1, 1)
        self.fieldSize = (x, y)
        self.statusPos = (x + 4, 0)
        self.statusSize = (Output.statusWidth - 3,  y + 2)
        self.printField()

    def prepareGame(self):
        screen.clear()
        self.printField()

    def printGame(self, game):
        # screen.clear()

        self.clearField(self.fieldPos, self.fieldSize, sign=" ")
        self.clearField(self.statusPos, self.statusSize, sign=" ")

        # self.printField()
        self.printStatus(game)

        for o in list(Object.objects):
            o.draw(self)

    def printField(self):
        fieldColor = 0
        for i in range(self.fieldPos[0] - 1, self.fieldPos[0] + self.fieldSize[0] + 2):
            self.addSign((i, self.fieldPos[1] - 1), "█", color = fieldColor)
            self.addSign((i, self.fieldPos[1] + self.fieldSize[1] + 1), "█", color = fieldColor)

        for i in range(self.fieldPos[1] - 1, self.fieldPos[1] + self.fieldSize[1] + 2):
            self.addSign((self.fieldPos[0] - 1, i), "█", color = fieldColor)
            self.addSign((self.fieldPos[0] + self.fieldSize[0] + 1, i), "█", color = fieldColor)

    def clearField(self, pos, size, sign=" "):
        for i in range(pos[1], pos[1] + size[1] + 1):
            self.addSign((pos[0], i), sign * (size[0] + 1))

    def printStatus(self, game):
        x, y = self.statusPos
        x = x + 3
        # self.addSign((x, 1), "Sensor:")
        # if inp is not None:
        #     self.addSign((x, 2), "cm slid: " + str(round(self.inp.position)))
        #     self.addSign((x, 3), "cm now:  " + str(round(inp.currA)))
        #     self.addSign((x, 4), "shoot:   " + str(round(inp.shoot)))
        #     self.addSign((x, 5), "shoot d: " + str(round(inp.shootDist)))

        y = 12
        for i, line in enumerate(getFromFile("./objects/heart.txt")):
            self.addSign((x - 1, y + 1 + i), line, color = 2)
            #self.addSign((x, 10 + i), line, color = curses.COLOR_RED)

        for i, line in enumerate(getFromFile("./objects/lifes/" + str(game.status['lifes']) + ".txt")):
            self.addSign((x, y + 8 + i), line)

        x += 14

        for i, line in enumerate(getFromFile("./objects/bottle2.txt")):
            self.addSign((x, y - 1 + i), line, color = 4)

        for i, line in enumerate(getFromFile("./objects/lifes/" + str(game.status['count']) + ".txt")):
            self.addSign((x, y + 8 + i), line)
        # self.addSign((x,10), "count:  " + str(game.status['count']))
        # self.addSign((x,11), "lifes:   " + str(game.status['lifes']))
        # self.addSign((x,12), "time:    " + str(game.time))
        # self.addSign((x,13), "objects: " + str(len(Object.objects)))


        if game.cupThere:
            self.printGlass((x - 13, self.screenSize[0] - 24), game.status["goodies"])
            self.printMl((x - 15, self.screenSize[0] - 31), game.status["ml"])

        if self.screenSize[0] - 31 - (y + 15) > 10:
            for i, line in enumerate(getFromFile("./objects/lebertron.txt")):
                self.addSign((self.statusPos[0] + 1,  (y + 16) + (self.screenSize[0] - 31 - (y + 15) - 9)//2 + i), line, color = 7)


        self.printRandomSigns((self.statusPos[0] + 1, self.statusPos[1] + 1), (self.statusSize[0], 7), 6)



        if Goody.generateT:
            self.addSign((self.statusPos[0] + 2, self.statusPos[1] + 2), Goody.generateT * 10, color = 6)

    def printCountdown(self, nr):
        self.fieldCenteredOutput("./screens/countdown/" + str(nr) + ".txt")

    def printMl(self, pos, ml):
        x, y = pos
        color = 3

        if ml > 100:
            for i, line in enumerate(getFromFile("./objects/lifes/" + str(int(ml/100)) + ".txt")):
                self.addSign((x, y + i), line, color = color)

        x += 8
        if ml > 10:
            for i, line in enumerate(getFromFile("./objects/lifes/" + str((ml/10)%10) + ".txt")):
                self.addSign((x, y + i), line, color = color)

        x += 8

        for i, line in enumerate(getFromFile("./objects/lifes/" + str(ml%10) + ".txt")):
            self.addSign((x, y + i), line, color = color)


    def fieldCenteredOutput(self, file):
        signs = getFromFile(file)
        w, h = (len(signs[0]), len(signs))
        x, y = self.fieldSize
        bx = (x - w) // 2
        by = (y - h) // 2
        for i, line in enumerate(signs):
            ty = by + i
            self.addSign((bx, ty), line, True)

    def printGlass(self, pos, goodies):
        x, y = pos
        top = getFromFile("./objects/glass/top.txt")
        bottom = getFromFile("./objects/glass/bottom.txt")

        body = []
        h = max(11, len(goodies))
        for i in range(h, -1, -1):
            if i > len(goodies) or len(goodies) == 0:
                body.append("||             ||")
            elif i == len(goodies):
                body.append("|:--.._____..--:|")
            elif i < len(goodies):
                body.append("||" + Goody.types[goodies[i]]["name"].center(13, " ") + "||")

        glass = top[:-1] + body + bottom
        for l in glass:
            y += 1
            self.addSign((x, y), l)

    def printRandomSigns(self, pos, size, color):
        for i in range(size[1]):
            self.addSign((pos[0], pos[1] + i), ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(size[0])), color = color)



    def addSign(self, coords, sign, field=False, color=None):
        x, y = coords
        if field:
            x += self.fieldPos[0]
            y += self.fieldPos[1]
        try:
            if color:
                screen.addstr(y, x, sign, curses.color_pair(color))
            else:
                screen.addstr(y, x, sign.encode('utf_8'))
        except:
            logging.debug("terminalSize: %s" % screen.getmaxyx())
            logging.debug("fieldPos: %s" % self.fieldPos)
            logging.debug("fieldSize: %s" % self.fieldSize)
            logging.debug("error writing sign to: %s" % x, y)
            logging.exception()

            # FIXME what does this sleep? do we really need to block for 2min?
            time.sleep(120)
            raise


################################################################################
# CONTROLLER CLASSES
################################################################################

class Controller(object):
    LEFT    = -1
    RIGHT   =  1
    QUIT    = -10
    RETRY   = -11
    SHOOT   = -12
    PAUSE   = -13
    CUPTEST = -15

    def __init__(self, screen = None, position = False, mirror = False, margin = 0):
        self.imp = None
        self.screen = screen
        self.position = position == "true"
        self.mirror = mirror == "true"
        self.margin = int(margin)

    def setImp(self, imp):
        self.imp = imp

    def getInput(self):
        c, k = self.getKeyboardInput();

        if k is not None:
            return k

        if self.imp is not None:
            return self.imp.getInput(c)

    def getPosition(self):
        pos = self.imp.getPosition()

        if self.margin > 0:
            pos = pos*(1 + 0.01*2*self.margin) - 0.01*self.margin

        if pos > 1:
            pos = 1
        elif pos < 0:
            pos = 0

        if self.mirror:
            return 1 - pos
        else:
            return pos

    def getKeyboardInput(self):
        if screen is None:
            return None

        c = self.screen.getch()

        if c == curses.KEY_LEFT:
            return (c, Controller.LEFT)
        elif c == curses.KEY_RIGHT:
            return (c, Controller.RIGHT)
        elif c == ord('q'):
            return (c, Controller.QUIT)
        elif c == ord('r'):
            return (c, Controller.RETRY)
        elif c == ord(' '):
            return (c, Controller.SHOOT)
        elif c == ord('p'):
            return (c, Controller.PAUSE)
        elif c == ord('n'):
            Goody.generateT = "N"
        elif c == ord('o'):
            Goody.generateT = "O"
        elif c == ord('c'):
            Goody.generateT = None
        elif c == ord('l'):
            return (c, Controller.CUPTEST)


        return (c, None)

    def close(self):
        if self.imp is not None:
            self.imp.close()




################################################################################
# GAME CLASS
################################################################################

class Game(object):
    moveStepSize = 3
    background  = None
    soundLost   = None
    soundFull   = None
    createObjects = False
    countdownTime = 30
    sleepTime     = 100

    obstacleCreationTime = 10
    goodyCreationTime = 10

    def __init__(self, controller, output, robot=None):
        self.time       = 0
        self.controller = controller
        self.output     = output
        self.robot      = robot
        self.pause      = False
        self.spaceShip  = SpaceShip(self)
        self.spaceShip.coords = (
            self.output.fieldSize[0] // 2, self.output.fieldSize[1] - 2)
        self.countdown  = 0

        self.status     = {}
        self.setStartStatus()
        self.overlay    = None
        self.oTime      = None
        self.cupThere   = False
        self.cupTaken   = True

        self.gameStarted = False

    def removeObjects(self):
        logging.debug("removing objects")
        Object.objects = [self.spaceShip]

    def setStartStatus(self):
        self.status['goodies'] = []
        self.status['lifes']   = 4
        self.status['ml']      = 0
        self.status['count']   = 0

    def prepare(self):
        self.time   = 0
        self.removeObjects()
        self.createObjects = False
        self.setStartStatus()
        self.output.prepareGame()
        self.countdown = 3
        self.overlay = None
        self.gameStarted = True
        self.cupTaken   = False
        Shoot.lastStartTime = 0
        Sound.startLoop(Game.background)

    def run(self):
        logging.info('Starting main loop...')
        while True:
            t0 = time.time()

            d = self.controller.getInput()

            if d == Controller.QUIT:
                break
            elif d == Controller.SHOOT:
                o = Shoot(self, coords = (self.spaceShip.coords[0], self.spaceShip.coords[1] - self.spaceShip.info['rHeight'] - 1))
            elif d == Controller.CUPTEST:
                if self.cupThere:
                    self.robotMessage("cupNotThere")
                else:
                    self.robotMessage("cupThere")

            # start game
            if d == Controller.RETRY or (not self.gameStarted and self.cupThere and self.cupTaken):
                self.prepare()

            if d == Controller.PAUSE:
                self.switchPause()

            if self.controller.position == False:
                m = 0
                if d == Controller.LEFT:
                    m = -1
                elif d == Controller.RIGHT:
                    m = 1

                x = self.spaceShip.coords[0]
                x += m * self.moveStepSize
            else:
                x = int(self.controller.getPosition() * self.output.fieldSize[0])

            # CHECK MARGINS
            if x > self.output.fieldSize[0] - self.spaceShip.info['rWidth'] - 1:
                x = self.output.fieldSize[0] - self.spaceShip.info['rWidth'] - 1
            elif x < self.spaceShip.info['rWidth'] + 1:
                x = self.spaceShip.info['rWidth'] + 1

            self.spaceShip.coords = (x, self.spaceShip.coords[1])

            for o in list(Object.objects):
                o.check()

            self.output.printGame(self)

            # COUNTDOWN
            if self.countdown > 0:
                self.output.printCountdown(self.countdown)
                if self.time > Game.countdownTime:
                    logging.info("countdown=%d" % self.countdown)
                    self.countdown -= 1
                    self.time = 0
                    if self.countdown == 0:
                        self.createObjects = True

            if self.overlay is not None:
                if self.overlay == "overLifes":
                    file = "./screens/lifes.txt"
                elif self.overlay == "overFull":
                    file = "./screens/full.txt"
                elif self.overlay == "refillBottle":
                    file = "./screens/refill.txt"
                elif self.overlay == "waiting":
                    file = "./screens/waiting.txt"
                elif self.overlay == "cupMissing":
                    file = "./screens/cupMissing.txt"
                self.output.fieldCenteredOutput(file)

            if not self.pause:
                # CREATE OBJECT
                if self.createObjects:
                    if (self.time + 1) % Game.goodyCreationTime == 0:
                        g = Goody(self)
                        g.setRandomXPos(self.output)
                    if self.time % Game.obstacleCreationTime == 0:
                        o = Obstacle(self)
                        o.setRandomXPos(self.output)
                self.time += 1

            time.sleep(max(0, t0 - time.time() + Game.sleepTime))

        self.end("quit")

    def switchPause(self):
        self.pause = not self.pause

    def full(self):
        self.end("overFull")

    def end(self, status):
        if status == "overLifes":
            Sound.play(Game.soundLost)
        if status == "overFull":
            Sound.play(Game.soundFull)

        logging.info("Ending game now (status=%s)" % status)
        logging.debug("threads alive: %s" % threading.active_count())
        self.overlay = status
        self.removeObjects()
        self.cupTaken = False
        logging.debug("clearing screen")
        screen.clear()
        self.output.printField()
        self.gameStarted = False
        self.createObjects = False
        if Game.background is not None:
            logging.debug("Game.background.stopLoop()")
            Sound.stopLoop(Game.background)
            logging.debug("background sound stopped successfully")
        logging.debug("Ending now, threads alive: %s" % threading.active_count())

    def lifeLost(self):
        logging.info("you lost a life!")
        self.status['lifes'] = self.status['lifes'] - 1
        logging.debug("status=%s" % self.status)
        if self.status['lifes'] == 0:
            self.end("overLifes")
        else:
            self.spaceShip.blink()

    def robotMessage(self, message):
        if message == "bottleEmpty":
            self.pause = True
            self.overlay = "refillBottle"
        elif message == "bottleEmptyResume":
            self.pause = False
            self.overlay = None
        elif message == "cupThere":
            self.cupThere = True
            if self.gameStarted:
                self.overlay = None
                self.pause = False
        elif message == "cupNotThere":
            self.cupThere = False
            self.cupTaken = True
            if self.countdown > 0:
                self.gameStarted = False
                self.countdown = 0
            if self.gameStarted:
                self.pause = True
                self.overlay = "cupMissing"
            if not self.gameStarted:
                self.overlay = "waiting"


def main(s=None):
    global screen
    screen = s
    screen.nodelay(1)

    ############################################################################
    # Sound Config
    ############################################################################
    soundConfig = ConfigParser()
    soundConfig.read('./etc/sound.cfg')

    if soundConfig.getboolean('General', 'enabled'):
        Shoot.soundShooting     = soundConfig.get('Shoot', 'shooting')
        Shoot.soundCollision    = soundConfig.get('Shoot', 'obstacle')

        Obstacle.cSpaceship     = soundConfig.get('Spaceship', 'obstacle')
        Goody.cSpaceship        = soundConfig.get('Spaceship', 'goody')
        Game.background         = soundConfig.get('General', 'background')
        Game.soundLost          = soundConfig.get('General', 'lost')
        Game.soundFull          = soundConfig.get('General', 'full')


    ############################################################################
    # Design Config
    ############################################################################
    # default factor == 1
    designConfig = ConfigParser({'factor': '1'})
    designConfig.read('./etc/design.cfg')

    # Set obstacles files
    folder = os.path.join(designConfig.get('Obstacles', 'folder'), "")
    for obstacleDesign in glob.glob(folder + "*.txt"):
        Obstacle.obstacles.append(obstacleDesign)

    Obstacle.color      = designConfig.getint('Obstacles', 'color')

    SpaceShip.color     = designConfig.getint('Spaceship', 'color')
    SpaceShip.design    = designConfig.get('Spaceship', 'file')

    folder = os.path.join(designConfig.get('Spaceship', 'folder'), "")
    if folder is not None:
        for spaceshipDesign in glob.glob(folder + "*.txt"):
            #logging.debug("spaceshipDesign %s" % spaceshipDesign)
            SpaceShip.designArray.append(spaceshipDesign)

    ingredientsFolder   = designConfig.get('Ingredients', 'folder')
    for nrGoody in range(1, designConfig.getint('Ingredients', 'count') + 1):
        sectionName = 'Ingredient' + str(nrGoody)
        Goody.types.append({
                "color":    designConfig.getint(sectionName, 'color'),
                "design":   os.path.join(ingredientsFolder, designConfig.get(sectionName, 'file')),
                "name":     designConfig.get(sectionName, 'name'),
                "arduino":  designConfig.getint(sectionName, 'arduino'),
                "factor":   designConfig.getint(sectionName, 'factor'),
                "category": designConfig.get(sectionName, 'category')
        })


    ############################################################################
    # Controller Config
    ############################################################################
    controllerConfig = ConfigParser()
    controllerConfig.read('./etc/controller.cfg')

    kwargsController = dict(controllerConfig.items("Controller"))

    controllerType = kwargsController['type']
    del kwargsController['type']

    kwargsController['screen'] = screen

    controller = Controller(**kwargsController)
    imp = None
    if controllerType == "ultrasonic":
        from inputComm import InputComm
        imp = InputComm(**dict(controllerConfig.items("UltraSonic")))
    elif controllerType == "camera":
        from camera import Camera
        kwargs = dict(controllerConfig.items("Camera"))
        kwargs['controller'] = controller
        imp = Camera(**kwargs)

    controller.setImp(imp)



    ############################################################################
    # Create Game
    ############################################################################
    o = Output()


    ############################################################################
    # Robot Config
    ############################################################################

    robot = None
    robotConfig = ConfigParser()
    robotConfig.read('./etc/robot.cfg')

    Game.sleepTime = robotConfig.getint('Game', 'sleepTime')/100
    Game.obstacleCreationTime = robotConfig.getint('Game', 'obstacleCreationTime')
    Game.goodyCreationTime = robotConfig.getint('Game', 'goodyCreationTime')

    g = Game(controller=controller, output=o)

    Goody.portion = robotConfig.getint('Mixing', 'portion')
    Goody.volume = robotConfig.getint('Mixing', 'volume')
    if robotConfig.getboolean('Robot', 'enabled'):
        robot = BotComm(robotConfig.get('Robot', 'serialPort'), g.robotMessage)

    g.robot = robot


    #g.prepare()
    #g.run()
    try:
        g.run()
    except Exception as e:
        raise e
    finally:
        # Cleaning Up
        if soundConfig.getboolean('General', 'enabled'):
            Sound.closeAll()

        if robot is not None:
            robot.close()

        controller.close()
        screen.refresh()


#main()
curses.wrapper(main)
