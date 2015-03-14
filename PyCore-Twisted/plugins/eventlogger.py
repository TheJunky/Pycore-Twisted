#!/usr/bin/env python

from SubspaceBot import *
from BotUtilities import *


class Bot(BotInterface):
	"""
	all bots that run on the master have to extend Botinterface
	bot interface contains all the interface code that is 
	required by the master, for master to start,stop,display info
	about your bot
	"""
	def __init__(self,ssbot,md):
		"""
		This is the first function that will be run in your bot.
		all initialization code should be put here
		"""
		# you have to run this function, it will initialize the bot interface
		BotInterface.__init__(self,ssbot,md)
		#register Your Module, this info will be displayed in !version
		ssbot.registerModuleInfo(__name__,"eventlogger","The Junky","logs events to file",".01")
		#register your commands 
		self.cmd_dict = {
		ssbot.registerCommand('!logger', #command  
							"!log", #alias can be None if no alias
							0, #min access level to use this command
							COMMAND_LIST_PP, #what types of messages this command will accept
							"w.t.f", #category this command belongs to
							"[on|off]", #what args if any this command accepts use "" if none
							"turn on/off display log") #short description of the command displayed in help 
							: self.cmdLOG #cmdHandler(self,ssbot,event)
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
		if event.type == EVENT_TICK:
			#alot of spamm
			#self.logger.info("Tick")
			pass
		elif event.type == EVENT_DISCONNECT:
			self.logger.info("Disconnected")
		elif event.type == EVENT_LOGIN:
			self.logger.info("Logged in")
			ssbot.sendPublicMessage("?arena")
		elif event.type == EVENT_MESSAGE:
			self.logger.info("message:(%i):(%s):%s"%(event.message_type,event.pname,event.message))
		elif event.type == EVENT_ENTER:
			self.logger.info("Entered:" + event.player.name)
		elif event.type == EVENT_LEAVE:
			self.logger.info("left:" + event.player.name)
		elif event.type == EVENT_CHANGE:
			self.logger.info("change:%s:(f:%i:s%i)->(%i:%i)" %
							(event.player.name,event.old_freq,
							event.old_ship,event.player.freq,event.player.ship))	
		elif (event.type == EVENT_COMMAND and event.command.id in self.cmd_dict):
			self.logger.info("cmd:"+event.command.name)
			self.cmd_dict[event.command.id](ssbot,event)
		elif event.type == EVENT_POSITION_UPDATE:
			#alot of spam every few ms
			pass	
		elif event.type == EVENT_KILL:
			self.logger.info("%s killed by %s[%i,%i,%i]"%(event.killer.name,event.killed.name,event.bounty,event.flags_transfered,event.death_green_id))
		elif event.type == EVENT_ARENA_LIST:
			c= 0
			self.logger.info("-------------ArenaList---------")
			for a in event.arena_list:
				self.logger.info(a[0]+":  "+str(a[1])+ ("" if a[2] == 0 else "  <--YOU ARE HERE"))
		elif event.type == EVENT_GOAL:
			self.logger.info("Goal: freq:%i points:%i" %(event.freq,event.points))
		elif event.type == EVENT_FLAG_PICKUP:
			self.logger.info("Flag Pickup: player:%s fid:%i transfered from:%i" %(event.player.name,event.flag_id,event.transferred_from))
		elif event.type == EVENT_FLAG_DROP:
			self.logger.info("flag_drop: player:%s count:%i" %(event.player.name,event.flag_count))	
		elif event.type == EVENT_TURRET:
			if event.old_turreted is None:
				self.logger.info("Attach:turreter:%s turreted:%s" %(event.turreter.name,event.turreted.name))
			else:
				self.logger.info("Detach:%s detached from %s" %(event.turreter,event.old_turreted))
		elif event.type == EVENT_PERIODIC_REWARD:
			for p in event.point_list:
				self.logger.info("Rewards:%i given %i"% p)
		elif event.type == EVENT_BALL:
			#this even is alot of spamm
			#n=None if event.player is None else event.player.name
			#t=(n,event.ball_id,event.x_pos,
			#event.y_pos,event.x_vel,event.y_vel,event.time)
			#self.logger.info("Ball:%s: [%i,%i,%i,%i,%i,%i]"%t)				
			pass
		elif event.type == EVENT_PRIZE:
			self.logger.info("%s picked up prize(%i) at (%i,%i)" %(event.player.name,event.prize,event.x,event.y))
		elif event.type == EVENT_SCORE_RESET:
			self.logger.info("Scorereset:" + "All" if event.player is None else event.player.name)
		elif event.type == EVENT_FLAG_UPDATE:
			#this spams alot
			#self.logger.info("flagupdate:%i: at %i,%i owned by freq:%i" %(event.flag_id,event.x,event.y,event.freq))
			pass
		elif event.type == EVENT_FLAG_VICTORY:
			self.logger.info("Flag Victory:%i won %i points" %(event.freq,event.points))
		elif event.type == EVENT_ARENA_CHANGE:
			self.logger.info("arena changed:" + event.old_arena + "-> " + ssbot.arena)
		elif event.type == EVENT_WATCH_DAMAGE:
			#spam, info when you do /*watchdamage to a player"
			pass
		elif event.type == EVENT_BRICK:
			for b in event.brick_list:
				t = (b.id,b.freq,b.x1,b.y1,b.x2,b.y2,b.timestamp)
				self.logger.info("Brick:%i:%i at [(%i,%i),(%i,%i)] ts:%i")
			pass
		elif event.type == EVENT_SPEED_GAME_OVER:
			pass

					
	def cmdLOG(self,ssbot,event):
		ssbot.sendReply(event,"log")
	def Cleanup(self):
		#put any cleanup code in here this is called when bot is about to die
		pass


if __name__ == '__main__': 
	#bot runs in this if not run by master
	#generic main function for when you run bot in standalone mode
	#we pass in the Bot class to the function, so it can run it for us
	botMain(Bot)
