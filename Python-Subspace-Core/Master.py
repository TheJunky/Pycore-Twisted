'''
@author: The Junky <thejunky@gmail.com>
'''

import logging
from logging import NOTSET
from optparse import OptionParser
from SubspaceBot import *
from BotUtilities import *
from BotConfig import GlobalConfiguration
import BotInstance
import time
import copy

class Bot(BotInterface):
	def __init__(self,ssbot,md,config,MQueue):
		BotInterface.__init__( self, ssbot, md)
		ssbot.registerModuleInfo(__name__,"MasterBot","The Junky","Manages other bots (starts/stops/lists/etc)","1.0d")
		self.config = config
		self._cmd_handlers = { 
		#Cmd_ID,								  cmd_handler_func
		ssbot.registerCommand('!startbot',"!sb",2,COMMAND_LIST_ALL,"Core","" ,'!startbot type arena') : self.HCStartBot,
		ssbot.registerCommand('!killbot',"!kb",2,COMMAND_LIST_ALL,"Core","", '!killbot name') : self.HCStopBot,
		ssbot.registerCommand('!listbots',"!lb",2,COMMAND_LIST_PP,"Core","" ,'!listbots') : self.HCListBots,
		ssbot.registerCommand('!listbottypes',"!lt",2,COMMAND_LIST_PP,"Core","" ,'!listtypes') : self.HCListBotTypes,
		ssbot.registerCommand('!reloadconf',"!rc",3,COMMAND_LIST_ALL,"Core","" ,'reload config') : self.HCLoadConfig,
		ssbot.registerCommand('!unloadmodule',"!um",7,COMMAND_LIST_ALL,"Core","" ,'unload a specific module from systems.module') : self.HCUnloadModule,
		ssbot.registerCommand('!log',None,2,COMMAND_LIST_PP,"Core","[-clear]" , 'default shows log, -clear to clear onscreen log') : self.HCLog}
		self._last_instance_id = 0
		self._instances = {}
		#this will copy all log entries to a list, so i can use it for !log
		self.max_recs = 40		
		self.listhandler = ListHandler(logging.DEBUG,self.max_recs)
		formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
		self.listhandler.setFormatter(formatter)
		self.listhandler.LoadFromFile(os.getcwd()+ R"/Bots.log")
		self.logger.addHandler(self.listhandler)

		self.logger.info("Master Bot Started")
		if len(config.MasterChats) > 0:
			ssbot.addChat(config.MasterChats)
		
		self.__queue = MQueue
		
	def GetBotConfig(self,type):
		for b in self.config.Bots.values():
			if b.Type.lower() == type.lower():
				return b
		else:
			return None
	def GenerateValidNames(self,type):
		bconfig = self.GetBotConfig(type)
		maxbots = bconfig.MaxBots
		validnames = []
		name = bconfig.Name
		if(maxbots > 1):
			for i in range(1,maxbots):
				validnames.append (  name + i )
		else:
			validnames.append (name)
		return validnames

	def DeleteInactiveBots(self):
		keys2del = []
		for k,v in self._instances.iteritems():
			if v.is_alive()==1:
				pass
			else:
				keys2del.append(k)
		for k in keys2del:
			del self._instances[k]
	def HCShutdown(self,ssbot,event):
		ssbot.disconnectFromServer()
		ssbot.sendReply(event,"ok" )
		self.logger.critical("Master is being Shutdown command issued by: " + event.pname)
		#raise ShutDownException("Master is being Shutdown command issued by: " + event.pname)
	def HCStartBot(self,ssbot,event):
		self.DeleteInactiveBots()
		if len(event.arguments) >= 2:
			type = event.arguments[0]
			bconfig = self.GetBotConfig(type)
			if bconfig != None :
				validname = None
				for n in self.GenerateValidNames(type):
					if(n in self._instances):
						continue
					else:
						validname = n
						break
				if(validname != None):
					self._last_instance_id+= 1
					arena = event.arguments[1]
					newbot = BotInstance.BotInstance(self._last_instance_id,
												  bconfig.Type,
												  bconfig.Description,
												  event.pname,
												  bconfig.Name,
												  bconfig.Password,
												  bconfig.ConfigurationFile,
												  self.config.Host,
												  self.config.Port,
												  arena,
												  bconfig.Modules,
												  self.__queue,
												  event.arguments_after[2] if len(event.arguments) > 2 else "",
												  logging.getLogger("ML." + bconfig.Type))
					self._instances[newbot.bname.lower()] = newbot
					newbot.start()
					ssbot.sendReply(event, "ok")
					self.logger.info("%s started to %s by %s"%(bconfig.Type,arena,event.pname))
				else:
					ssbot.sendReply(event, "all %s in use"%(type))
			else:
				ssbot.sendReply(event,"Error:type(%s) not found"%(type))
		else:
			ssbot.sendReply(event, "Usage: !startbot type arena")


	def HCStopBot(self,ssbot,event):
		if (len(event.arguments) == 1 and 
			event.arguments[0].lower() in self._instances):
			b = self._instances[event.arguments[0].lower()]
			b.RequestStop()
			ssbot.sendReply(event,"Stop Requested")
			self.logger.info("%s killed %s (Stop Requested)",event.pname,event.arguments[0])
		else:
			ssbot.sendReply(event,"Bot Not Found")
			
	def HCListBots(self,ssbot,event):
		c = 0
		for v in self._instances.values():
			ssbot.sendReply(event,"ID:%3i Type:%6s Name:%20s Arena:%10s alive:%i" %
									 (v.id,v.type,v.bname,v.arena,v.is_alive()))
			c+=1
		if c == 0:
			ssbot.sendReply(event,"No Active Bots")
	def HCListBotTypes(self,ssbot,event):
		if len(event.arguments) == 1:
			b = self.config.Bots.get(event.arguments[0].lower(),None)
			if b:
				ssbot.sendReply(event,"Type: " + b.Type)
				ssbot.sendReply(event,"Description: " + b.Description)
				ssbot.sendReply(event,"BotBaseName: " + b.Name)
				ssbot.sendReply(event,"TotalBots: " + str(b.MaxBots))
				ssbot.sendReply(event,"ConfigFile: " + b.ConfigurationFile)
				txt = ""
				c = 0
				ssbot.sendReply(event,"-" * 10 + "Modules" + "-" * 10)
				for b in b.Modules:
					if c != 0 and c % 2 == 0:
						ssbot.sendReply(event,"Modules:" + txt[1:])
						txt = ""
					txt += "," + b[0]
					c+=1
			
				if len(txt) > 0:
					ssbot.sendReply(event,"Modules:" + txt[1:]) 
			else:
				ssbot.sendReply(event,"Error:type(%s) not found"%(event.arguments[0]))
		else:
			c = 0
			txt = ""
			for b in self.config.Bots.values():
				c+=1
				if(c % 5 == 0):
					ssbot.sendReply(event,"Types:" + txt[1:])
					txt = ""
				txt += "," + b.Type
			
			if len(txt) > 0:
				ssbot.sendReply(event,"Types:" + txt[1:]) 
			if c == 0:
				ssbot.sendReply(event,"No Bot Types Defined")
	def HCUnloadModule(self,ssbot,event):
		if len(event.arguments) > 0:
			name = event.arguments[0]
			if name in sys.modules:
				del sys.modules[name]
				ssbot.sendReply(event,"module unloaded")
			else:
				ssbot.sendReply(event,"module not found")
		else:
			ssbot.sendReply(event,"invalid syntax")
					
	def HCLog(self,ssbot,event):
		if len(event.arguments) > 0 and event.arguments[0].lower() == "-clear":
			self.listhandler.Clear()
			ssbot.sendReply(event,"on screen log cleared")
		else:
			for r in self.listhandler.GetEntries():
				ssbot.sendReply(event,r)
	
	def HCLoadConfig(self,ssbot,event):
		try:
			oc = copy.deepcopy(self.config)
			self.config.Load()
			ssbot.sendReply(event,"Config Reloaded")
			self.logger.info("config file reloaded by %s" %(event.pname,))
		except:
			self.config = oc
			ssbot.sendReply(event,"failure, still using old configuration")						 
	def HandleEvents(self,ssbot,event):
		if event.type == EVENT_COMMAND and event.command.id in self._cmd_handlers:
			self._cmd_handlers[event.command.id](ssbot,event)
		elif event.type == EVENT_TICK:
			self.SendBroadcastsToAttachedBots(ssbot)
		elif event.type == EVENT_LOGIN:
			ssbot.setTimer(10, (2,None))# for periodic deleting of inactive bots and removing of old list entries from log
			c = 60#wait for bot to login
			for b in self.config.AutoLoad:#stagger the bots to load by 180 sec each
				c+=180
				ssbot.setTimer(c, (1,b))
				self.logger.info("Queued:[Sb] %s -> %s" % b)
		elif event.type == EVENT_TIMER:
			if (event.user_data != None
			and type(event.user_data) == types.TupleType
			and len(event.user_data) == 2): 
				if event.user_data[0] == 1:#start a bot
					t = event.user_data[1]
					ssbot.sendPublicMessage("!sb %s %s" % t)
				elif event.user_data[0] == 2:#do maintenance
					self.DeleteInactiveBots()
					self.listhandler.RemoveOld()
					ssbot.setTimer(10, (2,None))
	
	def SendBroadcastsToAttachedBots(self,ssbot):
		if self.__queue.size() > 0: # broadcasts waiting
				b = self.__queue.dequeue() 
				while b: #broadcasts waiting
					for bot in self._instances.values():
						if bot.is_alive():
							bot.queueBroadcast(b)#all attached bots
					ssbot.queueBroadcast(b)#modules attached to master
					b = self.__queue.dequeue()#will return None if there are none
				
	def Cleanup(self):
		for v in self._instances.values():
			v.RequestStop()
		
		for v in self._instances.values():
			v.join(10)

