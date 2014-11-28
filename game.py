#!/usr/bin/python2
# -*- coding: utf-8 -*-
import sys, traceback
import curses, locale
import random, os, glob
import time as timeLib
from ConfigParser import SafeConfigParser
import sound as soundLib

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

locale.setlocale(locale.LC_ALL, "")

screen = None
################################################################################
# HELPER FUNCTIONS
################################################################################

def getFromFile(fileName):
    #f = codecs.open("./objects/" + fileName + ".txt", 'r', "utf-8")
    f = open(fileName, 'r')
    content = f.read().decode('utf-8')
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
    def __init__(self, game, coords = None, signs = None, speed = None, color = None):
        self.game   = game
        self.coords = coords
        self.signs  = signs
        self.color  = color

        if speed is None:
            self.speed = random.randint(Object.stdSpeed/2, Object.stdSpeed*2)
        else:
            self.speed = speed

        Object.objects.append(self)

        self.info = {}
        self.info['maxHeight']  = len(signs)
        self.info['rHeight']    = (len(signs) - 1)/2

        self.info['widths']  = []

        for line in signs:
            self.info['widths'].append(len(line))

        self.info['maxWidth']   = max(self.info['widths'])
        self.info['rWidth']     = (self.info['maxWidth'] - 1)/2



    def setRandomXPos(self, output, y = None):
        if y is None:
            y = -self.game.time/self.speed - 5
        x = random.randint(2 + self.info['rWidth'], output.fieldSize[0] - 2 - self.info['rWidth'])
        self.coords = (x, y)


    def getPosArray(self):
        posArray = []
        x, y = self.getMapCoords()
        #for i, width in enumerate(self.info["widths"]):
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
            Object.objects.remove(self)
            self.collision()


    def collision(self):
        pass


    def getMapCoords(self):
        return (self.coords[0], self.coords[1] + self.game.time/self.speed)


    def draw(self, output):
        x, y = self.getMapCoords()
        if y > output.fieldSize[1] + self.info['rHeight']:
            Object.objects.remove(self)
            return

        if y < -10:
            Object.objects.remove(self)
            return

        for i, line in enumerate(self.signs):
            py = y - self.info['rHeight'] + i
            if py <= output.fieldSize[1] and py >= 0:
                for j, sign in enumerate(line):
                    if sign != " ":
                        px = x - self.info['rWidth'] + j
                        output.addSign((px, py), sign, field = True, color = self.color)
            #py = y - (len(self.signs) - 1)/2 + i
            #if py <= output.fieldSize[1] and py >= 0:
            #    output.addSign((x - (len(line) - 1)/2, py), line, field = True, color = self.color)



class Shoot(Object):
    soundShooting   = None
    soundCollision  = None
    startTime       = None
    def __init__(self, game, **args):
        args["signs"] = getFromFile("./objects/shoot.txt")
        args["color"] = 2
        args["speed"] = 1
        self.startTime = game.time
        Shoot.soundShooting.play()
        super(Shoot, self).__init__(game, **args)

    def getMapCoords(self):
        return (self.coords[0], self.coords[1] - (self.game.time - self.startTime)/self.speed)

    def check(self):
        for o in Object.objects:
            if isinstance(o, Obstacle):
                if len(set(self.getPosArray()).intersection(o.getPosArray())) > 0:
                    Object.objects.remove(o)
                    Object.objects.remove(self)
                    Shoot.soundCollision.play()
                    break


class Obstacle(Object):
    obstacles   = []
    cSpaceship  = None

    def collision(self):
        Obstacle.cSpaceship.play()
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

    def collision(self):
        Goody.cSpaceship.play()
        self.game.status['points'] = self.game.status['points'] + 5
        self.game.status['goodies'].append(self.name)

    def __init__(self, game, **args):
        if "signs" not in args:
            i = random.randint(0, len(Goody.types) - 1)
            args["signs"] = getFromFile(Goody.types[i]["design"])
            args["color"] = Goody.types[i]["color"]
            self.name = Goody.types[i]["name"]
            self.ouptut = i
        super(Goody, self).__init__(game, **args)


class SpaceShip(Object):
    design  = getFromFile("./objects/spaceShip.txt")
    color   = None
    def __init__(self, game, **args):
        if "signs" not in args:
            args["signs"] = getFromFile(self.design)
            args["color"] = self.color
        super(SpaceShip, self).__init__(game, **args)

    def getMapCoords(self):
        return (self.coords[0], self.coords[1])

    def check(self):
        return








################################################################################
# OUTPUT CLASSES
################################################################################

