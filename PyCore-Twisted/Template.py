#!/usr/bin/env python

from SubspaceBot import *
from BotUtilities import ModuleData,BotInterface,botMain
import logging



class Bot(BotInterface):
	def __init__(self,ssbot,md):
		BotInterface.__init__(self,ssbot,md)
		#register Your Module
		ssbot.registerModuleInfo(__name__,"Template","The Junky","displays/checks players lag",".01")
		#register your commands 

		self.cmd_dict = {
		#add commands here like below but followed by a comma, only the last command doesnt have a comma after it.				
		ssbot.registerCommand('!whatthef', #command  
							"!wtf", #alias can be None if no alias
							0, #min access level to use this command
							COMMAND_LIST_PP, #what types of messages this command will accept
							"w.t.f", #category this command belongs to
							"<name>", #what args if any this command accepts use "" if none
							"what the f") #short description of the command displayed in help 
							: self.cmdWTF #cmdHandler(self,ssbot,event)

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
			pass
		elif event.type == EVENT_DISCONNECT:
			pass	
	def cmdWTF(self,ssbot,event):
		ssbot.sendReply(event,"wtf")
	def Cleanup(self):
		#put any cleanup code in here this is called when bot is about to die
		pass


if __name__ == '__main__':
	botMain(Bot)

