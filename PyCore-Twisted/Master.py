'''
@author: The Junky <thejunky@gmail.com>
'''

import logging
from logging import NOTSET
from optparse import OptionParser
from SubspaceBot import *
from BotUtilities import *
from BotConfig import GlobalConfiguration
import copy
import os
from TimerManager import TimerManager

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
				
				
				
class Bot(BotInterface):
	def __init__(self,ssbot,md,config,MQueue):
		BotInterface.__init__( self, ssbot, md)
		ssbot.registerModuleInfo(__name__,"MasterBot","The Junky","Manages other bots (starts/stops/lists/etc)","1.0d")
		self.config = config
		self._cmd_handlers = { 
		#Cmd_ID,								  cmd_handler_func
		ssbot.registerCommand('!shutdown',None,7,COMMAND_LIST_ALL,"Master","" ,'Shutdown the master') : self.HCShutdown,
		ssbot.registerCommand('!startbot',"!sb",2,COMMAND_LIST_ALL,"Master","[type] [arena]" ,'!startbot type arena') : self.HCStartBot,
		ssbot.registerCommand('!killbot',"!kb",2,COMMAND_LIST_ALL,"Master","[name]", 'Stop a specific bot') : self.HCStopBot,
		ssbot.registerCommand('!listbots',"!lb",2,COMMAND_LIST_ALL,"Master","" ,'lists all currently running bots') : self.HCListBots,
		ssbot.registerCommand('!listbottypes',"!lt",2,COMMAND_LIST_ALL,"Master","" ,'!lists all bot types currently defined in config file') : self.HCListBotTypes,
		ssbot.registerCommand('!reloadconf',"!rc",3,COMMAND_LIST_ALL,"Master","" ,'reload json config file') : self.HCLoadConfig,
		ssbot.registerCommand('!unloadmodule',"!um",7,COMMAND_LIST_ALL,"Master","[modulename]" ,'unload a specific module from systems.module') : self.HCUnloadModule,
		ssbot.registerCommand('!log',None,2,COMMAND_LIST_PP,"Master","[-clear]" , 'default shows last 100 lines from the core logger') : self.HCLog}
		self._last_instance_id = 0
		self._instances = {}
		#this will copy all log entries to a list, so i can use it for !log
		self.max_recs = 40		
		self.listhandler = ListHandler(logging.DEBUG,self.max_recs)
		formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s:%(message)s')
		self.listhandler.setFormatter(formatter)
		self.listhandler.LoadFromFile(os.path.join(os.getcwd(),"Bots.log"))
		self.logger.addHandler(self.listhandler)

		self.logger.info("Master Bot Started")
		if len(config.MasterChats) > 0:
			ssbot.addChat(config.MasterChats)
		
		self.__queue = MQueue
		self.reactor= None
		
		self.tm = TimerManager()
		
	
	def setReactor(self,reactor):
		self.reactor=reactor
			
	def GetBotConfig(self,btype):
		for b in self.config.Bots.values():
			if b.Type.lower() == btype.lower():
				return b
		else:
			return None
	def GenerateValidNames(self,btype):
		bconfig = self.GetBotConfig(btype)
		maxbots = bconfig.MaxBots
		validnames = []
		name = bconfig.Name
		if(maxbots > 1):
			for i in range(1,maxbots):
				validnames.append (  name + str(i) )
		else:
			validnames.append (name)
		return validnames
	
	def StopAllBots(self):
		for k,v in self._instances.iteritems():
			if v.is_alive()==1:
				v.RequestStop()
				self.logger.critical("Requested Stop for "+v.bname)

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
		self.StopAllBots()
		ssbot.sendReply(event,"ok" )
		self.logger.critical("Master is being Shutdown command issued by: " + event.pname)
		self.tm.set(10, (3,None))
		
	def StartBot(self,ssbot,pname,btype,arena,args):
		bconfig = self.GetBotConfig(btype)
		if bconfig != None :
			validname = None
			for n in self.GenerateValidNames(btype):
				if(n.lower() in self._instances):
					continue
				else:
					validname = n
					break
			if(validname != None):
				self._last_instance_id+= 1
				newbot = BotInstance(self._last_instance_id,
											  bconfig.Type,
											  bconfig.Description,
											  pname,
											  validname,
											  bconfig.Password,
											  bconfig.ConfigurationFile,
											  self.config.Host,
											  self.config.Port,
											  arena,
											  bconfig.Modules,
											  self.__queue,
											  args,
											  logging.getLogger("ML." + bconfig.Type))
				self._instances[newbot.bname.lower()] = newbot
				newbot.AddToReactor(self.reactor)
				self.logger.info("%s started to %s by %s"%(bconfig.Type,arena,pname))
				return 1 #success
			else:
				return -2 #all bots of type used
		else:
			return -1 #type not found
	def HCStartBot(self,ssbot,event):
		self.DeleteInactiveBots()
		if len(event.arguments) >= 2:
			btype = event.arguments[0]
			arena = event.arguments[1]
			args = event.arguments_after[2] if len(event.arguments) > 2 else ""
			r =  self.StartBot(ssbot, event.pname, btype, arena, args);
			if r == 1:
				ssbot.sendReply(event,"ok")
			elif r == -1:
				ssbot.sendReply(event,"Error:type(%s) not found"%(type))
			elif r == -2:
				ssbot.sendReply(event, "all %s in use"%(type))
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
		elif event.type == EVENT_LOGIN:
			self.tm.set(10, (2,None))# for periodic deleting of inactive bots and removing of old list entries from log
			c = 60#wait for bot to login
			for b in self.config.AutoLoad:#stagger the bots to load by 180 sec each
				c+=180
				self.tm.set(c, (1,b))
				self.logger.info("Queued:[Sb] %s -> %s" % b)
		elif event.type == EVENT_TICK:
			self.SendBroadcastsToAttachedBots(ssbot)
			#self.logger.info("tick")
			timer_expired = self.tm.getExpired() # a timer expired
			if timer_expired:
				#self.logger.info("timer expired")
				
				if timer_expired.data[0] == 1:#start a bot
					t = timer_expired.data[1]
					#ssbot.sendPublicMessage("!sb %s %s" % t)
					r =  self.StartBot(ssbot, ssbot.name, t[0], t[1], "");
					if r == 1:
						ssbot.sendPublicMessage("autospawn:successfull spawned %s to %s"%t)
					elif r == -1:
						ssbot.sendPublicMessage("autospawn:Error:type(%s) not found"%(t[0]))
					elif r == -2:
						ssbot.sendPublicMessage("autospawn:all %s in use"%(t[0]))
				elif timer_expired.data[0] == 2:#do maintenance
					self.DeleteInactiveBots()
					self.listhandler.RemoveOld()
					self.tm.set(10, (2,None))
				elif timer_expired.data[0] == 3: #shutdown
					self.logger.info("calling disconnect")
					ssbot.disconnectFromServer()
					#ssbot.stopReactor()
	
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
		pass

