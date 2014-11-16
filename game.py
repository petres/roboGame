#!/usr/bin/python2
import serial, sys, traceback
import time as timeLib
import curses
import random
import input as inp
from curses import wrapper

STD_SPEED = 5
time = 0

gameStatus = {}

def getFromFile(fileName):
    f = open("./objects/" + fileName + ".txt", 'r')
    content = f.read()
    signsArray = []
    for line in content.split("\n"):
        temp = line.strip()
        signsArray.append(temp)
    return signsArray


class Object(object):
    objects = []
    def __init__(self, coords = None, signs = getFromFile("stone"), speed = None, randomX = False, color = None):
        self.coords = coords
        self.signs  = signs
        self.color   = color

        if speed is None:
            self.speed = random.randint(STD_SPEED - 3, STD_SPEED + 3)

        Object.objects.append(self)

        self.info = {}
        self.info['maxHeight']  = len(signs)
        self.info['maxWidth']   = 0
        self.info['rHeight']    = (len(signs) - 1)/2
        self.info['widths']     = []

        for line in signs:
            self.info['widths'].append(len(line))

        self.info['maxWidth']   = max(self.info['widths'])
        self.info['rWidth']     = (self.info['maxWidth'] - 1)/2

        if randomX:
            self.setRandomXPos()


    def setRandomXPos(self, y = None):
        if y is None:
            y = -time/self.speed - 10
        x = random.randint(2 + self.info['rWidth'], fieldSize[0] - 2 - self.info['rWidth'])
        self.coords = (x, y)


    def getPosArray(self):
        posArray = []
        x, y = self.getMapCoords()
        for i, width in enumerate(self.info["widths"]):
            for j in range(width):
                posArray.append((x - (width - 1)/2 + j, y - self.info["rHeight"] + i))
        return posArray


    def check(self):
        global points

        x, y = self.getMapCoords()
        if y > fieldSize[1] + self.info['rHeight']:
            Object.objects.remove(self)

        if len(set(self.getPosArray()).intersection(spaceShip.getPosArray())) > 0:
            Object.objects.remove(self)
            self.collision()


    def collision():
        pass


    def getMapCoords(self):
        return (self.coords[0], self.coords[1] + time/self.speed)


    def draw(self):
        x, y = self.getMapCoords()

        for i, line in enumerate(self.signs):
            py = y - (len(self.signs) - 1)/2 + i
            if py <= fieldSize[1] and py >= 0:
                addSign((x - (len(line) - 1)/2, py), line, field = True, color = self.color)


class Obstacle(Object):
    obstacles = ['stone', 'bigStone']
    def collision(self):
        global spaceShip
        gameStatus['lifes'] = gameStatus['lifes'] - 1

        if gameStatus['lifes'] == 0:
            endGame()
        else:
            Object.objects = []
            spaceShip = SpaceShip(signs = getFromFile("spaceShip"), color = 3)
            spaceShip.coords = (fieldSize[0]/2, fieldSize[1] - 2)

    def __init__(self, **args):
        if "signs" not in args:
            i = random.randint(0, len(Obstacle.obstacles) - 1)
            args["signs"] = getFromFile(Obstacle.obstacles[i])
        super(Obstacle, self).__init__(**args)



class Goody(Object):
    def collision(self):
        gameStatus['points'] = gameStatus['points'] + 5

    def __init__(self, **args):
        if "signs" not in args:
            args["signs"] = getFromFile("vodka")
            args["color"] = 2
        super(Goody, self).__init__(**args)


class SpaceShip(Object):
    def getMapCoords(self):
        return (self.coords[0], self.coords[1])
    def check(self):
        return


def printField():
    for i in range(fieldPos[0] - 1, fieldPos[0] + fieldSize[0] + 2):
        addSign((i, fieldPos[1] - 1), "X", color = 78)
        addSign((i, fieldPos[1] + fieldSize[1] + 1), "X", color = 78)

    for i in range(fieldPos[1] - 1, fieldPos[1] + fieldSize[1] + 2):
        addSign((fieldPos[0] - 1, i), "X", color = 78)
        addSign((fieldPos[0] + fieldSize[0] + 1, i), "X", color = 78)



