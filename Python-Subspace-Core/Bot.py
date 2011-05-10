'''
@author: The Junky
'''
import os
import glob
import logging
import logging.handlers

from Credentials import botowner, botname, botpassword
from SubspaceBot import *
#Generic Bot will load all Bot classes that follow the Botinterface
# and end with Bot.py
#for some reason when i try to inherit from botinterface this code wont work


if __name__ == '__main__':
        BotList = []
        bot = SubspaceBot(botowner, 'WebBot')
        bot.connectToServer('66.235.184.102', 7900, botname, botpassword, '#master')
        thisfile = ".\\Bot.py"
        #print "this file: " + thisfile
        for infile in glob.glob( os.path.join(".//", '*Bot.py') ):
            if infile != thisfile:
                module = __import__( infile[2:-3],fromlist=["Bot"])
                try:
                    BotList.append (module.Bot(bot))
                except AttributeError as wtf:
                    print( "trying to instantiate %s caused Exception %s " %
                    (infile[2:-3],wtf))
                    
                    
                    
        while bot.isConnected():
                event = bot.waitForEvent()
                for b in BotList:
                    b.HandleEvents(bot,event);
        print "Bot disconnected"