class Output(object):
    rightStatusWidth = 30
    fieldPos  = None
    fieldSize = None
    statusPos = None

    def __init__(self):

        screen.clear()
        screen.nodelay(1)
        #screen.curs_set(0)
        curses.curs_set(0)
        curses.start_color()

        curses.use_default_colors()
        for i in range(0, curses.COLORS):
            curses.init_pair(i + 1, i, -1)

        y, x = screen.getmaxyx()
        y -= 3
        x -= 3 + Output.rightStatusWidth
        self.fieldPos = (1, 1)
        self.fieldSize = (x, y)
        self.statusPos = (x + 5, 0)


    def printGame(self, game):
        #screen.clear()

        for i in range(self.fieldPos[1], self.fieldPos[1] + self.fieldSize[1] + 1):
            self.addSign((self.fieldPos[0], i), " "*self.fieldSize[0])

        self.printField()
        self.printStatus(game)

        for o in list(Object.objects):
            o.draw(self)


    def printField(self):
        for i in range(self.fieldPos[0] - 1, self.fieldPos[0] + self.fieldSize[0] + 2):
            self.addSign((i, self.fieldPos[1] - 1), u"█")
            self.addSign((i, self.fieldPos[1] + self.fieldSize[1] + 1), u"█")

        for i in range(self.fieldPos[1] - 1, self.fieldPos[1] + self.fieldSize[1] + 2):
            self.addSign((self.fieldPos[0] - 1, i), u"█", color = None)
            self.addSign((self.fieldPos[0] + self.fieldSize[0] + 1, i), u"█")


    def printStatus(self, game):
        x, y = self.statusPos
        self.addSign((x, 1), "Sensor:")
        try:
            self.addSign((x, 2), "cm:      " + str(round(inp.curr)))
            self.addSign((x, 4), "dir:     " + str(inp.state))
        except NameError:
            pass

        self.addSign((x, 6), "Game:")
        self.addSign((x, 7), "points:  " + str(game.status['points']))
        self.addSign((x, 8), "lifes:   " + str(game.status['lifes']))
        self.addSign((x, 9), "time:    " + str(game.time))
        self.addSign((x,10), "objects: " + str(len(Object.objects)))

        self.printGlass(x, 12, game.status["goodies"])


    def printGlass(self, x, y, goodies):
        top    = getFromFile("./objects/glass/top.txt")
        bottom = getFromFile("./objects/glass/bottom.txt")

        body    = []
        h = max(6, len(goodies))
        for i in range(h, -1, -1):
            if i > len(goodies) or len(goodies) == 0:
                body.append("||             ||")

            elif i == len(goodies):
                body.append("|:--.._____..--:|")

            elif i < len(goodies):
                body.append("||" + goodies[i].center(13, " ") + "||")

        glass = top + body + bottom
        for l in glass:
            y += 1
            self.addSign((x, y), l)


    def addSign(self, coords, sign, field = False, color = None):
        x, y = coords
        if field:
            x += self.fieldPos[0]
            y += self.fieldPos[1]
        try:
            if color:
                screen.addstr(y, x, sign.encode('utf_8'), curses.color_pair(color))
            else:
                screen.addstr(y, x, sign.encode('utf_8'))
        except Exception as e:
            print >> sys.stderr, "terminalSize:", screen.getmaxyx()
            print >> sys.stderr, "fieldPos:", self.fieldPos
            print >> sys.stderr, "fieldSize:", self.fieldSize
            print >> sys.stderr, "error writing sign to:", x, y
            print >> sys.stderr, traceback.format_exc()

            timeLib.sleep(120)
            exit();


################################################################################
# CONTROLLER CLASSES
################################################################################

class Controller(object):
    LEFT    = -1
    RIGHT   =  1
    QUIT    = -10
    RETRY   = -11
    SHOOT   = -12

    def __init__(self, screen, position):
        self.screen = screen
        self.position = position

    def getInput(self):
        #raise NotImplementedError
        c = self.screen.getch()
        return None


class UltraSonicController(Controller):
    def __init__(self, serialPort, screen, position = False):
        import input as inp
        self.inp = inp
        self.distPos    = (10, 60)
        inp.connect(serialPort)
        inp.start()
        super(UltraSonicController, self).__init__(screen, position)

    def getInput(self):
        c = self.screen.getch()

        if c == ord('q'):
            return Controller.QUIT

        if self.position:
            return float(self.inp.curr - self.distPos[0])/(self.distPos[1] - self.distPos[0])


        if inp.state == -1:
            return Controller.LEFT
        elif inp.state == 1:
            return Controller.RIGHT
        return None


    # def getPosition(self):
    #     float(inp.curr - self.distPos[0])/(self.distPos[1] - self.distPos[0])



class KeyboardController(Controller):
    def __init__(self, screen, position):
        super(KeyboardController, self).__init__(screen, position)

    def getInput(self):
        c = self.screen.getch()

        if c == curses.KEY_LEFT:
            return Controller.LEFT
        elif c == curses.KEY_RIGHT:
            return Controller.RIGHT
        elif c == ord('q'):
            return Controller.QUIT
        elif c == ord('r'):
            return Controller.RETRY
        elif c == ord(' '):
            return Controller.SHOOT
        # try:
        #     value = int(c)
        #     return float(value - 1)/8
        # except ValueError:


        return None


################################################################################
# GAME CLASS
################################################################################

