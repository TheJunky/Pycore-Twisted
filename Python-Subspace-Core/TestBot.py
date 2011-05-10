#!/usr/bin/env python
#requires simplejson and python-twitter libraries


from Credentials import botowner, botname, botpassword
from SubspaceBot import *
from BotUtilities import *
import time


if __name__ == '__main__':
        BotList = []
        bot = SubspaceBot(botowner, 'testbot')
        bot.connectToServer('66.235.184.102', 7900, botname, botpassword, '#master')
        #BotList.append(TweetBot(bot,"param",Oplist()))
        while bot.isConnected():
                event = bot.waitForEvent()
                time.sleep(10)
                for b in BotList:
                    b.HandleEvents(bot,event);
        print "Bot disconnected"
        for b in BotList:
            b.Cleanup(bot,event);