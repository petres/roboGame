#!/usr/bin/python
#
"""
Connect to robot
Provide API to write to robot
Provide listener thread
Disconnect gracefully

"""
import serial
import threading
import time
import logging
from queue import Queue


class BotComm(object):

    def __init__(self, serialPort, listenCallback):
        self.exitFlag = False
        self.ready = False
        self.pouring = False
        self.pourQueue = Queue()
        self.bottleEmpty = False

        try:
            self.serialConn = serial.Serial(port=serialPort) # timeout = 0
            self.listenCallback = listenCallback
            self.listenThread = threading.Thread(
                target=self.callbackWrapper)
            self.listenThread.start()
        except:
            logging.exception('ups, something went wrong')

    def close(self):
        self.exitFlag = True
        logging.info("INFO: Waiting for botComm listen thread ... ")
        self.listenThread.join()
        logging.info("DONE" + "\n")
        # time.sleep(0.2)
        self.serialConn.close()

    def callbackWrapper(self):
        serialBuffer = ""
        while not self.exitFlag:
            try:
                serialBuffer += self.serialConn.read()
                commandArray = serialBuffer.split("\r\n")
                serialBuffer = commandArray.pop()

                for command in commandArray:
                    logging.debug('R %s \\r\\n' % command)

                    commandList = command.split(" ")

                    if commandList[0] == "READY":
                        if int(commandList[2]) == 1:
                            self.listenCallback("cupThere")
                            if self.pouring == False:
                                self.ready = True
                        else:
                            self.listenCallback("cupNotThere")

                    elif commandList[0] == "WAITING_FOR_CUP":
                        pass
                    elif commandList[0] == "POURING":
                        pass
                    elif commandList[0] == "ENJOY":
                        self.pouring = False
                        if self.bottleEmpty:
                            self.bottleEmpty = True
                            self.listenCallback("bottleEmptyResume")

                    elif commandList[0] == "ERROR":
                        if commandList[1] == "BOTTLE_EMPTY":
                            self.bottleEmpty = True
                            self.listenCallback("bottleEmpty")
                    elif commandList[0] == "NOP":
                        pass
                    else:
                        pass

                    #self.listenCallback(command)

                    if not self.pourQueue.empty() and self.ready:
                        self.pour(*self.pourQueue.get())

                #time.sleep(0.2)

            except Exception as e:
                logging.info(str(e) + '\n')
                continue

    def send(self, verb, *args):
        try:
            messageString = verb + " " + " ".join(str(n) for n in args)
            self.serialConn.write(messageString + '\r\n')
            logging.debug("T %s \\r\\n" % messageString)
            self.serialConn.flushInput()
        except Exception as e:
            logging.info(str(e) + '\n')

    def pourBottle(self, bottleNr, amount):
        temp = [0] * 7
        temp[bottleNr] = amount
        self.pourQueue.put(temp)
        # self.pour(*temp)

    def pour(self, *args):
        logging.info(
            "INFO: SEND POUR COMMAND (" + " ".join(str(n) for n in args) + ")")
        """pour x_i grams of ingredient i, for i=1..n; will skip bottle
		if x_n < UPRIGHT_OFFSET"""
        # TODO: Check if ready for pour
        # from time import sleep
        # sleep(5)
        self.send("POUR", *args)
        self.ready = False
        self.pouring = True

    def abort(self):
        """abort current cocktail"""
        self.ready = False
        self.send("ABORT")

    def resume(self):
        """resume after BOTTLE_EMPTY error, use this command when
        bottle is refilled"""
        self.send("RESUME")

    def dance(self):
        """let the bottles dance!"""
        self.send("DANCE")

    def tare(self):
        """sets scale to 0, make sure nothing is on scale when
        sending this command Note: taring is deleled, when Arduino
        is reseted (e.g. on lost serial connection)"""
        self.send("TARE")

    def turn(self, bottle_nr, microseconds):
        """turns a bottle (numbered from 0 to 6) to a position
        given in microseconds"""
        self.send("TURN")

    def echo(self, msg):
        """Example: ECHO ENJOY\r\n Arduino will then print "ENJOY"
        This is a workaround to resend garbled messages manually."""
        self.send("ECHO", msg)

    def nop(self):
        """Arduino will do nothing and send message "DOING_NOTHING".
        This is a dummy message, for testing only."""
        self.send("NOP")


if __name__ == '__main__':
    def youGotMsg(msg):
        print(msg)

    c = BotComm('/dev/ttyS99', youGotMsg)
    while True:
        if c.ready:
            print("Ready")
            c.pour(str(10), str(10), str(10),
                   str(10), str(10), str(10), str(10))

        # time.sleep(0.2)
