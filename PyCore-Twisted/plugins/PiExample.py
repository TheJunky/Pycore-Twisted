#!/usr/bin/env python

from SubspaceBot import *
from BotUtilities import ModuleData,BotInterface,botMain
import logging


class PlayerInfo():
	def __init__(self):
		self.kills_in_a_row = 0


class Bot(BotInterface):
	def __init__(self,ssbot,md):
		BotInterface.__init__(self,ssbot,md)
		#register Your Module
		ssbot.registerModuleInfo(__name__,"Spree","The Junky","displays/checks players lag",".01")
		self.setPlayerInfoOptions(self.module.PlayerInfo)
		
	def HandleEvents(self,ssbot,event):
		#whatever events your bot needs to respond to add code here to do it
		if event.type == EVENT_KILL:
			killer = event.killer
			killer = event.killed
			killerpi = self.getPlayerInfo(killer.name)
			killedpi = self.getPlayerInfo(killed.name)
			killerpi.kills_in_a_row+=1
			if killedpi.kills_in_a_row > 20:
				ssbot.sendArenaMessage("%s's Spree of %i kills ended by %s" %(killed.name,killedpi.kills_in_a_row,killer.name))
			if killerpi.kills_in_a_row > 20 and (killerpi.kills_in_a_row %10)==0: #if he has 20 kills it will announce then it will announce every 10 kills 
				ssbot.sendArenaMessage("%s is on fire and is on a killing spree of %i kills" %(killer.name,killerpi.kills_in_a_row))	
			
	def Cleanup(self):
		#put any cleanup code in here this is called when bot is about to die
		pass


if __name__ == '__main__':
	botMain(Bot)
