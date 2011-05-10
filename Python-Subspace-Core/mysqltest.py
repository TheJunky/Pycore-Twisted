'''
@author: The Junky
'''

from BotUtilities import *
from SubspaceBot import *

import TimerManager
from Amysql import *
import copy


class Bot(BotInterface):
	def __init__(self, bot, md):
		BotInterface.__init__( self, bot, md)
		bot.registerModuleInfo(__name__,"MysqLtest","The Junky","mysqlclient for ss",".01")
		self._db = Amysql(self.logger)
		self._db.setDbCredentialsFromFile(self.module_path + R"/db.conf","db")
		self._db.start()
		self.clist = [COMMAND_TYPE_PUBLIC,COMMAND_TYPE_TEAM,COMMAND_TYPE_FREQ,COMMAND_TYPE_PRIVATE,COMMAND_TYPE_CHAT]
		self._sql_command_id = bot.registerCommand('!sql',None,9,self.clist,"web","[query]" , 'sql it zz')
		self._sqlnl_command_id = bot.registerCommand('!sqlnl',None,9,self.clist,"web","[query]" , 'sql it zz')
		self.level = logging.DEBUG
		self.timer_man = TimerManager.TimerManager()
		self.timer_man.set(.01, 1)
		self.timer_man.set(300, 2)
		self.chat = bot.addChat("st4ff")
		#formatter = logging.Formatter('%(name)s:%(message)s')
		#chathandler = loggingChatHandler(logging.DEBUG,bot,1)
		#chathandler.setFormatter(formatter)
		#self.logger.addHandler(chathandler)
		
	def HandleEvents(self,ssbot,event):
		
		if event.type == EVENT_COMMAND:
			if event.command.id in [self._sql_command_id,self._sqlnl_command_id]:
				
				if event.command.id == self._sql_command_id: #automatically addlimit or not
					limit = " limit 100"
				else:
					limit = ""
						
				if event.command_type in [MESSAGE_TYPE_PRIVATE,MESSAGE_TYPE_REMOTE]:
					target = event.pname
				elif event.command_type == MESSAGE_TYPE_FREQ:
					target = event.player.freq
				elif event.command_type == MESSAGE_TYPE_CHAT:
					target = event.chat_no
				else:
					target = None

				db = self._db
				db.query(event.arguments_after[0] + limit , None, (event.command_type,target)) 

		elif event.type == EVENT_TICK:
			timer_expired = self.timer_man.getExpired() # a timer expired
			#self.logger.info("tick")
			if timer_expired:
				#self.logger.info("timer expired")
				
				if timer_expired.data == 1:
					#self.logger.info("1")
					r = self._db.getResults()
					if r:# most of the time this will be None so check first
						self.HandleResults(ssbot,event,r)
					self.timer_man.set(1, 1) #set it to check again in a sec
				elif timer_expired.data == 2:
					#self.logger.info("2")
					self._db.ping()
					self.timer_man.set(300, 2)

	def HandleResults(self,ssbot,event,r):
		if r.getType() == AElement.TYPE_MESSAGE: #message like connection error or connected
			self.logger.info(r.message)
		else:
			r.GenericResultPrettyPrinter(ssbot,r.query.data[0],r.query.data[1])
		
	def Cleanup(self):
		self._db.CleanUp()

if __name__ == '__main__': #bot runs in this if not run by master u can ignore this 
	botMain(Bot,False,True)