fieldPos  = None
fieldSize = None

def addSign(coords, sign, field = False, color = None):
    x, y = coords
    if field:
        x += fieldPos[0]
        y += fieldPos[1]
    try:
        if color:
            screen.addstr(y, x, sign, curses.color_pair(color))
        else:
            screen.addstr(y, x, sign)
    except Exception as e:
        print >> sys.stderr, "terminalSize:", screen.getmaxyx()
        print >> sys.stderr, "fieldPos:", fieldPos
        print >> sys.stderr, "fieldSize:", fieldSize
        print >> sys.stderr, "error writing sign to:", x, y
        print >> sys.stderr, traceback.format_exc()

        timeLib.sleep(120)
        exit();



rightStatusWidth = 30

def init():
    global fieldPos, fieldSize, statusPos

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
    x -= 3 + rightStatusWidth
    fieldPos = (1, 1)
    fieldSize = (x, y)
    statusPos = (x + 5, 0)




spaceShip = None

def endGame():
    spaceShip = None

    screen.clear()
    printField()
    printStatus()

    screen.nodelay(0)

    c = screen.getch()

    if c == ord('r'):
        initGame()
    else:
        exit()

def initGame():
    global time, spaceShip
    screen.nodelay(1)
    Object.objects = []
    spaceShip = SpaceShip(signs = getFromFile("spaceShip"), color = 3)
    time = 0
    spaceShip.coords = (fieldSize[0]/2, fieldSize[1] - 2)
    gameStatus['points'] = 0
    gameStatus['lifes']  = 3


moveStepSize = 3



def printStatus():
    x, y = statusPos
    addSign((x, 1), "Sensor:")
    addSign((x, 2), "cm:      " + str(inp.curr))
    addSign((x, 4), "dir:     " + str(inp.state))

    addSign((x, 6), "Game:")
    addSign((x, 7), "points:  " + str(gameStatus['points']))
    addSign((x, 8), "lifes:   " + str(gameStatus['lifes']))
    addSign((x, 9), "time:    " + str(time))
    addSign((x,10), "objects: " + str(len(Object.objects)))




#def printSpaceShip():
#    x, y = spaceShipPos
#    for i, line in enumerate(spaceShipSigns):
#        addSign((x - (len(line) - 1)/2, y - (len(spaceShipSigns) - 1)/2 + i),  line, True)



distSize = (15, 50)

def main(s):
    global screen, spaceShipPos, time
    screen = s

    inp.main()

    init()

    initGame()

    while True:
        c = screen.getch()
        x = spaceShip.coords[0]
        if c == ord('q'):
            break  # Exit the while loop
        elif c == curses.KEY_LEFT or inp.state == -1:
            if (x - moveStepSize - spaceShip.info['maxWidth']/2) > 0:
                x -= moveStepSize
        elif c == curses.KEY_RIGHT or inp.state == 1:
            if (x + moveStepSize + spaceShip.info['maxWidth']/2) < fieldSize[0]:
                x += moveStepSize

        # x = int(float(inp.curr - distSize[0])/(distSize[1] - distSize[0])*fieldSize[0])

        if x > fieldSize[0] - spaceShip.info['maxWidth']:
            x = fieldSize[0] - spaceShip.info['maxWidth']
        elif x < spaceShip.info['maxWidth']:
            x = spaceShip.info['maxWidth']

        spaceShip.coords = (x, spaceShip.coords[1])

        screen.clear()
        printField()
        printStatus()

        for o in list(Object.objects):
            o.check()

        for o in list(Object.objects):
            o.draw()

        #printSpaceShip()

        timeLib.sleep(.02)
        if time%100 == 0:
            Goody(randomX = True)
        if time%50 == 0:
            Obstacle(randomX = True)
        time += 1

    inp.exitFlag = 1
    screen.refresh()

wrapper(main)