class Game(object):
    spaceShip   = None
    time        = None
    status      = None
    moveStepSize = 3
    background  = None

    def __init__(self, controller, output):
        self.controller = controller
        self.output = output

    def prepare(self):
        self.time   = 0
        self.status = {}
        self.status['points']   = 0
        self.status['goodies']  = []
        self.status['lifes']    = 3
        self.removeObjectsAndCreateSpaceship()
        Game.background.loop()

    def removeObjectsAndCreateSpaceship(self):
        Object.objects = []
        self.spaceShip = SpaceShip(self)
        self.spaceShip.coords = (self.output.fieldSize[0]/2, self.output.fieldSize[1] - 2)


    def run(self):
        while True:
            d = self.controller.getInput()

            if d == Controller.QUIT:
                break
            elif d == Controller.SHOOT:
                o = Shoot(self, coords = (self.spaceShip.coords[0], self.spaceShip.coords[1] - self.spaceShip.info['rHeight']))

            if self.controller.position == False:
                m = 0
                if d == Controller.LEFT:
                    m = -1
                elif d == Controller.RIGHT:
                    m = 1

                x = self.spaceShip.coords[0]
                x += m * self.moveStepSize
            else:
                x = int(d*self.output.fieldSize[0])

            # CHECK MARGINS
            if x > self.output.fieldSize[0] - self.spaceShip.info['rWidth'] - 1:
                x = self.output.fieldSize[0] - self.spaceShip.info['rWidth'] - 1
            elif x < self.spaceShip.info['rWidth'] + 1:
                x = self.spaceShip.info['rWidth'] + 1

            self.spaceShip.coords = (x, self.spaceShip.coords[1])

            for o in list(Object.objects):
                o.check()

            self.output.printGame(self)

            if self.time%50 == 0:
                g = Goody(self)
                g.setRandomXPos(self.output)
            if self.time%40 == 0:
                o = Obstacle(self)
                o.setRandomXPos(self.output)

            timeLib.sleep(.02)

            self.time += 1
        self.end()


    def end(self):
        Game.background.stopLoop()
        self.spaceShip = None
        screen.clear()
        self.output.printField()
        # screen.nodelay(0)
        # c = screen.getch()
        #
        # if c == ord('r'):
        #     self.prepare()
        # else:
        #     exit()
        # screen.nodelay(1)

    def lifeLost(self):
        self.status['lifes'] = self.status['lifes'] - 1

        if self.status['lifes'] == 0:
            self.end()
        else:
            self.removeObjectsAndCreateSpaceship()




def main(s = None):
    global screen
    screen = s
    screen.nodelay(1)

    ############################################################################
    # Sound Config
    ############################################################################
    soundConfig = SafeConfigParser()
    soundConfig.read('./sound.cfg')

    Shoot.soundShooting     = soundLib.Sound(soundConfig.get('Shoot', 'shooting'))
    Shoot.soundCollision    = soundLib.Sound(soundConfig.get('Shoot', 'obstacle'))

    Obstacle.cSpaceship     = soundLib.Sound(soundConfig.get('Spaceship', 'obstacle'))
    Goody.cSpaceship        = soundLib.Sound(soundConfig.get('Spaceship', 'goody'))
    Game.background         = soundLib.Sound(soundConfig.get('General', 'background'))

    ############################################################################
    # Design Config
    ############################################################################
    designConfig = SafeConfigParser()
    designConfig.read('./design.cfg')

    # Set obstacles files
    folder = os.path.join(designConfig.get('Obstacles', 'folder'), "")
    for obstacleDesign in glob.glob(folder + "*.txt"):
        Obstacle.obstacles.append(obstacleDesign)

    Obstacle.color      = designConfig.getint('Obstacles', 'color')

    SpaceShip.color     = designConfig.getint('Spaceship', 'color')
    SpaceShip.design    = designConfig.get('Spaceship', 'file')

    ingredientsFolder   = designConfig.get('Ingredients', 'folder')
    for nrGoody in range(1, designConfig.getint('Ingredients', 'count') + 1):
        sectionName = 'Ingredient' + str(nrGoody)
        Goody.types.append({
                "color":    designConfig.getint(sectionName, 'color'),
                "design":   os.path.join(ingredientsFolder, designConfig.get(sectionName, 'file')),
                "name":     designConfig.get(sectionName, 'name')
        })


    ############################################################################
    # Controller Config
    ############################################################################
    controllerConfig = SafeConfigParser()
    controllerConfig.read('./controller.cfg')
    position = False
    if controllerConfig.get('Controller', 'type') == "keyboard":
        c = KeyboardController(screen, position)
    else:
        position = controllerConfig.getboolean('UltraSonic', 'position')
        c = UltraSonicController(controllerConfig.get('UltraSonic', 'serialPort'), screen, position)



    ############################################################################
    # Create Game
    ############################################################################
    o = Output()
    g = Game(c, o)
    g.prepare()
    g.run()

    if isinstance(c, UltraSonicController):
        inp.exitFlag = 1
        timeLib.sleep(0.3)

    screen.refresh()


#main()
curses.wrapper(main)
