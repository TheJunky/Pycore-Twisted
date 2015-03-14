#!/usr/bin/env python

from SubspaceBot import *
from BotUtilities import *


# your custom player info classes have to follow this format
class MyPI():
	def __init__(self):
		self.wins = 0
		self.losses = 0;


class Bot(BotInterface):
	def __init__(self,ssbot,md):
		BotInterface.__init__(self,ssbot,md)
		#register Your Module
		ssbot.registerModuleInfo(__name__,"FFA","The Junky","Example of ffa to 3 event",".01")
		#register your commands 
		self.cmd_dict = {
		ssbot.registerCommand('!FFA', #command  
							None, #alias can be None if no alias
							1, #min access level to use this command
							COMMAND_LIST_PP, #what types of messages this command will accept
							"FFA", #category this command belongs to
							"[on|off]", #what args if any this command accepts use "" if none
							"turn ffa on") #short description of the command displayed in help 
							: self.cmdFFA #cmdHandler(self,ssbot,event)

		}
		#do any other initialization code here
		self.state = 0#off
		self.locked = 0
		self.setPlayerInfoOptions(self.module.MyPI)
		self.maxlosses = 3
		self.winner = None
		
	def HandleEvents(self,ssbot,event):
		#whatever events your bot needs to respond to add code here to do it
		if event.type == EVENT_LOGIN:
			pass
		elif (event.type == EVENT_COMMAND and event.command.id in self.cmd_dict):
			self.cmd_dict[event.command.id](ssbot,event)
		elif event.type == EVENT_TICK:
			timer_expired = self.getExpiredTimer()
			if timer_expired:
				d = timer_expired.data
				if d == 0:
					ssbot.sendPublicMessage("FFa starting in 30 seconds")
					self.tm.set(25,1)
				if d == 1:
					ssbot.sendPublicMessage("FFa starting in 5 seconds")
					self.tm.set(1,2)
				if d == 2:
					ssbot.sendPublicMessage("4")
					self.tm.set(1,3)
				if d == 3:
					ssbot.sendPublicMessage("3")		
					self.tm.set(1,4)
				if d == 4:
					ssbot.sendPublicMessage("2")
					self.tm.set(1,5)
				if d == 5:
					ssbot.sendPublicMessage("1")
					self.tm.set(1,6)
				if d == 6:
					ssbot.sendPublicMessage("GO GO GO")
					ssbot.sendPublicMessage("*lock")
					self.lock = 1
					self.state = 2
					for p in ssbot.players_here:
						if p.ship != SHIP_SPECTATOR:
							ssbot.sendPrivateMessage(p,"*setfreq %i"%(p.pid,))
							ssbot.sendPrivateMessage(p,"*shipreset")
							ssbot.sendPrivateMessage(p,"*scorereset")
							pi = self.getPlayerInfo(p.name)
							pi.wins = 0
							pi.losses = 0
						
		elif event.type == EVENT_MESSAGE:
			if event.message_type == MESSAGE_TYPE_SYSTEM:
				if event.message == "Arena LOCKED":
					if self.locked == 0:
						ssbot.sendPublicMessage("*lock")
				if event.message == "Arena UNLOCKED":
					if self.locked == 1:
						ssbot.sendPublicMessage("*lock") 
		elif event.type == EVENT_ENTER:
			pass
		elif event.type == EVENT_LEAVE and self.state == 2:
			# checking for state == 2 is  to only make this code execute when the bot is "on"
			if event.player.ship != SHIP_SPECTATOR:
				c = self.CountPlaying(ssbot)
				if c == 1:
					self.HandleWin(ssbot)

		elif event.type == EVENT_CHANGE and self.state == 2:
			if (event.old_ship != SHIP_SPECTATOR and event.player.ship == SHIP_SPECTATOR):
				c = self.CountPlaying(ssbot)
				if c == 1:
					self.HandleWin(ssbot)
			
		elif event.type == EVENT_KILL and self.state == 2:
			killer = event.killer
			kri = self.getPlayerInfo(killer.name)
			killed = event.killed
			kdi = self.getPlayerInfo(killed.name)
			kdi.losses+=1
			kri.wins+=1
			ssbot.sendPublicMessage("*arena %s[%i:%i] killed by %s[%i:%i]"%(killed.name,kdi.wins,kdi.losses,killer.name,kri.wins,kri.losses))
			if(kdi.losses >= self.maxlosses):
				ssbot.sendPublicMessage("*arena %s is out [%i:%i]"%(killed.name,kdi.wins,kdi.losses))
				ssbot.sendPrivateMessage(killed,["*spec","*spec","You are out"])		
		elif event.type == EVENT_DISCONNECT:
			pass
	def HandleWin(self,ssbot):
		for p in ssbot.players_here:
			if p.ship != SHIP_SPECTATOR: #there should only be one person in a ship
				winner = p
				wi = self.getPlayerInfo(winner.name)
				break
		ssbot.sendPublicMessage("*arena %s wins [%i:%i]"%(winner.name,wi.wins,wi.losses))
		self.state = 0#off
		self.locked = 0
		
			
	def CountPlaying(self,ssbot):
		i = 0
		self.winner = None
		for p in ssbot.players_here:
			if p.ship != SHIP_SPECTATOR:
				i+=1
		return i
				
	def cmdFFA(self,ssbot,event):
		if len(event.arguments) > 0:
			if event.arguments[0] == "on":
				if self.state == 0:
					self.state = 1
					ssbot.sendReply(event,"Ok")
					self.tm.set(0,0)
					#ssbot.sendPublicMessage("FFa starting in 2 minutes")
				else:
					ssbot.sendReply(event,"Bot's On")
			elif event.arguments[0] == "off":
				if self.state != 0:
					self.state = 0
					self.tm.deleteAll()
					ssbot.sendReply(event,"ffa off")
			
	def Cleanup(self):
		#put any cleanup code in here this is called when bot is about to die
		pass


if __name__ == '__main__':
	botMain(Bot)