def MasterMain():
	try:
		#other bots use logging i dont want it to spamm the main logger
		rootlogger = logging.getLogger('')
		rootlogger.addHandler(NullHandler())
		rootlogger.setLevel(logging.CRITICAL)
		#logging.basicConfig(level=logging.ERROR,
		#					format='%(asctime)s:%(name)s:%(levelname)s:%(message)s',
		#					datefmt='%m-%d %H:%M')
		
		logger = logging.getLogger("ML")
		logger.setLevel(logging.DEBUG)	
		
		
		# set a format
		formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
		
		
		# define a Handler which writes INFO messages or higher to the sys.stderr
		console = logging.StreamHandler()
		console.setLevel(logging.DEBUG)
		# tell the handler to use this format
		console.setFormatter(formatter)
		# add the handler to the mainloop logger
		logger.addHandler(console)
	
		
		filehandler  = logging.FileHandler(os.getcwd()+ R"/Bots.log",mode='a')
		filehandler.setLevel(logging.ERROR)
		filehandler.setFormatter(formatter)
		logger.addHandler(filehandler)
	
		#command Line Options
		parser = OptionParser()
		
		parser.add_option("-c", "--ConfigFile", dest="ConfigFile",
					  help="Load Configuration from a non default file",
					  default=os.getcwd() + R"\Bots.json")
		
		
		parser.add_option("-p", "--Password", dest="Password",
					  help="pass sysop/smod pass by commandline instead of in config",
					  default=None)
		
		(options, args) = parser.parse_args()
	
		Queue = MasterQue()
		ssbot = SubspaceBot(False,True,Queue,logging.getLogger("ML.Master.Core"))
		ssbot.setBotInfo("Master","MasterBot Manages the starting/stopping of bots", None)
		BotList = [ ]
		config = GlobalConfiguration(options.ConfigFile,options.Password)
		#this adds dir's to pythonpath so we can run the dev code out of seperate dirs
		for p in config.paths:
			sys.path.append(p)
		#get the module object for the current file...	
		module = sys.modules[globals()['__name__']]
		#loads atleast the masterbot
		md = ModuleData("Master",module,"None",config.ConfigurationFile,"",logging.getLogger("ML.Master"))
		master = Bot(ssbot,md,config,Queue)
		BotList.append(master)
		#load any bots that are specified in the config
		bot = None
		for m in config.Modules:
			bot = LoadBot(ssbot,m[0],m[1],config.ConfigurationFile,"",logging.getLogger("ML.Master."  + m[0]))
			if bot:
				BotList.append (bot)
			bot = None
		
		#while 1:
		ssbot.connectToServer(config.Host,
							  config.Port, 
							  config.MasterName, 
							  config.MasterPassword,
							  config.MasterArena)		   
		while ssbot.isConnected():
				event = ssbot.waitForEvent()
				for b in BotList:
					b.HandleEvents(ssbot,event)
		logger.critical("Master disconnected")
			#if ssbot.shouldReconnect():				
			#	ssbot.resetState()
			#	time.sleep(120)
			#	logger.critical("Reconnecting")
			#else:
			#	break	
		
	except (KeyboardInterrupt, SystemExit):
		logger.critical("CTRL-c or System.exit() detected")	
	except:
		logger.critical("Unhandled Exception")
		LogException(logger)
		
	finally:
		if ssbot.isConnected():
			ssbot.disconnectFromServer()
		logger.info( "Master disconnected" )
		logger.info( "Waiting For Bots to stop")
		for b in BotList:
			b.Cleanup()
		logger.critical("Master shutting down")
		filehandler.close()
		
		
if __name__ == '__main__':
	profile = True
	if profile:
		import cProfile
		filename = time.strftime("bot-%a-%d-%b-%Y-%H-%M-%S.profile", time.gmtime())
		cProfile.run('MasterMain()',filename)
		import pstats
		p = pstats.Stats(filename)
		p.sort_stats('cumulative')
		p.print_stats(.1)
		pass
	else:
		MasterMain()

	