def MasterMain():
	try:
		#other bots use logging i dont want it to spamm the main logger
		rootlogger = logging.getLogger('')
		rootlogger.addHandler(NullHandler())
		rootlogger.setLevel(logging.DEBUG)
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
	
		
		filehandler  = logging.FileHandler(os.path.join(os.getcwd(),"Bots.log"),mode='a')
		filehandler.setLevel(logging.ERROR)
		filehandler.setFormatter(formatter)
		logger.addHandler(filehandler)
	
		#command Line Options
		parser = OptionParser()
		
		parser.add_option("-c", "--ConfigFile", dest="ConfigFile",
					  help="Load Configuration from a non default file",
					  default=os.path.join(os.getcwd(),"Bots.json"))
		
		
		parser.add_option("-p", "--Password", dest="Password",
					  help="pass sysop/smod pass by commandline instead of in config",
					  default=None)
		
		(options, args) = parser.parse_args()
	
		Queue = MasterQue()
		config = GlobalConfiguration(options.ConfigFile,options.Password)
		ssbot = SubspaceBot(config.Host,
								  config.Port, 
								  config.MasterName, 
								  config.MasterPassword,
								  config.MasterArena,
								  False,
								  BM_MASTER,
								  Queue,
								  logging.getLogger("ML.Master.Core"))
		ssbot.setBotInfo("Master","MasterBot Manages the starting/stopping of bots", None)
		BotList = [ ]
		#this adds dir's to pythonpath so we can run the dev code out of seperate dirs
		for p in config.paths:
			sys.path.append(p)
		#get the module object for the current file...	
		module = sys.modules[globals()['__name__']]
		#loads atleast the masterbot
		md = ModuleData("Master",module,"None",config.ConfigurationFile,"",logging.getLogger("ML.Master"))
		master = Bot(ssbot,md,config,Queue)
		master.setReactor(reactor)
		
		BotList.append(master)
		#load any bots that are specified in the config
		bot = None
		for m in config.Modules:
			bot = LoadBot(ssbot,m[0],m[1],config.ConfigurationFile,"",logging.getLogger("ML.Master."  + m[0]))
			if bot:
				BotList.append (bot)
			bot = None
			
		ssbot.setBotList(BotList)
		lp = reactor.listenUDP(0, ssbot)
		ssbot.setReactorData(reactor,lp) # so clients can disconnect themselves when they get disconnect packet or master kills them
		reactor.run()	   

		
	except (KeyboardInterrupt, SystemExit):
		logger.critical("CTRL-c or System.exit() detected")	
	except:
		logger.critical("Unhandled Exception")
		LogException(logger)
	finally:
# 		if 'master' in locals():
# 			master.StopAllBots()
		if reactor.running:
			reactor.stop()
		for b in BotList:
			b.Cleanup()
		logger.critical("Master Bot behaviors cleansed")
		filehandler.close()
		os._exit(1)
		
		
if __name__ == '__main__':
	profile = False
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

	
