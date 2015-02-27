#!/usr/bin/env python

from SubspaceBot import *
from BotUtilities import ModuleData,BotInterface
import logging
from TimerManager import TimerManager


class Bot(BotInterface):
	def __init__(self,ssbot,md):
		BotInterface.__init__(self,ssbot,md)
		#register Your Module
		ssbot.registerModuleInfo(__name__,"Info/LagBot","The Junky","displays/checks players lag",".01")
		#register your commands 
		
		self.tm = TimerManager()
		
		self.cmd_dict = {
		ssbot.registerCommand('!whatthef', #command  
							"!wtf", #alias can be None if no alias
							0, #min access level to use this command
							COMMAND_LIST_PP, #what types of messages this command will accept
							"w.t.f", #category this command belongs to
							"<name>", #what args if any this command accepts use "" if none
							"what the f") #short description of the command displayed in help 
							: self.cmdWTF #cmdHandler(self,ssbot,event)
#		ssbot.registerCommand('!listflags', #command  
#							"!lf", #alias can be None if no alias
#							0, #min access level to use this command
#							COMMAND_LIST_PP, #what types of messages this command will accept
#							"info", #category this command belongs to
#							"<name>", #what args if any this command accepts use "" if none
#							"request/check players lag") #short description of the command displayed in help 
#							: self.cmdLF #cmdHandler(self,ssbot,event)
		}
		#do any other initialization code here
		#...
		
	def HandleEvents(self,ssbot,event):
		#whatever events your bot needs to respond to add code here to do it
		if event.type == EVENT_LOGIN:
			pass
		elif (event.type == EVENT_COMMAND and event.command.id in self.cmd_dict):
			self.cmd_dict[event.command.id](ssbot,event)
		elif event.type == EVENT_TICK:
			timer_expired = self.tm.getExpired()
			if timer_expired:
				if timer_expired.data == 1: #timer_expired is now the data we passed to timer
					pass
		elif event.type == EVENT_DISCONNECT:
			pass	
	def cmdWTF(self,ssbot,event):
		ssbot.sendReply(event,"wtf")
	def Cleanup(self):
		#put any cleanup code in here this is called when bot is about to die
		pass


if __name__ == '__main__':
	from Credentials import botowner, botname, botpassword
	# create logger with 'spam_application'
	logger = logging.getLogger('Main')
	logger.setLevel(logging.DEBUG)
	# create file handler which logs even debug messages
	fh = logging.FileHandler('main.log')
	fh.setLevel(logging.DEBUG)
	# create console handler with a higher log level
	ch = logging.StreamHandler()
	ch.setLevel(logging.DEBUG)
	# create formatter and add it to the handlers
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	fh.setFormatter(formatter)
	ch.setFormatter(formatter)
	# add the handlers to the logger
	logger.addHandler(fh)
	logger.addHandler(ch)
	
	ssbot= SubspaceBot('66.36.247.83', 7900, botname, botpassword,'#master',False,BM_STANDALONE,None,logger)
	lp = reactor.listenUDP(0, ssbot)
	ssbot.setReactorData(reactor,lp) # so clients can disconnect tghemselves when they get disconnect packet or master kills them
	module = sys.modules[globals()['__name__']]
	md = ModuleData("TesttBot",module,"None","test.ini","",logger)
	ssbot.setBotList([Bot(ssbot,md)])
	reactor.run()
