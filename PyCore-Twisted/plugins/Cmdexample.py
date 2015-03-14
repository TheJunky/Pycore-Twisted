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
							: self.cmdWTF, #cmdHandler(self,ssbot,event)
		ssbot.registerCommand('!whatthef2', #command  
							"!wtf2", #alias can be None if no alias
							0, #min access level to use this command
							COMMAND_LIST_PP, #what types of messages this command will accept
							"w.t.f", #category this command belongs to
							"<name>", #what args if any this command accepts use "" if none
							"what the f") #short description of the command displayed in help 
							: self.cmdWTF2 #cmdHandler(self,ssbot,event)					

		}
		#do any other initialization code here
		#...

		
	def HandleEvents(self,ssbot,event):
		#whatever events your bot needs to respond to add code here to do it
		if event.type == EVENT_LOGIN:
			self.setTimer(10,1)#set timer for 10 secs from now
			self.setTimer(50,2)#set timer for 10 secs from now
			pass
		elif (event.type == EVENT_COMMAND and event.command.id in self.cmd_dict):
			self.cmd_dict[event.command.id](ssbot,event)
		elif event.type == EVENT_TICK:
			#Example of timers 
			timer_expired = self.getExpiredTimer()
			while(timer_expired):	
				if timer_expired.data == 1: #timer_expired is now the data we passed to timer
					print("i logged in 10 seconds ago")
					self.setTimer(10,3)#set timer for 10 secs from now
				elif timer_expired.data == 2: #timer_expired is now the data we passed to timer
					print("i logged in 50 seconds ago")
				elif timer_expired.data == 3: #timer_expired is now the data we passed to timer
					print("woo 10 Secs")
					self.setTimer(10,3)#set timer for 10 secs from now so it repeats every 10 secs	
				timer_expired = self.getExpiredTimer()	
				
		elif event.type == EVENT_DISCONNECT:
			pass	
	def cmdWTF(self,ssbot,event):
		ssbot.sendReply(event,"wtf")
	def cmdWTF(self,ssbot,event):
		ssbot.sendReply(event,"wtf2: "+ event.pname)	
	def Cleanup(self):
		#put any cleanup code in here this is called when bot is about to die
		pass


if __name__ == '__main__':
	botMain(Bot)

