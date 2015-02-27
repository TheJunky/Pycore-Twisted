'''
@author: The Junky
'''
# -*- coding: UTF-8 -*-
#masterbot for cycad's python core written by The Junky<thejunky@gmail.com>
import os


from SubspaceBot import *
from BotUtilities import *
import logging


class BotInstance():
	def __init__(self,id,type,description,owner,bname,bpassword,inifile,host,port,arena,modules,MQueue,args,logger):
		self.id = id
		self.type = type
		self.description = description
		self.owner = owner
		self.bname = bname
		self.bpassword = bpassword
		self.inifile = inifile
		self.host = host
		self.port = port
		self.arena = arena
		self.modules = modules
		self.ssbot = None
		self.keepgoing = True
		self.logger = logger
		self.MQueue = MQueue
		self.args = args
		self.listeningport = None
	def RequestStop(self):
		if self.ssbot != None:
			self.ssbot.disconnectFromServer()
	def queueBroadcast(self,event):#used by master
		if self.ssbot:
			self.ssbot.queueBroadcast(event)
	def is_alive(self):
		return self.ssbot.isConnected()

	def AddToReactor(self,reactor):
		try:
			BotList = []
			ssbot = SubspaceBot(self.host, 
									self.port,
									self.bname,
									self.bpassword, 
									self.arena,
									False,
									BM_SLAVE,
									self.MQueue,
									logging.getLogger("ML." +self.type +".Core"))
			ssbot.setBotInfo(self.type,self.description,self.owner)
			self.ssbot = ssbot
			ssbot.arena = self.arena# serexl's bots look at arena in init
			bot = None
			for m in self.modules:
				bot = LoadBot(ssbot,m[0],m[1],self.inifile,self.args,logging.getLogger("ML." +self.type +"."+ m[0]))
				if bot:
					BotList.append (bot)
				bot = None
			ssbot.setBotList(BotList)
			self.listeningport = reactor.listenUDP(0, ssbot)
			ssbot.setReactorData(reactor,self.listeningport)
			

		except:
			LogException(self.logger)  
		finally:
			if ssbot.isConnected():
				ssbot.disconnectFromServer()
			for b in BotList:
				b.Cleanup()

						
