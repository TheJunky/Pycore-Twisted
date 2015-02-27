

from Subspace import *


class SubspaceBot(DatagramProtocol):

	def __init__(self, host, port, username, password, arena, debug=False, botmode=BM_STANDALONE, MQueue=None, logger = None):
		"""Initialize the CoreStack class. If debug is set debugging messages will be displayed."""
		self.__debug = debug
		self.logger = logger
		
		
		self.__username = username
		self.__password = password
		self.__host = host
		self.__port = port
		self.arena = arena
		
		self.__state= None
		self.__crypto = None # initialized after servers key is received. once set, encryption is done
		self.__packet_queues = [[], []]	# list containing QueuedPacket objects
		self.__reliable_messages_in_transit = { } # ackid : [packet, last transmit tick]   a list is used because it needs to be assigned (updating tick count) while the dictionary has an open iterator
		self.__incoming_reliable_packets = [] # (ack_id, packet) reliable messages that were received out of order, packet does not include the reliable header

		
		self.__last_packet_received_tick = GetTickCountHs()
		
		# the list of incoming chunk data that gets concatenated and then handled
		self.__chunk_list = None
		self.__huge_chunk_data = None
		

		self.__core_about = "Python-SubspaceBot By cycad <cycad@zetasquad.com>"
		self.__core_version = "0.0001-Twisted"

		

		self.__botlist= None
		
		
		self.__players_by_pid = {} # pid : Player
		self.__players_by_name = {} # name: Player
		
		self.__event_list = []
		
		
		# generate a valid mid
		hash_string = os.name + sys.platform + socket.getfqdn()
		self.machine_id, self.permission_id = struct.unpack_from('II', hashlib.md5(hash_string).digest())
		self.machine_id = self.__makeValidMachineID(self.machine_id)
		
		self.players_here = []
		self.__players_by_name = {}
		self.__players_by_pid = {}
			
		self.__last_event_generated = None
		
		self.flag_list = [Flag(i) for i in range(MAX_FLAGS)]
		self.ball_list = [Ball(i) for i in range(MAX_BALLS)]
		
		
		self.pid = None
		self.name = None
		
		self.type =None
		self.description = None
		self.owner = None
		
		self.__connected = False
		
		#will be true unl;ess disconnectfrom server was called by bot/master
		self.__reconnect = True
		self.__last_recconect_attempt = None
		self.__total_reconnect_attempts = None
		
		
		#added by junky	
		self.__cmd_dict = {}
		self.__alias_dict = {}
		self.__category_dict = {}
		self.__module_info_list = []
		
		
		self.freq = None
		
		# the ships position data
		self.ship = None
		self.x_pos = 512 * 16
		self.y_pos = 512 * 16
		self.x_vel = 0
		self.y_vel = 0
		self.status = 0
		self.bounty = 0
		self.energy = 0
		self.rotation = 0
			
		self.__timer_list = [] # Timer()
		self.__next_timer_id = 0
		self.__last_timer_expire_tick = GetTickCountHs()
		
		self.__max_cmd_len = 10 #used for formatting will store the max(len("!name/!alias [args]"))
		
		self.__command_help_id = self.registerCommand('!help',None,0,COMMAND_LIST_PP,"Core","[<cat>|<!cmd>|*]","display available commands")
		self.__command_about_id = self.registerCommand('!about',None,0,COMMAND_LIST_PP,"Core","","display information about current bot")
		

		#for broadcasts it goes to master master distributes
		self.__mqueue = MQueue

		self.__botmode = botmode;	
		if(botmode in [BM_MASTER,BM_STANDALONE]):
			if botmode == BM_STANDALONE:
				self.__command_die_id = self.registerCommand('!stopbot',"!die",7,COMMAND_LIST_PR,"Core","","stop the master")
			else:
				self.__command_die_id = None #need to handle it in the master code
			self.__command_addop_id = self.registerCommand('!Addop',"!ao",4,COMMAND_LIST_ALL,"Core","[lvl:name]","add a player to the oplist")
			self.__command_delop_id = self.registerCommand('!Delop',"!do",4,COMMAND_LIST_ALL,"Core","[name]","delete a player from the oplist")
			self.__command_listops_id = self.registerCommand('!Listops',"!lo",4,COMMAND_LIST_PP,"Core","","list all the ops <= to your lvl")
			self.__command_reloadops_id = self.registerCommand('!Reloadops',"!ro",4,COMMAND_LIST_ALL,"Core","","reread oplist from file")
		elif botmode==BM_SLAVE:
			self.__command_die_id = self.registerCommand('!stopbot',"!die",2,COMMAND_LIST_ALL,"Core","","stop this bot")
			self.__command_addop_id = None
			self.__command_delop_id = None
			self.__command_listops_id = None
			self.__command_reloadops_id = None
		
		#: Event preprocessors can return a new event to pass on to the bot, or None if no event should be generated
		self.__event_preprocessors = {
			#EVENT_START : self.__eventStartPreprocessor,						
			EVENT_ENTER : self.__eventEnterPreprocessor,
			EVENT_LEAVE : self.__eventLeavePreprocessor,
			EVENT_TICK :  self.__eventTickPreprocessor,
			EVENT_CHANGE: self.__eventChangePreprocessor,
			EVENT_DISCONNECT : self.__eventDisconnectPreprocessor,
			EVENT_COMMAND : self.__eventCommandPreprocessor,
			EVENT_ARENA_LIST : self.__eventArenaListPreprocessor,
		}
			
		# event post processors
		self.__event_postprocessors = {

			EVENT_START : self.__eventStartPostprocessor,
			EVENT_CHANGE: self.__neutFlagsCarriedByPlayerProccessor,
			EVENT_LEAVE : self.__neutFlagsCarriedByPlayerProccessor,
			EVENT_FLAG_PICKUP : self.__eventFlagPickupPostprocessor,
			EVENT_FLAG_DROP : self.__eventFlagDropPostprocessor,
			EVENT_KILL : self.__eventKillPostprocessor,
			EVENT_DISCONNECT: self.__eventDisconnectPostprocessor
		}
		
		
		
		# the packet handler functions
		self.__core_packet_handlers = {
			0x03 : self.__handleReliableMessage,
			0x04 : self.__handleAckPacket,
			0x05 : self.__handleSyncRequestPacket,
			0x06 : self.__handleSyncResponsePacket,
			0x07 : self.__handleDisconnectPacket,
			0x08 : self.__handleChunk,
			0x09 : self.__handleChunkEnd,
			0x0A : self.__handleHugeChunk,
			#0x0D : self.__handleDisconnectPacket,	#xxx we could parse the reason out of this
			0x0E : self.__handleClusterPacket,
		}
		
		# setup the appropriate handlers
		self.__packet_handlers = {
			0x03 : self.__handlePlayerEnteredPacket,
			0x04 : self.__handlePlayerLeftPacket,
			0x05 : self.__handleLargePositionUpdatePacket,
			0x06 : self.__handleKillPacket,
			0x07 : self.__handleMessagePacket,
			0x08 : self.__handlePrizePacket,
			0x09 : self.__handleScoreUpdatePacket,
			0x0A : self.__handleLoginResponsePacket,
			0x0B : self.__handleGoalPacket,
			0x0D : self.__handleFreqchangePacket,
			0x0E : self.__handleTurretPacket,
			0x0F : self.__handleArenaSettingsPacket,
			0x10 : self.__handleFileTransfer,
			0x12 : self.__handleFlagUpdatePacket,
			0x13 : self.__handleFlagPickupPacket,
			0x14 : self.__handleFlagVictoryPacket,
			0x16 : self.__handleFlagDropPacket,
			0x19 : self.__handleRequestFile,
			0x1A : self.__handleScoreResetPacket,
			0x1C : self.__handleShipChangePacketSelf,
			0x1D : self.__handleShipchangePacket,
			0x1F : self.__handleBannerPacket,
			0x21 : self.__handleBrickDropPacket,
			0x22 : self.__handleTurfFlagUpdatePacket,
			0x23 : self.__handlePeriodicRewardPacket,			
			0x27 : self.__handlePositionUpdateRequest,
			0x28 : self.__handleSmallPositionUpdatePacket,
			0x29 : self.__handleMapInformationPacket,
			0x2A : self.__handleCompressedMapPacket,
			0x2C : self.__handleKothGameReset,
			0x2E : self.__handleBallPositionPacket,
			0x2F : self.__handleArenaListPacket,
			0x31 : self.__handleLoginPacket,
			0x32 : self.__handleWarptoPacket,
			0x38 : self.__handleWatchDamagePacket,

		}

		self.__login_response = {
			0x00 : "Login OK",
			0x01 : "Unregistered Player",
			0x02 : "Bad Password",
			0x03 : "Arena is Full",
			0x04 : "Locked Out of Zone",
			0x05 : "Permission Only Arena",
			0x06 : "Permission to Spectate Only",
			0x07 : "Too many points to Play here",
			0x08 : "Connection is too Slow",
			0x09 : "Permission Only Arena",
			0x0A : "Server is Full",
			0x0B : "Invalid Name",
			0x0C : "Offensive Name",
			0x0D : "No Active Biller",
			0x0E : "Server Busy, try Later",
			0x10 : "Restricted Zone",
			0x11 : "Demo Version Detected",
			0x12 : "Too many Demo users",
			0x13 : "Demo Versions not Allowed",
			0xFF : "Restricted Zone, Mod Access Required"
		}
		
		self.__chats = []
		self.__chats_changed = False
		
		self.__oplist = Oplist()
		
		self.__started_time = time.time()
		
		#should the core download maps or not?
		self.__downloadLevelFiles = False
		
		#getaccesslevel will return 0 if biller is down
		self.billing = True
		
		self.settings = None
		
		self.lc = task.LoopingCall(self.Tick)
		self.lc.start(0.01,False)
		
		
		self.__reactor= None
		self.__listeningport=None

	def createPeriodicCallBack(self,func,secs,now):#broken
		lc = task.LoopingCall(func)
		lc.start(secs,now)
		
	def setReactorData(self,reactor,listeningport):
		self.__reactor = reactor
		self.__listeningport = listeningport
		
	def loseConnection(self):
		if self.__botmode in [BM_STANDALONE,BM_MASTER]:
			self.stopReactor()
		else:
			self.__log(CRITICAL,self.name +" losing connection")
			self.transport.loseConnection()
			#self.transport.disconnect()
			#self.__listeningport.connectionLost()
			
	def stopReactor(self):
		self.__reactor.disconnectAll()
		self.__log(CRITICAL, "stopping reactor")
		self.__reactor.stop()
			
			
	def setBotList(self,botlist):
		self.__botlist= botlist
		
	def startProtocol(self):
		self.connectToServer()
		
	def datagramReceived(self, data, (host, port)):
		
		self.__last_packet_received_tick = GetTickCountHs()
		
		if self.__state == STATE_CONNECTED:
			self.__total_packets_received += 1
			# decrypt the packet
			if self.__crypto:
				type, = struct.unpack_from("<B", data)
				begin_offset = 1
				if type == 0x00:
					begin_offset = 2
				data = data[:begin_offset] + self.__crypto.decryptData(data[begin_offset:])
			self.__processIncomingPacket(data)
		else:
			try:
				game_type, core_type = struct.unpack_from("<BB", data)
				if game_type == 0x00:
					if core_type == 0x05:	# response to __sendClientKey()
						if self.__debug == True:
							self.__log(INFO,"sending response to server challenge")
						self.__server_challenge, = struct.unpack_from("<i", data, 2)
						self.__state = STATE_CHALLENGE_RECEIVED
						packet = struct.pack("<BBII", 0x00, 0x06, self.__server_challenge & 0xFFFFFFFF, GetTickCountHs())
						self.__sendRawPacket(packet)
					elif core_type == 0x02:
						# success
						self.__server_key, = struct.unpack_from("<i", data, 2)
						self.__crypto = SubspaceEncryption.SubspaceEncryption(self.__client_key, self.__server_key)
						self.__state = STATE_CONNECTED
						if self.__debug == True:
							self.__log(INFO,"We got crypto, state connected")
						self.__queueLoginPacket(self.__username, self.__password)
						self.flushOutboundQueues()
						self.__connected = True
						self.__last_pos_update_sent_tick = GetTickCountHs()	
					
			except struct.error:
				pass
				
			# write sent packets to the network
			self.flushOutboundQueues()	
		
	def Tick(self):
		if self.__connected:
			self.__addPendingEvent(GameEvent(EVENT_TICK))
			self.__corePeriodicEvent()
			self.flushOutboundQueues()
			self.ProcessEventQueue()
	

	
	# Possibly invoked if there is no server listening on the
	# address to which we are sending.
	def connectionRefused(self):
		self.__log(CRITICAL,"Unable to connect to server")
		self.__connected = False
		self.loseConnection()
	
	
		
	def __log(self,level,message):
		if self.logger:
			self.logger.log(level,message)
		else:
			print (message)
	
		

			
		
	def connectToServer(self):
		"""Connect to the server, otherwise raise an exception."""

		self.__total_packets_sent = 0
		self.__total_packets_received = 0
		self.__next_outgoing_ack_id = 0
		self.__next_incoming_ack_id = 0
		self.__last_sync_response_received_tick = GetTickCountHs()
		


		self.transport.connect(self.__host, self.__port)
			

		
		self.__client_key = (-random.randrange(1, sys.maxint))
		self.__server_challenge = 0
		
		
		self.fc = FileChecksum()
		self.fc.generateChecksumArray(0)
		
		self.__state = STATE_NONE
		self.__sendRawPacket(struct.pack("<BBIH", 0x00, 0x01, self.__client_key & 0xFFFFFFFF, 0x0001))
		
		self._queueSyncRequest()
		self.flushOutboundQueues()
	
		
	def queuePacket(self, data, reliable=False, priority=PRIORITY_NORMAL):
		"""Queue a packet to be sent."""
		size = len(data)
		psize = size + (6 if reliable else 0)
		if psize < MAX_PACKET:
			self.__packet_queues[priority].append(QueuedPacket(data, reliable))
		else:
			if size < (MAX_PACKET*100):
				print "small chunk total size:" + str(size)
				#print "chunk total size:" + str(len(data))
				MAX_CHUNK = MAX_PACKET - 8# 6 for reliable header + 2 for packet header
				while(len(data)> 0):
					chunk_size = min(MAX_CHUNK,len(data))
					remaining = len(data)- chunk_size
					if remaining >0:
						packet = struct.pack("<BB",0x00,0x08)
						#print "Headpacket_size: %d Remaining Data:%d" % (chunk_size, remaining)  
					else:
						packet = struct.pack("<BB",0x00,0x09) 
						#print "Tailpacket_size: %d Remaining Data:%d" % (chunk_size, remaining) 
					packet += data[0:chunk_size-1]
					data = data[chunk_size:]
					self.__packet_queues[priority].append(QueuedPacket(packet, True))	
			else:
				#dont think this works when i putfile it seems to fail if it gets so big as to use huge chunk
					offset =0 
					print "huge chunk total size:" + str(size)
					MAX_CHUNK = MAX_PACKET - 12# 6 for reliable header + 6 for packet header
					
					while(len(data)> 0):
						chunk_size = min(MAX_CHUNK,len(data))
						packet = struct.pack("<BBI",0x00,0x0a,size) 
						packet += data[0:chunk_size-1]
						data = data[chunk_size:]
						print "packet_size: %d Remaining Data:%d" % (chunk_size, len(data))
						self.__packet_queues[priority].append(QueuedPacket(packet, True)) 
	
	def __generateNextOutboundPacket(self):
		"""Extract packets from queues and return a buffer containing the next outbound packet
		that is to be sent on the network, if a packet can be built.
		"""
		h = self.__packet_queues[PRIORITY_HIGH]
		n = self.__packet_queues[PRIORITY_NORMAL]
		
		if len(h) == 0 and len(n) == 0:
			return None
				
		# determine which packets can be clustered, if any
		clusterable_packets = 0
		try:
			for packet_list in [h, n]:
				for outgoing_packet in packet_list:
					if outgoing_packet.totalPacketSize() > 255:
						raise StopIteration()
					clusterable_packets += 1
		except StopIteration:
			pass
		
		data = None
		if clusterable_packets > 1:
			data = struct.pack("<BB", 0x00, 0x0E)
			
			reliable_allowed = True
			for packet_list in [h, n]:
				i = 0
				for p in packet_list[:]:
					if p.totalPacketSize() <= 255 and len(data) + p.totalPacketSize() + 1 <= MAX_PACKET: #plus 1 is for the data length in cluster
						if p.reliable:
							#send reliable packet, can be disallowed due to ordering concerns
							if reliable_allowed:
								packet = struct.pack("<BBBI", p.totalPacketSize(), 0x00, 0x03, self.__next_outgoing_ack_id & 0xFFFFFFFF) + p.data
								
								# store off packet[1:] here so when its retransmitted, it doesnt re-append the 'size' field
								# since only the data should be resent
								self.__reliable_messages_in_transit[self.__next_outgoing_ack_id] = [packet[1:], GetTickCountHs()]
								self.__next_outgoing_ack_id += 1
								data += packet
								
								packet_list[i] = None
						else:
							# send an unreliable packet
							data += struct.pack('<B', p.totalPacketSize()) + p.data
							packet_list[i] = None
					elif p.reliable:
						# this packet wont fit and it is reliable, so dont allow following
						# reliable packets to be sent, because these need to be sent in order
						reliable_allowed = False
					i += 1
			
			# remove None entries
			# opt: should these be   self.__packet_queues[PRIORITY_Xxx][:] = ...   ?
			self.__packet_queues[PRIORITY_HIGH] = [x for x in h if x is not None]
			self.__packet_queues[PRIORITY_NORMAL] = [x for x in n if x is not None]
			
		else:
			# a single, non-cluster packet is being sent
			if len(h): p = h.pop(0)
			else: p = n.pop(0)
				
			data = p.data
			
			if p.reliable:
				# send packet with the reliable header prepended
				data = struct.pack("<BBI", 0x00, 0x03, self.__next_outgoing_ack_id & 0xFFFFFFFF) + data
				self.__reliable_messages_in_transit[self.__next_outgoing_ack_id] = [data, GetTickCountHs()]
				self.__next_outgoing_ack_id += 1
		
		return data
	
	def flushOutboundQueues(self):
		"""Flush outbound packet queues."""
		while 1:
			if len(self.__packet_queues[PRIORITY_HIGH]) == 0 and len(self.__packet_queues[PRIORITY_NORMAL]) == 0:
				break
			# check to make sure outbound socket is writable
			packet = self.__generateNextOutboundPacket()
			if packet:
				self.__sendRawPacket(packet)
				
				
	def __queueAckPacket(self, ack_id):
		"""Queue an ack packet."""
		self.queuePacket(struct.pack("<BBI", 0x00, 0x04, ack_id & 0xFFFFFFFF))
	
	def __queueDisconnectPacket(self):
		"""Queue a disconnect packet."""
		self.queuePacket(struct.pack("<BB", 0x00, 0x07))
	
	def disconnectFromServer(self):
		"""Disconnect from the server."""
		self.__reconnect = False
		self.__queueDisconnectPacket()
		self.__addPendingEvent(GameEvent(EVENT_DISCONNECT))
		self.flushOutboundQueues()
		self.__log(CRITICAL,"disconnected")
		self.loseConnection()
	
	def shouldReconnect(self):
		return self.__reconnect
		
	def __handleReliableMessage(self, packet):
		"""Handle an incoming reliable message."""
		# this could be cleaner by adding to the incoming list, then processing lists
		zero, core_type, ack_id = struct.unpack_from("<BBI", packet)
		
		self.__queueAckPacket(ack_id)
		
		if ack_id == self.__next_incoming_ack_id:
			self.__next_incoming_ack_id += 1
			self.__processIncomingPacket(packet[6:])
			#self.__log(DEBUG,"ackid = next incoming ackid processing reliabhle message:expected: "+str(self.__next_incoming_ack_id)+" recieved:"+str(ack_id))
			
			loop_again = True
			while loop_again:
				loop_again = False
				index = 0
				for ack_packet_tuple in self.__incoming_reliable_packets:
					if ack_packet_tuple[0] == self.__next_incoming_ack_id:
						self.__incoming_reliable_packets.pop(index)
						self.__next_incoming_ack_id += 1
						self.__processIncomingPacket(ack_packet_tuple[1])
						#self.__log(DEBUG,"ackid = in incoming ack list processing reliabhle message:expected: "+str(self.__next_incoming_ack_id)+" recieved:"+str(ack_id))
						loop_again = True
						break
					index += 1
			
		elif ack_id > self.__next_incoming_ack_id:
			self.__incoming_reliable_packets.append((ack_id, packet[6:]))
			#self.__log(DEBUG,"ackid = > received acks appending to list expected: "+str(self.__next_incoming_ack_id)+" recieved:"+str(ack_id))
	
	def __handleChunk(self, packet):
		if self.__chunk_list is None:
			self.__chunk_list = []
			#print "small chunk type: " + packet.encode('hex')
		self.__chunk_list.append(packet[2:])
	
	def __handleChunkEnd(self, packet):
		if self.__chunk_list:
			self.__chunk_list.append(packet[2:])
			self.__processIncomingPacket(''.join(self.__chunk_list))
			self.__chunk_list = None
	
	#added by junky
	def __handleHugeChunk(self,packet):
		type,type2, total_size = struct.unpack_from("<BBI",packet)
		if(self.__huge_chunk_data == None): #new chunk
			self.__huge_chunk_data = packet[6:]
			print "huge chunk type: " + self.__huge_chunk_data.encode('hex')
		else:
			self.__huge_chunk_data += packet[6:] 
			
		if( len(self.__huge_chunk_data) == total_size): #packet complete
			self.__processIncomingPacket(self.__huge_chunk_data[:])
			self.__huge_chunk_data = None



			
	def __corePeriodicEvent(self):
		"""This is called every 100ms"""
		# requeue reliable messages that havent been acked
		now = GetTickCountHs()
		for ack_id, packet_last_transmit_tick_list in self.__reliable_messages_in_transit.iteritems():
			if TickDiff(now, packet_last_transmit_tick_list[1]) > RELIABLE_RETRANSMIT_INTERVAL:
				self.queuePacket(packet_last_transmit_tick_list[0], False, PRIORITY_HIGH)
				packet_last_transmit_tick_list[1] = now
		
		if TickDiff(now, self.__last_packet_received_tick) >= NO_PACKET_RECEIVED_TIMEOUT_INTERVAL:
			self.__addPendingEvent(GameEvent(EVENT_DISCONNECT))
			self.logger.critical("packet not recieved in timeout interval,sending disconnect")
	
	def __handleClusterPacket(self, packet):
		packet = packet[2:]
		while len(packet):
			data_len, = struct.unpack_from("<B", packet)
			self.__processIncomingPacket(packet[1:data_len + 1])
			packet = packet[data_len + 1:]
	
	def __handleDisconnectPacket(self, packet):
		self.__addPendingEvent(GameEvent(EVENT_DISCONNECT))
	
	def __handleSyncRequestPacket(self, packet):
		self.__queueSyncResponse()
	
	def __handleSyncResponsePacket(self, packet):
		self.__last_sync_response_received_tick = GetTickCountHs()
		
	def __handleAckPacket(self, packet):
		zero, type, ack_id = struct.unpack_from("<BBI", packet)
		self.__reliable_messages_in_transit.pop(ack_id, None)
	
	
		
	def __processIncomingPacket(self, packet):
		# process the incoming packet, etc
		try:
			type, = struct.unpack_from("<B", packet)
			if type == 0x00:
				# core packet handlers
				type, = struct.unpack_from("<B", packet, 1)
				if (self.__debug and type !=0x03):
					self.__log(DEBUG, "Handling Core Type: 0x%02X" % type)
					
				handler = self.__core_packet_handlers.get(type, None)
				if handler:
					handler(packet)
				else:
					self.__log(INFO,"wtf corestack type %i not handled"%(type,))
			else:
				if self.__debug and type != 0x03:
					self.__log(DEBUG, "Handling Game Type: 0x%02X" % type)

				game_type, = struct.unpack_from("<B", packet)
				handler = self.__packet_handlers.get(game_type, None)
				if handler:
					handler(packet)
					if (self.__debug and game_type != 0x03):	
						self.__log(DEBUG, "Handler for Type: 0x%02X is %s" % (game_type,handler))
				else:
					if self.__debug == True:
						self.__log(DEBUG, "Handler for Type: 0x%02X is %s" % (game_type,"No Handler"))	
						self.__log(DEBUG, "Packet data: " + packet.encode('hex'))	
						
				if self.__last_event_generated is not None:
					postprocessor = self.__event_postprocessors.get(self.__last_event_generated.type, None)
					if postprocessor:
						postprocessor(self.__last_event_generated)
					self.__last_event_generated = None
					
				if self.__connected is False:
					return None
		except (IndexError, struct.error):
			if game_type:
				self.__log(CRITICAL, 'Structure error in SubspaceBot packet handler: %02X' % game_type)
			else:
				self.__log(CRITICAL, "Error in Core packet processing")
			self.__log(CRITICAL, "Packet data: " + packet.encode('hex'))
			formatted_lines = traceback.format_exc().splitlines()
			for l in formatted_lines:
				self.__log(DEBUG,l)			

	
	def _queueSyncRequest(self):
		self.queuePacket(struct.pack("<BBIII", 0x00, 0x05, GetTickCountHs(), self.__total_packets_sent & 0xFFFFFFFF, self.__total_packets_received & 0xFFFFFFFF), priority=PRIORITY_HIGH)
	
	def __queueSyncResponse(self):
		self.queuePacket(struct.pack("<BBII", 0x00, 0x06, GetTickCountHs(), TickDiff(GetTickCountHs(), self.__last_sync_response_received_tick)), priority=PRIORITY_HIGH)
	
	#def __handleSyncResponsePacket(self, packet):
	#	# packet contents are irrelevant
	#	self.__last_sync_response_received_tick = GetTickCountHs()
	
	def __queueAckMessage(self, ack_id):
		self.queuePacket(struct.pack("<BBI", 0x00, 0x03, ack_id & 0xFFFFFFFF), priority=PRIORITY_HIGH)
	
	def __sendRawPacket(self, packet):
		if self.__debug == True:
			self.__log(DEBUG, "Sent:" + packet.encode('hex'))
			
		if self.__crypto:
			begin_offset = 1
			if ord(packet[0]) == 0x00:
				begin_offset = 2
			
			packet = packet[:begin_offset] + self.__crypto.encryptData(packet[begin_offset:])
			
		self.transport.write(packet)
		self.__total_packets_sent += 1

	def setDownloadLevelFiles(self,doit):	
		"""
			must set this to true if you want the core to download map files
		"""
		self.__downloadLevelFiles = doit
	
	def __log(self,level,message):
		if self.logger:
			self.logger.log(level,message)
		else:
			print (message)
	
	def getAccessLevel(self,name):
		return self.__oplist.GetAccessLevel(name)
	
	def findPlayerByPid(self, pid):
		"""Find a player by PID.
		
		If a player is not found, None is returned."""
		return self.__players_by_pid.get(pid, None)
	
	def findPlayerByName(self, name):
		"""Find a player by name.
		
		If a player with the exact name is not found, None is returned.""" 
		return self.__players_by_name.get(name.lower(), None)

	def registerCommand(self,name,alias,access_lvl,msg_types_list,category,args,short_help,long_help=None):
		"""Register a command with the core.
		
		name is the name of the command, including the '!'.  description is a short
		one-line explanation of what the command does, displayed in !help.
		
		alias is a shortverion of the command like !sb for !startbot
		
		access_level is the min accesslevel you need to use this command
		
		msg_types_list is a list of message types this command supports
		for example [MESSAGE_TYPE_PRIVATE,MESSAGETYPE_PUBLIC,MSG_TYPE_CHAT]
		
		args will be displayed in help to tell users what arguments a command supports
		
		short_help will be displayed in !help category if the command is in a category
		
		long help only when u do !help !cmd
		
		Returns a unique identifier for the command, to be used in EVENT_COMMAND
		to identify the command being used."""
		kc = category.lower()
		k = name.lower()
		id = -1
		
		
		if args is None:
			args = ""
		if category is None:
			category = "None"
		if alias is None:
			alias = ""
		
		if k in self.__cmd_dict:
			self.__log(INFO,"Attempt to register already existing command:", name)
		else:
			id = len(self.__cmd_dict)
			nc = Command(id,name,alias,access_lvl,msg_types_list,category,args,short_help,long_help)
			self.__cmd_dict[k] = nc
			
			self.__max_cmd_len = max(len(nc.name)+len(nc.alias)+len(nc.args)+4,self.__max_cmd_len) 
			
			if alias != None and alias != "":
				ka = alias.lower()
				if ka in self.__alias_dict:
					self.__log(INFO,"Attempt to register already existing alias:", ka)
				else:
					self.__alias_dict[ka] = nc
				
			if kc in self.__category_dict:
				self.__category_dict[kc].append(nc)
			else:
				self.__category_dict[kc] = [nc]
			
		return id
	
	def __getCmd(self,name):
		name = name.lower()
		if name in self.__cmd_dict:
			return self.__cmd_dict[name]
		elif name in self.__alias_dict:
			return self.__alias_dict[name]
		else:
			return None
	
	def setBotInfo(self,type,description,owner):
		self.type =type
		self.description = description
		self.owner = owner
		
	def registerModuleInfo(self,filename,name,author,description,version):
		self.__module_info_list.append(ModuleInfo(filename,name,author,description,version))

	def __expireTimers(self):
		"""Expires timers that are in the core's timer list."""
		now = GetTickCountHs()
		self.__timer_list.sort(lambda a, b: int((a.duration - TickDiff(now, a.base)) - (b.duration - TickDiff(now, b.base))))
		
		while self.__timer_list:
			t = self.__timer_list[0]
			if TickDiff(now, t.base) >= t.duration:
				event = GameEvent(EVENT_TIMER)
				event.id = t.id
				event.user_data = t.user_data
				self.__addPendingEvent(event)
				self.__timer_list.pop(0)
			else:
				# since the timer list is sorted the timers after are greater and dont need to be tested
				break

	def setTimer(self, seconds, user_data=None):
		"""Sets a timer that will generate an EVENT_TIMER event in seconds seconds.
		
		user_data is passed back as event.user_data during EVENT_TIMER.
		
		Returns a unique timer id that is passed back in EVENT_TIMER's event.id
		when the timer expires."""
		id = self.__next_timer_id
		self.__next_timer_id += 1
		self.__timer_list.append(Timer(id, seconds, user_data))
		return id
	
	def deleteTimer(self,id):
		self.__timer_list = [t for t in self.__timer_list if t.id != id]

	#def deleteAllTimers(self):
	#	self.__timer_list = []
		
	def __makeValidMachineID(self, machine_id):
		"""Generates a valid machine ID."""
		# the mid has to be in a specific format
		mid = array.array('B', struct.pack('<I', machine_id))
		mid[0] = mid[0] % 73
		mid[1] = mid[1] % 129
		mid[3] = (mid[3] % 24) + 7
		return struct.unpack_from('<I', mid.tostring())[0]
	
		
	def __queueLoginPacket(self, username, password):
		self.queuePacket(struct.pack("<BB32s32sIBhHhIIIIII", 0x09, 0, username, password, self.machine_id, 0, 0, 0x6f9d, 0x86, 444, 555, self.permission_id, 0, 0, 0))
		self.name = username
		
	def __queueArenaLoginPacket(self, arena, ship_type=SHIP_SPECTATOR):
		join_type = 0xFFFD
		if arena.isdigit():
			join_type = int(arena)
		self.queuePacket(struct.pack("<BBHHHH16s", 0x01, ship_type, 0, 4096, 4096, join_type, arena))
	
	def sendArenaMessage(self, message, sound=SOUND_NONE):
		"""Send a message to the arena with an optional sound.
		
		message can be a list of messages to send."""
		self._queueMessagePacket(MESSAGE_TYPE_PUBLIC,
								 ["*arena "+ m for m in message] if isinstance(message, list) else "*arena" + message
								 , sound=sound)
		
	def sendPublicMessage(self, message, sound=SOUND_NONE):
		"""Send a public message with an optional sound.
		
		message can be a list of messages to send.
		
		Public messages are sent to the server reliably but may not be relayed
		from the server to all players reliably."""
		self._queueMessagePacket(MESSAGE_TYPE_PUBLIC, message, sound=sound)
		
	def sendFreqMessage(self, freq, message, sound=SOUND_NONE):
		"""Send a freq message.
		
		message can be a list of messages to send."""
		for p in self.players_here:
			if p.freq == freq:
				self._queueMessagePacket(MESSAGE_TYPE_FREQ, message, target_pid=p.pid)
				break
		
	def sendPrivateMessage(self, player, message, sound=SOUND_NONE):
		"""Send a private message to player.
		player can be a Player object or the player's name
		message can be a list of messages to send.
		Only pass players to this function if your doing alot of spamming qat once to 
		ensure private Message is used instead of remote.
		if you pass a name the message will most liky be remote message"""
		
		if isinstance(player, Player):
			pp = player
		else:
			pn= player
			pp = self.findPlayerByName(pn)
			
		if pp:
			self._queueMessagePacket(MESSAGE_TYPE_PRIVATE, message, target_pid=pp.pid, sound=sound)
		else:
			self._queueMessagePacket(MESSAGE_TYPE_REMOTE, 
									[':' + pn + ':' + m for m in message] if isinstance(message, list) else ':' + pn + ':' + message,
									 sound=sound)	
	def sendRemoteMessage(self, player_name, message, sound=SOUND_NONE):
		"""Send a Remote message to player.
		message can be a list of messages to send.
		if there is a player with the name in the arena it will priv instead of remote"""
		
		pn= player_name
		pp = self.findPlayerByName(pn)
			
		if pp:
			self._queueMessagePacket(MESSAGE_TYPE_PRIVATE, message, target_pid=pp.pid, sound=sound)
		else:
			self._queueMessagePacket(MESSAGE_TYPE_REMOTE, 
									[':' + pn + ':' + m for m in message] if isinstance(message, list) else ':' + pn + ':' + message,
									 sound=sound)
		
	def sendReply(self,event,message, sound=SOUND_NONE):
		"""
		Convenience function, will only work in EVENT COMMAND
		you can use this function with out worrying how the command was used
		it will reply with priv/remote for most command types and on 
		the chat it was contacted with if its a chat message
		"""
		if event.command_type in [MESSAGE_TYPE_PUBLIC,
							MESSAGE_TYPE_PRIVATE,
							MESSAGE_TYPE_TEAM,
							MESSAGE_TYPE_FREQ,
							MESSAGE_TYPE_ALERT]:
			self.sendPrivateMessage(event.player,message)
		elif event.command_type == MESSAGE_TYPE_REMOTE:	
			self.sendPrivateMessage(event.pname,message)
		elif event.command_type == MESSAGE_TYPE_CHAT:
			#if event.chat_no  in [8,10]:
			#	self.sendChatMessage(";;"+str(event.chat_no)+";"+message)
			#else:
			#	self.sendChatMessage(";"+str(event.chat_no)+";"+message)
			self.sendChatMessage(";"+str(event.chat_no)+";"+message)
	
	def sendTeamMessage(self, message,sound=SOUND_NONE):
		"""Send a team message."""
		self._queueMessagePacket(MESSAGE_TYPE_TEAM, message, sound=sound)
			
	def sendChatMessage(self, message,sound=SOUND_NONE):
			self._queueMessagePacket(MESSAGE_TYPE_CHAT, message, sound=sound)

	def addChat(self,chat):
		"""
		multiple modules may be adding chats to a bot, this is an ez way for modules to know
		which chat is relevant to them
		input: chat can be a single chat or a list of chats, or a string that contains a list of chats
		output: a list of of numbers, 1 for each chat you passed in
		Note: if you only added one chat then the list will contain only one int
		if there are more than 10 chats this function will return -1 for all chats it couldnt add
		"""
		rc = []
		existing_chat = -1
		if type(chat) == types.ListType:
			lc = chat
		else:
			lc = chat.split(",")
			
		for c in lc:
			c = c.lower().strip()
			existing_chat = self.getChatno(c)
			if existing_chat != -1:
				rc.append(existing_chat)
			else:
				if len(self.__chats) >= 10:
					rc.append(-1)
				else:
					self.__chats.append(c)
					rc.append(len(self.__chats))
					self.__chats_changed = True
		return rc	

	def getChatno(self,chat_):
		"""
		get the channel number for any given chat if it is in the list
		else it will return -1 
		"""
		i = 0
		chat = chat_.lower()
		for c in self.__chats:
			i+=1
			if c == chat:
				return i
		return -1


	
#	def sendMessage(self, message_type, message, target=NONE, sound=SOUND_NONE):
#		if message_type == MESSAGE_TYPE_PUBLIC
#			self.sendPrivateMessage(event.player,message)
#		elif message_type == MESSAGE_TYPE_PRIVATE:
#		elif message_type == MESSAGE_TYPE_FREQ:
#			if type(target) != int
#		elif message_type == MESSAGE_TYPE_TEAM:		
#		elif message_type == MESSAGE_TYPE_REMOTE:	
#			self.sendPrivateMessage(event.pname,message)
#		elif message_type == MESSAGE_TYPE_CHAT:
#			self.sendChatMessage(message)
		
	def _queueMessagePacket(self, message_type, message, target_pid=PID_NONE, sound=SOUND_NONE):
		# this isnt exposed because its a bit too complicated, the simpler calls are exposed that
		# deal with basic message types and are easier to use. lets make this private
		if isinstance(message, list):
			for m in message:
				self.queuePacket(struct.pack("<BBBH", 0x06, message_type, sound, target_pid) + m[:247] + '\x00', reliable=True)
		else:
			self.queuePacket(struct.pack("<BBBH", 0x06, message_type, sound, target_pid) + message[:247] + '\x00', reliable=True)
		
	def sendModuleEvent(self,source,name,data):
		"""
		this function is so modules can share information with each other
		for example info bot will parse info
		and trigger this event
		if another module wanst to use the parsed info it knows the event_data is info
		and can use it accordingly
		if data is likly to change the data should be deep coped b4 being used
		if you are going to store the data deep copy it
		"""
		event = GameEvent(EVENT_MODULE)
		event.event_source = source
		event.event_name = name
		event.event_data = data
		self.__addPendingEvent(event)
			
	def sendBroadcast(self,message):#used by bots/modules
		"""
		a way for bots to send text messages to all other bots connected to the master
		"""
		event = GameEvent(EVENT_BROADCAST)
		event.bsource = self.name
		event.bmessage = message
		if self.__mqueue: #if is being used as a module in master
			self.__mqueue.queue(event)# send to master for distribution
		else:
			self.__addPendingEvent(event) #else queue back to the core
	
	def queueBroadcast(self,event):#used by master to queue back the broadcasts
		self.__addPendingEvent(event)
		
	def spectatePlayer(self,player):
		#sets the bot to spectate specified player.
		#IMPORTANT: does not change the bot's position. this only tells the server you wish to recieve position update packets from target player.
		#if you wish to follow the player around, must use SubspaceBot's setPosition() function for each recieved position update packet from target player.
		if not isinstance(player,Player):
			player = self.findPlayerByName(player)
		self.__queueSpecPlayerPacket(player)
		
	def unspectatePlayer(self):
		#unspectates player, if any is spectated.
		self.__queueSpecPlayerPacket(None)
	
	def __queueSpecPlayerPacket(self,player):
		if player and player.ship != SHIP_SPECTATOR:
			self.queuePacket(struct.pack("<BH", 0x08, player.pid), reliable=True)
		else:
			self.queuePacket(struct.pack("<BH", 0x08, 0xFFFF), reliable=True)
	
	def SetBotBanner(self,banner):
		"""Sets the bots banner to banner given as an argument. Banner is a 96 byte array."""
		self.__queueBannerPacket(banner)
	
	def __queueBannerPacket(self,banner):
		packet = struct.pack("<B", 0x19) + banner
		self.queuePacket(packet, reliable=True)
		
	def sendDeathPacket(self,pp):
		"""Tells the bot to queue a death packet to the server, with pid being the killer."""
		pid = self.__toPid(pp)
		self.__queueDeathPacket(pid)
		
	def __queueDeathPacket(self,pid):
		packet = struct.pack("<BHH", 0x05, pid, self.bounty)
		self.queuePacket(packet, reliable=True)
				
	def __handleLoginPacket(self, packet):
		self.__queueArenaLoginPacket(self.arena)
		self.flushOutboundQueues()
		self.__addPendingEvent(GameEvent(EVENT_START))
	
	def __eventStartPostprocessor(self, event):
		if len(self.__chats) > 0:
			cstr = "?chat="
			for c in self.__chats:
				cstr += c +","
			self.sendPublicMessage(cstr)
			self.__chats_changed = False
		self.sendPublicMessage("?arena")
		return event
					
	def __handlePlayerEnteredPacket(self, packet):
		# this should really create a player here dictionary (pid -> player object)
		while len(packet) >= 64:
			type, ship, audio, name, squad, fp, kp, pid, freq, w, l, turreted, flags_carried, koth = struct.unpack_from("<BBB20s20sIIHHHHHHB", packet)
			name = name.split(chr(0))[0]
			squad = squad.split(chr(0))[0]
			player = Player(name, squad, pid, ship, freq)
			player.kill_points = kp
			player.flag_points = fp
			player.wins = w
			player.losses = l
			player.flag_count = flags_carried
			player.turreted_pid = turreted
			#t = self.findPlayerByPid(turreted)
			#self.sendPublicMessage("Entered %s turreting %s:%x"%(name,t.name if t else "None",turreted ))
			#if t:
			#	t.turreter_list.append(turreted)
			#else
			#	self.__log(INFO,"EventEnter:Turreted pid not found:%x"%(turreted))
			event = GameEvent(EVENT_ENTER)
			event.player = player
			self.__addPendingEvent(event)	
			packet = packet[64:]
				
	def __handleGoalPacket(self, packet):
		type, freq, points = struct.unpack_from("<BHI", packet)
		event = GameEvent(EVENT_GOAL)
		event.freq = freq
		event.points = points
		self.__addPendingEvent(event)
			
	def __handleBallPositionPacket(self, packet):
		type, ball_id, x_pos, y_pos, x_vel, y_vel, pid, time = struct.unpack_from("<BBHHhhHI", packet)
		event = GameEvent(EVENT_BALL)
		event.ball_id = ball_id
		event.x_pos = x_pos
		event.y_pos = y_pos
		event.x_vel = x_vel
		event.y_vel = y_vel
		event.player = self.findPlayerByPid(pid)
		event.time = time
		#move to post processor
		b = self.ball_list[ball_id]
		b.x= x_pos
		b.y= y_pos
		b.pid=pid
		b.time = time
		self.__addPendingEvent(event)

	def __handleFlagUpdatePacket(self, packet):#0x12
		type, flag_id, x, y, freq = struct.unpack_from("<BHHHH", packet)
		event = GameEvent(EVENT_FLAG_UPDATE)
		event.freq = freq
		event.flag_id = flag_id
		event.x = x
		event.y = y
		#move to postprocessor
		f =self.flag_list[flag_id]
		f.freq = freq
		f.x = x
		f.y = y
		self.__addPendingEvent(event)
		
	def __handleFlagVictoryPacket(self, packet):#0x14
		type, freq, points = struct.unpack_from("<BHL", packet)
		event = GameEvent(EVENT_FLAG_VICTORY)
		event.freq = freq
		event.points = points
		for f in self.flag_list:
			f.freq = FREQ_NONE
			f.x = COORD_NONE
			f.y = COORD_NONE
		#addpostprocessor and reset flag state
		self.__addPendingEvent(event)

	def __handleScoreUpdatePacket(self, packet):
		type, pid, flag_points, kill_points, wins,losses = struct.unpack_from("<BHLLHH", packet)
		player = self.findPlayerByPid(pid)
		if player:
			event = GameEvent(EVENT_SCORE_UPDATE)
			#event.pid = pid
			event.old_flag_points = player.flag_points
			event.old_kill_points = player.kill_points
			event.old_wins = player.wins
			event.old_losses = player.losses
			
			player.flag_points = flag_points
			player.kill_points = kill_points
			player.wins = wins
			player.losses = losses
			event.player = player
			self.__addPendingEvent(event)
				
	def __handlePrizePacket(self, packet):
		type, time_stamp, x, y, prize, pid = struct.unpack_from("<BLHHHH", packet)
		player = self.findPlayerByPid(pid)
		if player:
			event = GameEvent(EVENT_PRIZE)
			event.time_stamp = time_stamp
			event.x = x
			event.y = y
			event.prize = prize
			event.player = player
			player.x =x
			player.y = y
			self.__addPendingEvent(event)
			
	def __handleFlagPickupPacket(self, packet):
		type, flag_id, pid = struct.unpack_from("<BHH", packet)
		player = self.findPlayerByPid(pid)
		if player:
			flag = self.flag_list[flag_id]
			event = GameEvent(EVENT_FLAG_PICKUP)
			event.player = player
			event.flag_id = flag_id
			event.flag = flag
			event.old_freq= flag.freq
			event.new_freq= player.freq
			event.x = flag.x
			event.y = flag.y 
			#self.sendPublicMessage("fp/ft %d:%x->%x"%(flag_id,flag.carried_by_pid,pid))
			self.__addPendingEvent(event)

			
	def __eventFlagPickupPostprocessor(self,event):
		event.flag.x = COORD_NONE
		event.flag.y = COORD_NONE
		event.player.flag_count+=1
		event.flag.freq = event.player.freq		
		
	def __handleFlagDropPacket(self, packet):
		type, pid = struct.unpack_from("<BH", packet)
		player = self.findPlayerByPid(pid)
		if player:
			event = GameEvent(EVENT_FLAG_DROP)
			event.player = player
			#move to post processor
			event.flag_count = player.flag_count
			self.__addPendingEvent(event)
			
	def __eventFlagDropPostprocessor(self,event):
		player = event.player
		player.flag_count = 0
		
	def __handleScoreResetPacket(self, packet):
		type, pid = struct.unpack_from("<BH", packet)
		#player = self.findPlayerByPid(pid)
		event = GameEvent(EVENT_SCORE_RESET)
		event.player = None
		event.pid = pid
		#move to post ptocessor
		if pid == 0xFFFF:
			for p in self.players_here:
				p.kill_points = 0
				p.flag_points = 0
				p.wins=0
				p.losses=0
		else:
			p = self.findPlayerByPid(pid)
			if p:
				p.kill_points = 0
				p.flag_points = 0
				p.wins=0
				p.losses=0	
				event.player = p	
		self.__addPendingEvent(event)
						
	def __handleTurretPacket(self, packet):
		type, turreter_pid, turreted_pid = struct.unpack_from("<BHH", packet)
		turreter = self.findPlayerByPid(turreter_pid)
		turreted = self.findPlayerByPid(turreted_pid)
		
		event = GameEvent(EVENT_TURRET)
		event.turreter = turreter
		event.turreted = turreted
		if turreter:
			if turreter.turreted_pid == 0xFFFF:
				event.old_turreted = None
			else:
				event.old_turreted = self.findPlayerByPid(turreter.turreted_pid)
			turreter.turreted_pid = turreted_pid
			self.__addPendingEvent(event)
	
	def __handleArenaSettingsPacket(self, packet):
		self.settings = arenaSettings(packet);
		
				
	def __handlePeriodicRewardPacket(self, packet):
		packet = packet[1:]
		point_list = []
		if len(packet) >= 4:
			while len(packet) >= 4:
				freq, points = struct.unpack_from("<HH", packet)
				point_list.append((freq, points))
				packet = packet[4:]
				#todo: add points to all the player structs post event

			event = GameEvent(EVENT_PERIODIC_REWARD)
			event.point_list = point_list
			self.__addPendingEvent(event)
				
	def __handleTurfFlagUpdatePacket(self,packet):
		packet = packet[1:]
		i = 0
		while len(packet) >= 2:
			self.flag_list[i].freq = struct.unpack_from("H",packet)
			packet = packet[2:]
			i+=1
		
	def __handleSpeedGameOver(self,packet):
		type,best,mr,msc,sc1,sc2,sc3,sc4,sc5,p1,p2,p3,p4,p5 = struct.unpack_from("BBHIIIIIIHHHHH",packet)
		event = GameEvent(EVENT_SPEED_GAME_OVER)
		event.best = best
		event.bot_rank = mr
		event.bot_score = msc
		event.winners = [
						(1,self.findPlayerByPid(p1),sc1),
						(2,self.findPlayerByPid(p2),sc2),
						(3,self.findPlayerByPid(p3),sc3),
						(4,self.findPlayerByPid(p4),sc4),
						(5,self.findPlayerByPid(p5),sc5),
						]
				
	def __handleBannerPacket(self, packet):
		#commented out stuff is if you wish to save the banner as an int array
		type, pid = struct.unpack_from("<BH", packet)
		#banner = []
		packet = packet[3:]
		player = self.findPlayerByPid(pid)
		if player:
			player.banner = packet
					
	#def __handleObjectMovePacket(self,packet):
	#	#uncomment for debugging, must add 0x36 : self.__handleObjectMovePacket, to dictionary before uncommenting 
	#	print (packet.encode('hex'))
	#	type, changeflags, rand, x, y, image, layer, timemode = struct.unpack_from("<BBHhhBBH", packet)
	#	#print ('change flags: ' + self.int2bin(changeflags, 8))
	#	print ('object id: ' + str((rand & 0xFFFE) >> 1))
	#	print ('map value: ' + str(rand & 0x0001))
	#	print ('x: ' + str(x))
	#	print ('y: ' + str(y))
	#	print ('image: ' + str(image))
	#	print ('layer: ' + str(layer))
	#	print ('timemode: ' + str(timemode))
		
	def __toPid(self,pp):
		if pp is None:
			pid = 0xFFF
		elif type(pp) == types.IntType:
			pid = pp
		elif type(pp) == types.StringType:
			p = self.findPlayerByName(pp)
			if p:
				pid = p.pid
			else:
				raise Exception("__toPid recieved a string, but player not found")
		elif isinstance(pp,Player):
			pid = pp.pid
		else:
			raise Exception("__topid recieved unknown type" + pp)
		return pid
			
	def sendMapObjectMove(self,pp,changeflags, x_pos, y_pos, objectidandtype, imageid, layer, timemode):
		#currently only moves a MAPOBJECT in an LVZ, please use the LVZObject class and run updates through it.
		pid = self.__toPid(pp)
		packet = struct.pack("<BHBBHhhBBH", 0x0A, pid, 0x36, changeflags, objectidandtype, x_pos, y_pos, imageid, layer, timemode)
		self.queuePacket(packet)
	
	def sendLvzObjectToggle(self,pp,list_of_tuples):
		""""
		pp can be PID_NONE to send to entire arena
		the list of tuples has to be  [(id,on/off),(id2,on,off),etc]
		For example: turn on obj 3333 and off 3334
		ssbot.sendLvzObjectToggle(player,[(3333,True),(3334,False)])
		"""
		packet = struct.pack("<BHB",0x0A, PID_NONE if pp == PID_NONE else self.__toPid(pp),0x35)
		for objtoggletuple in list_of_tuples:
			packet+= struct.pack("<H",(objtoggletuple[0] & 0x7FFF) if objtoggletuple[1] else (objtoggletuple[0] | 0x8000))
		self.queuePacket(packet)
		
	def __handlePlayerLeftPacket(self, packet):
		# this should really use a player here dictionary and add the player info to the event
		type, pid = struct.unpack_from("<BH", packet)
		player = self.findPlayerByPid(pid)
		if player:
			event = GameEvent(EVENT_LEAVE)
			event.player = player
			event.flags_neuted = player.flag_count
			player.flag_count = 0
			self.__addPendingEvent(event)
	
	def __handleLoginResponsePacket(self, packet):
		login_response, = struct.unpack_from("<B", packet, 1)
		self.__log(DEBUG,self.__login_response[login_response])
		if login_response == 0x01:
			self.__sendRegistrationForm()#doesnt work
			self.__log(INFO, "Sending Registration Form")
		elif login_response in [0x00, 0x05, 0x06]:
			pass
		elif login_response == 0x0D: #biller down
			self.billing = False
		elif login_response == 0x0E:
			self.__log(DEBUG,"Server Busy, try again later")
			self.__connected = False
		else:
			raise Exception("Login Error:%s" % self.__login_response[login_response])
	
	
	def __handleShipchangePacket(self, packet):
		type, ship, pid, freq = struct.unpack_from("<BBHH", packet)
		
		player = self.findPlayerByPid(pid)
		if player:
			event = GameEvent(EVENT_CHANGE)
			event.new_freq = freq
			event.new_ship = ship
			event.player = player

			if pid == self.pid:
				self.freq = freq
				self.ship = ship
			self.__addPendingEvent(event)
	
	def __handleFreqchangePacket(self, packet):
		type, pid, freq, unused = struct.unpack_from("<BHHB", packet)
		
		player = self.findPlayerByPid(pid)
		if player:
			event = GameEvent(EVENT_CHANGE)
			event.new_freq = freq
			event.new_ship = player.ship
			event.player = player

			if pid == self.pid:
				self.freq = freq
				self.ship = player.ship
			self.__addPendingEvent(event)
	
	def __neutFlagsCarriedByPlayerProccessor(self,event):
		"""
			set flags carried by event_player to neuted
		"""
		p = event.player
		p.flag_count = 0
					
	
	def __handleShipChangePacketSelf(self, packet):
		"""Handle a ship change packet for the bot itself."""
		type, ship = struct.unpack_from("<BB", packet)
		
		player = self.findPlayerByPid(self.pid)
		if player:
			event = GameEvent(EVENT_CHANGE)
			event.new_freq = player.freq
			event.new_ship = ship
			event.player = player
			event.flags_neuted = player.flag_count
			player.flag_count = 0

			self.__addPendingEvent(event)

	def __handleMessagePacket(self, packet):
		type, message_type, sound, pid = struct.unpack_from("<BBBH", packet)
		message = packet[5:].split(chr(0))[0]
		message_name = None
		chatnum = None
		alert = None
		arena = None
		player = None
		#added by junky	
		if message_type == MESSAGE_TYPE_REMOTE:
			i = message.find(": (")
			i2 = message.find(") (")
			i3 = message.find("): ")
			if(i != -1 and i2 != -1 and i3 != -1): #alert
				alert = message[0:i]
				message_name = message[i+3:i2]
				arena = message[i2+3:i3]
				message =message[i3+3:]
				message_type = MESSAGE_TYPE_ALERT
			else:
				i = message.find(")>")
				message_name = message[1:i]
				i+=2
				message = message[i:]
		elif message_type == MESSAGE_TYPE_CHAT:
			i = message.find(":")
			chatnum = int(message[0:i])
			i2 = message.find(">")
			message_name = message[i+1:i2]

			i2+=1
			message = message[i2+1:]
		elif message_type in [MESSAGE_TYPE_PUBLIC_MACRO,
							MESSAGE_TYPE_PUBLIC,
							MESSAGE_TYPE_TEAM,
							MESSAGE_TYPE_FREQ,
							MESSAGE_TYPE_PRIVATE,
							MESSAGE_TYPE_WARNING]:
			player = self.findPlayerByPid(pid)
			if player:
				message_name = player.name
			else:
				self.__log(DEBUG, "WTF:MESSAGE mtype%i pid 0x%x:%s"%(message_type,pid,message))
				message_name = ""

		
		
		# add the message event
		event = GameEvent(EVENT_MESSAGE)
		event.player = player
		event.message = message
		event.message_type = message_type
		event.pname = message_name
		event.chat_no = chatnum
		event.alert_name = alert
		event.alert_arena = arena

		self.__addPendingEvent(event)
		
		# add the command event
		if len(message) > 0 and message[0] == '!' and message_type in COMMAND_LIST_ALL: 
			command = message.split()[0]
			arguments = message.split()[1:]
			arguments_after = []
			
			for index in xrange(0, min(8, len(arguments))):
				arguments_after.append(' '.join(arguments[index:]))
				if index > 8: break
			
			event = GameEvent(EVENT_COMMAND)
			event.player = player
			event.command = command
			event.arguments = arguments
			event.arguments_after = arguments_after
			event.pname = message_name
			if event.pname:
				event.plvl = self.getAccessLevel(event.pname)
			else:
				event.plvl = 0					 
			event.chat_no = chatnum
			event.alert_name = alert
			event.alert_arena = arena
			event.command_type = message_type
				
			self.__addPendingEvent(event)
	
	def __handleCommandDie(self, event):
		self.sendReply(event, "Ok")
		self.__log(INFO,"%s stopped by %s" % (self.name,event.pname))
		self.disconnectFromServer()
			
		

	def __handleCommandAbout(self, event):
		self.sendReply(event,"Interpreter:" + platform.python_implementation()+" version:"+platform.python_version())
		self.sendReply(event,"Core:"+self.__core_about)
		self.sendReply(event,"Core Version:"+self.__core_version)
		self.sendReply(event,"BotType:%-10s owner:%-10s"%(self.type,self.owner))
		self.sendReply(event,"About:%s" %(self.description))
		for m in self.__module_info_list:
			self.sendReply(event, "Modules:%10s: %10s:%10s by %10s\t\t %50s" % 
											(m.filename,m.name,m.version,m.author,m.description))

	def __handleCommandHelp(self, event):
		if len(event.arguments_after) > 0:
			fmt = '%'+'-'+str(self.__max_cmd_len)+"s   %s" # make format string based on max cmd size

			if event.arguments_after[0][0] == '*':
				self.sendReply(event, "All commands:")
				for k, v in self.__cmd_dict.iteritems():
					if v.alias != "":
						alias = "/" + v.alias
					else:
						alias = ""
					self.sendReply(event, fmt % (v.name+alias+" "+v.args,v.help_short))
			elif event.arguments_after[0][0] == '!':
				command = self.__getCmd(event.arguments_after[0])
				if command:
					self.sendReply(event, "Extended help for command:")
					self.sendReply(event, "Name:%10s Alias:%10s"%(command.name,command.alias))
					self.sendReply(event, "Accepted Arguments:%s"%(command.args))
					if command.help_long:
						for m in command.help_long.split("\n"):
							self.sendReply(event,m)
					else:
						self.sendReply(event,"This command doesnt have extended help defined for it")
				else:
					self.sendReply(event, "unknown command:")
			else:
				name = event.arguments_after[0].lower()
				cat = self.__category_dict.get(name,None)
				if cat:
					self.sendReply(event, "commands in %s:"%(name))
					for v in cat:
						if v.alias != "":
							alias = "/" + v.alias
						else:
							alias = ""
						self.sendReply(event, fmt % (v.name+alias+" "+v.args,v.help_short))
				else:	
					self.sendReply(event, "no such category exists (%s):"%(name))
		else:
			self.sendReply(event, "commands:")
			for k, v in self.__category_dict.iteritems():
				i = 1
				out = ""
				for e in v:
					if i % 6 == 0:
						self.sendReply(event,k + ": " + out[1:])
						out = ""
						i = 1
					i+=1
					out += "," + e.name 
				if len(out) > 0 :
					self.sendReply(event,k + ": " + out[1:])
					out = ""
		
	def __handleCommandAddop(self, event):
		if (len(event.arguments_after) > 0 
		and len(event.arguments_after[0]) > 3
		and event.arguments_after[0][0].isdigit() 
		and event.arguments_after[0][1] in [':',' ']):
			
			lvl = int(event.arguments_after[0][0])
			name = event.arguments_after[0][2:]
			if lvl <= 0 or lvl > 9:
				self.sendReply(event,"Error:Invalid Level must be between 0 1 and 9")
				return
			if self.getAccessLevel(name) > event.plvl:
				self.sendReply(event,"ERROR:ACCESS DENIED:%s is already an op and has >= access than you do"%(name))
				return
			rc = self.__oplist.AddOp(lvl,name)
			if rc:
				self.sendReply(event,"Success")
				self.__log(INFO,"%s added op %s with %d level" % (event.pname,name,lvl))
			else:
				self.sendReply(event,"Failure")				
				
		else:
			self.sendReply(event,"invalid syntax use: !addop lvl:name")

	def __handleCommandDelop(self, event):
		if len(event.arguments_after) > 0:
			name = event.arguments_after[0]
			if self.getAccessLevel(name) >= event.plvl:
				self.sendReply(event,"ERROR:ACCESS DENIED:You Can only delete ops who have lower levels")
				return
			rc = self.__oplist.DelOp(name)
			if rc:
				self.sendReply(event,"Success")
				self.__log(INFO,"%s deleted op %s" % (event.pname,name))
			else:
				self.sendReply(event,"Failure")				
				
		else:
			self.sendReply(event,"invalid syntax use: !addop lvl:name")

	def __handleCommandListops(self, event):
		self.__oplist.ListOps(self,event)
	
	def __handleCommandReloadops(self, event):
		rc = self.__oplist.Read()
		if rc:
			self.sendReply(event,"Success")
			self.__log(INFO,"%s reloaded oplist" % (event.pname,))
		else:
			self.sendReply(event,"Failure")			  
	
	def __eventEnterPreprocessor(self, event):
			#xxx we should probably make sure the player doesnt already exist here
		player = event.player
		self.__players_by_name[player.name.lower()] = player
		self.__players_by_pid[player.pid] = player
		# make sure player does not already exist in the list
		self.players_here = [p for p in self.players_here if p.pid != player.pid]
		self.players_here.insert(0, player)
		
		if player.name.lower() == self.name.lower():
			self.pid = player.pid
			self.ship = player.ship
			self.freq = player.freq
			self.sendPrivateMessage(player,"*bandwidth 10000")
			self.sendPublicMessage("*relkills 1")
			self.__addPendingEvent(GameEvent(EVENT_LOGIN))
			
		
		return event
	
	def __eventLeavePreprocessor(self, event):
		self.__players_by_name.pop(event.player.name.lower(), None)
		self.__players_by_pid.pop(event.player.pid, None)
		self.players_here = [p for p in self.players_here if p.pid != event.player.pid]
		
		return event
			
	def __eventTickPreprocessor(self, event):
		#send pos update
		now = GetTickCountHs()
		#xxx this will need to be changed later if the bot is out of ship (10hs interval if out of ship)
		
		# update position every 10 hs if in ship, otherwise every 1 second
		if self.ship is not None:
			time_period = 100 if self.ship == SHIP_SPECTATOR else 10
			if TickDiff(now, self.__last_pos_update_sent_tick) > time_period:
				self.__queuePositionUpdatePacket()
				self.__last_pos_update_sent_tick = now
		
		if TickDiff(now, self.__last_timer_expire_tick) > 100:
			self.__expireTimers()
			self.__last_timer_expire_tick = now
		

		#if chats have been added redo the ?Chat command
		if self.__chats_changed and self.isConnected():	
			cstr = "?chat="
			for c in self.__chats:
				cstr += c +","
			self.sendPublicMessage(cstr,0)
			self.logger.info(cstr)
			self.__chats_changed = False
			
		return event
			
	def __eventChangePreprocessor(self, event):
			# update the players freq and ship
			player = event.player
			
			# if this is the bots own info, update it
			if player.pid == self.pid:
				self.ship = event.new_ship
				self.freq = event.new_freq
			
			new_event = GameEvent(EVENT_CHANGE)
			new_event.player = player
			new_event.old_freq = player.freq
			new_event.old_ship = player.ship
			
			player.ship = event.new_ship
			player.freq = event.new_freq
			
			new_event.flags_neuted = player.flag_count
			player.flag_count = 0
			
			return new_event
	
	def __eventDisconnectPreprocessor(self, event):
		self.__connected = False
		return event

	def __eventCommandPreprocessor(self, event):
		command = self.__getCmd(event.command)
		
		if command is None:
			if event.command_type in [COMMAND_TYPE_PRIVATE,COMMAND_TYPE_REMOTE]:
				self.sendReply(event, "Unknown command")
			return None
		
		new_event = None
		if command.IsAllowed(event.command_type) == False:
			return None

		if event.plvl >= command.access_level:
			# this player is allowed to use the command
			new_event = GameEvent(EVENT_COMMAND)
			new_event.player = event.player
			new_event.command = command
			new_event.arguments = event.arguments
			new_event.arguments_after = event.arguments_after
			new_event.pname = event.pname
			new_event.plvl = event.plvl
			new_event.chat_no = event.chat_no
			new_event.alert_name = event.alert_name
			new_event.alert_arena = event.alert_arena
			new_event.command_type = event.command_type

			if self.__botmode != BM_MASTER and command.id == self.__command_die_id:
				self.__handleCommandDie(new_event)
			elif command.id == self.__command_help_id:
				self.__handleCommandHelp(new_event)
			elif command.id == self.__command_about_id:
				self.__handleCommandAbout(new_event)
			elif self.__botmode in [BM_MASTER,BM_STANDALONE]:
				if command.id == self.__command_addop_id :
					self.__handleCommandAddop(new_event)
				elif command.id == self.__command_delop_id :
					self.__handleCommandDelop(new_event)
				elif command.id == self.__command_listops_id :
					self.__handleCommandListops(new_event)
				elif command.id == self.__command_reloadops_id :
					self.__handleCommandReloadops(new_event)
			else:
				event.command = command
		else:
			self.sendReply(event,  "Access denied")
		
		return new_event
			
	def __eventArenaListPreprocessor(self, event):
		#preprocess the negative count
		new_event = GameEvent(EVENT_ARENA_LIST)
		new_event.arena_list = []
		
		for arena, count in event.arena_list:
			if count < 0:
				count = abs(count)
				here = 1
				self.arena = arena
			else:
				here = 0
			
			new_event.arena_list.append((arena, count, here))
			
		return new_event
	
	
	def isConnected(self):
		"""Returns True if the bot is connected to the server, otherwise False."""
		return self.__connected
		
	def __handlePositionUpdateRequest(self, packet):
		self.__queuePositionUpdatePacket()
	
	def __queuePositionUpdatePacket(self,weapons=0):
		"""Queue a position update packet to the server."""
		checksum = 0

		packet = struct.pack("<BBIhHBBHhHHH", 
							0x03, self.rotation, GetTickCountHs(),
							 self.x_vel, self.y_pos, checksum,
							  self.status, self.x_pos, self.y_vel,
							   self.bounty, self.energy, weapons)
		for b in packet:
			checksum ^= ord(b)
			
		
		packet = packet[:10] + chr(checksum) + packet[11:]
		
		self.queuePacket(packet, priority=PRIORITY_HIGH)
		self.__last_pos_update_sent_tick = GetTickCountHs()
	
	def setPosition(self, x_pos=8192, y_pos=8192,
					x_vel=0, y_vel=0, rotation=0,
					status_flags=0, bounty=1000, energy=1000):
		"""Set the bot's coordinates and other position data and send the new position to the server.
		
		status_flags is made of combinations of STATUS_Xxx.
		
		When this is called a packet is queued for send immediately."""
		self.x_pos = x_pos
		self.y_pos = y_pos
		self.x_vel = x_vel
		self.y_vel = y_vel
		self.status = status_flags
		self.bounty = bounty
		self.energy = energy
		self.rotation = rotation
		self.__queuePositionUpdatePacket()

	def makeWeapons(self,type,lvl,shrapb,shraplvl,shrap,alternate):
		"""
		this function will create a weapons struct to pass to sendfireweapon
		type  is WEAPON_XX
		lvl can be 0-3 
		shrap_b 0,1 indicates if the weapon has bouncing shrapnal
		shraplvl 0-3 
		shrap 0-31
		alternate can be 0,1  
			if firing bombs 0 for bombs 1 for mines
			if firing bullets 0 for single gun 1 for multifire
		"""
		return  ((alternate  << 15) | (shrap << 10) |(shraplvl << 8) |
	 			(shrapb <<7 ) |(lvl << 5) | type)  

	def sendFireWeapon(self, x_pos=8192, y_pos=8192,
						x_vel=0, y_vel=0, rotation=0,
						status_flags=0, bounty=1000,
						energy=1000, weapons=0):
		"""
		same as setposition if weapons is not passed
		see WEAPON_XX and makeWeapons function
		"""
		self.x_pos = x_pos
		self.y_pos = y_pos
		self.x_vel = x_vel
		self.y_vel = y_vel
		self.status = status_flags
		self.bounty = bounty
		self.energy = energy
		self.rotation = rotation
		self.__queuePositionUpdatePacket(weapons)
		
	def sendDropBrick(self,x,y):
		"""
		this function will make the bot drop a brick in the specified location
		unfortunatly we cannot control the orientation of the dropped brick
		x,y are in pixels not tiles conversion done by this function
		"""
		x = x>>4
		y = y>>4
		packet = struct.pack("<BHH", 0x1C, x, y)
		self.queuePacket(packet, reliable=True, priority=PRIORITY_HIGH)
			
	def sendFreqChange(self, freq):
		"""Sends a freq change request to the server.
		
		Note that until you receive an EVENT_CHANGE update for the bot,
		your freq has not changed."""
		
		packet = struct.pack("<BH", 0x0F, freq)
		self.queuePacket(packet, priority=PRIORITY_HIGH)
	
	def __isNumeric(self,cstr):
		for i in range(len(cstr)):
			if cstr[i].isdigit():
				pass
			else:
				return False
		return True

	def sendChangeArena(self,arena):
		"""
		allows the bot to change arenas 
		although the protocal supports random arenas 
		this function will only take a string
		which can be a number is pub 0 is 0 
		or  it can be any arena,#arena
		you will recicve event leaves for all player in current arena 
		"""
		if not arena:
			return 
		#send arena leave packet
		self.queuePacket(struct.pack("<B",0x02),reliable=True)
		self.flushOutboundQueues()
		#generate leaves for everyone in the current arena
		for p in self.players_here:
			event = GameEvent(EVENT_LEAVE)
			event.player = p
			event.flags_neuted = p.flag_count
			p.flag_count = 0
			self.__addPendingEvent(event)
		#make enter arena packet		
		if arena:
			if self.__isNumeric(arena):
				atype = int(arena)#public
			else:
				atype = 0xFFFD #private
		else:
			atype = 0xFFFF #random arena
		packet = struct.pack("<BBHHHH",0x01,8,0,4096,4096,atype)
		packet = packet + arena[:15] + '\x00' if atype == 0xFFFD else packet	
		self.queuePacket(packet,reliable=True)
		
		event = GameEvent(EVENT_ARENA_CHANGE)
		event.old_arena = self.arena
		self.arena = arena
		self.__addPendingEvent(event)
		
	def sendShipChange(self, ship_type):
		"""Sends a ship change request to the server.
		
		Note that until you receive an EVENT_CHANGE update for the bot,
		your ship has not changed."""
		
		packet = struct.pack("<BB", 0x18, ship_type)
		self.queuePacket(packet,reliable=True, priority=PRIORITY_HIGH)
			
	def sendPickupFlags(self,flag_id):
		"""
		try to pickup a flag
		"""
		packet = struct.pack("<BH", 0x13, flag_id)
		self.queuePacket(packet, reliable=True, priority=PRIORITY_HIGH)

	def sendFlagDrop(self):
		"""
		if the bot is carrying flags sending this command will
		make it drop all flags at its current coordinates
		 """
		packet = struct.pack("<B", 0x15)
		self.queuePacket(packet, reliable=True, priority=PRIORITY_HIGH)
		
	def sendPickupBall(self,id):
		"""
		try to pickup a Ball id is the ball id 
		"""
		if id >= 0 and id <MAX_BALLS:
			b = self.ball_list[id]
			packet = struct.pack("<BBI", 0x20, b.id, b.time)
			self.queuePacket(packet, reliable=True, priority=PRIORITY_HIGH)

	def sendScoreGoal(self,id):#doesnt work
		"""
		try to score a goal if the bot has a ball
		"""
		#if id >= 0 and id <MAX_BALLS:
		#	b = self.ball_list[id]
		packet = struct.pack("<BBI", 0x21, id, GetTickCountHs())
		self.queuePacket(packet,reliable=True, priority=PRIORITY_HIGH)
		
	def sendShootBall(self,id,x,y,dx,dy):
		"""shoots powerball if the bot has a ball x,y in pixels"""
		#if id >= 0 and id <MAX_BALLS:
		#	b = self.ball_list[id]
		packet = struct.pack("<BBhhhhhI", 0x1F, id, x, y,
							 dx, dy, self.pid, GetTickCountHs())
		self.queuePacket(packet, reliable=True, priority=PRIORITY_HIGH)	
	
	def sendAttach(self,pp):#untested
		"""sendAttach use this if you want the bot to attach to a player"""
		pid = self.__toPid(pp)
		packet = struct.pack("<BH",0x10,pid)
		self.queuePacket(packet, reliable=True)
	
	def sendChangeSettings(self,settings_list):
		"""
		sendChangeSettings:allows you to cluster 
		and send a list of settings changes in one packet
		settings_list must be a list 1 or more items
		eg. sendChangeSettings(["Team:MaxPerTeam:4","Team:MaxPerPrivateTeam:4"])
		"""
		if type(settings_list) == types.ListType and len(settings_list) > 0:
			packet = struct.pack("<B",0x1d)
			for e in settings_list:
				packet += e + chr(0)
			packet+=chr(0)
			self.queuePacket(packet, reliable=True)	
		else:
			self.__log(DEBUG,"sendChangesettings argument must be a list of strings with atleast 1 entry")		
		
	def __parseExtraPlayerData(self,event,packet):
		energy, s2c_ping, timer,t1 = struct.unpack_from("<HHHI", packet)
		event.sd_updated = True
		player = event.player
		player.sd_energy = energy
		player.sd_s2c_ping = s2c_ping
		player.sd_timer = timer
		player.sd_shields = 1 if t1 & 1 else 0
		player.sd_super = 1 if (t1 & (1<<1)) else 0
		player.sd_bursts = (t1 & (0xF << 2))>> 2
		player.sd_repels = (t1 & (0xF << 6))>> 6
		player.sd_thors = (t1 & (0xF << 10))>> 10
		player.sd_bricks =(t1 & (0xF << 14))>> 14
		player.sd_decoys =(t1 & (0xF << 18))>> 18
		player.sd_rockets =(t1 & (0xF << 22))>> 22
		player.sd_portals =(t1 & (0xF << 26))>> 26
		player.sd_time = GetTickCountHs()
		
	def __handleSmallPositionUpdatePacket(self, packet):
		# pos updates dont come for yourself, so this packet does not check against the bot's pid
		type, rotation, timestamp, x_pos, latency, bounty, pid, status, y_vel, y_pos, x_vel = struct.unpack_from("<BBHHBBBBhHh", packet)
		player = self.findPlayerByPid(pid)
		if player:
			player.rotation = rotation
			player.x_pos = x_pos
			player.y_pos = y_pos
			player.x_vel = x_vel
			player.y_vel = y_vel
			player._setStatus(status)
			player.bounty = bounty
			player.ping = latency
			player.last_pos_update_tick = GetTickCountHs()
			
			
			event = GameEvent(EVENT_POSITION_UPDATE)
			event.player = player
			event.fired_weapons = False
			if len(packet) == 26:
				self.__parseExtraPlayerData(event, packet[16:])
			else:
				event.sd_updated = False
			
			self.__addPendingEvent(event)
			
	def __handleKothGameReset(self, packet):
		#dont really need to decode this just 
		#send a response to remove bot from koth game
		self.queuePacket(struct.pack("<B", 0x1E),reliable=True)
		
	def __parseWeapons(self,event,weapons):
		event.weapons_type = (weapons & 0x1F)
		event.weapons_level = (weapons & (0x3 << 4))>> 4
		event.shrap_bouncing = (weapons & (1 << 6))>> 6
		event.shrap_level = (weapons & (0x3 << 7))>> 7
		event.shrap = (weapons & (0x1F << 9))>> 9
		event.alternate = 1 if (1 << 15 & weapons) else 0 
			
	def __handleLargePositionUpdatePacket(self, packet):
		# pos updates dont come for yourself, so this packet does not check against the bot's pid
		#xxx this packet is actually a lot larger and some fields are ignored here
		type, rotation, timestamp, x_pos, y_vel, pid, x_vel, checksum, status, latency, y_pos, bounty, weapons = struct.unpack_from("<BBHHhHhBBBHHH", packet)
		
		player = self.findPlayerByPid(pid)
		if player:
			player.rotation = rotation
			player.x_pos = x_pos
			player.y_pos = y_pos
			player.x_vel = x_vel
			player.y_vel = y_vel
			player._setStatus(status)
			player.bounty = bounty
			player.ping = latency
			player.last_pos_update_tick = GetTickCountHs()
			
			event = GameEvent(EVENT_POSITION_UPDATE)
			event.player = player
			#parse weapons
			event.fired_weapons = True
			self.__parseWeapons(event,weapons)
			#parse extra data if it exists
			if len(packet) == 31:
				self.__parseExtraPlayerData(event, packet[21:])
			else:
				event.sd_updated = False	
			self.__addPendingEvent(event)
	
	def __handleKillPacket(self, packet):
		type, death_green_id, killer_pid, killed_pid, bounty, flags_transfered = struct.unpack_from("<BBHHHH", packet)
		
		killer = self.findPlayerByPid(killer_pid)
		killed = self.findPlayerByPid(killed_pid)
		
		if killer and killed:
			event = GameEvent(EVENT_KILL)
			event.killed = killed
			event.killer = killer
			event.death_green_id = death_green_id
			event.bounty = bounty 
			event.flags_transfered = flags_transfered
			killer.flag_count+= flags_transfered
			killed.flag_count = 0
			self.__addPendingEvent(event)
	
	def __eventKillPostprocessor(self,event):
		pass
	
	def __eventDisconnectPostprocessor(self,event):
			#self.__log(CRITICAL,"disc postprocessor")
			#self.loseConnection()
			return event
	
				
	def __handleArenaListPacket(self, packet):
		"""'arenaname\x00\xFF\xFF'"""
		offset = 1 # skip the type byte
		arena_list = []
		while offset < len(packet):
			terminating_null = packet.find('\x00', offset)
			name = packet[offset:terminating_null]
			offset = terminating_null + 1
			count, = struct.unpack_from("h", packet, offset)
			offset += 2
			arena_list.append((name, count))
		
		event = GameEvent(EVENT_ARENA_LIST)
		event.arena_list = arena_list
		self.__addPendingEvent(event)

	def __handleBrickDropPacket(self, packet):
		packet = packet[1:]
		l = []
		while len(packet) >= 16:
			x1,y1,x2,y2,freq,id,timestamp = struct.unpack_from("HHHHHHI",packet)
			l.append(Brick(x1,y1,x2,y2,freq,id,timestamp))
			packet = packet[16:]
		event = GameEvent(EVENT_BRICK)
		event.brick_list = l
		self.__addPendingEvent(event)
		
	def __handleWarptoPacket(self, packet):
		type,x,y = struct.unpack_from("<BHH", packet)
		self.x_pos = x<<4
		self.y_pos = y<<4
		self.__queuePositionUpdatePacket()
	
	def __handleCompressedMapPacket(self,packet):#untested
		type,mapname = struct.unpack_from("<B16s", packet)
		mapdata = zlib.decompress(packet[17:])
		mapname = mapname[0:mapname.find(chr(0))]
		f = open(mapname,"wb")
		f.write(mapdata)
		f.close()
		self.__log(DEBUG,"downloaded " + mapname)	 

	def __handleFileTransfer(self,packet):
		type,filename = struct.unpack_from("<B16s", packet)
		if len(packet) == 17:
			self.__log(ERROR,"Requested File Doesnt Exist: " + filename)
		else:	
			if filename[0] == chr(0):
				filename="news.txt"
				data = packet[17:]
			else:
				filename = filename[0:filename.find(chr(0))]
				data = packet[17:]
				#data = zlib.decompress(packet[17:])

			f = open(filename,"wb")
			f.write(data)
			f.close()
			self.__log(DEBUG,"downloaded " + filename)
#		self.__log(INFO,"*getfile disabled")
		
	def __handleRequestFile(self,packet):#0x19
		type,lfname,rfname = struct.unpack_from("<B256s16s", packet)
		lfname = lfname[0:lfname.find(chr(0))]
		rfname = rfname[0:rfname.find(chr(0))]
		self.__log(DEBUG,"server is requesting %s as %s"%(lfname,rfname))
		self.__sendFile(lfname,rfname)

	def __sendFile(self,filename,remotefilename):#0x16
		if (os.path.isfile(os.getcwd()+ "//" + filename)):
			packet = struct.pack("<B16s",0x16,remotefilename[0:14]+chr(0))
			#packet+= zlib.compress(open(os.getcwd()+ "//" + filename,"rb").read())
			packet+= open(os.getcwd()+ "//" + filename,"rb").read()
			self.__log(DEBUG,"sending file:%s"%(filename,))
			self.queuePacket(packet)
		else:
			self.__log(ERROR,"sendfile %s localfile doesnt exist"%(filename,))
#		self.__log(INFO,"*putfile disabled(doesnt work)")

	def __requestLevelFile(self):
		self.queuePacket(struct.pack("<B",0x0C),reliable=True)	 

	def __handleMapInformationPacket(self,packet):
		type,mapname,checksum_remote = struct.unpack_from("<B16sI", packet)
		if self.__downloadLevelFiles == True:
			mapname = mapname[0:mapname.find(chr(0))]
			if (os.path.isfile(os.getcwd()+ "//" + mapname)):
				checksum_local = self.fc.getFileChecksum(mapname)
				if checksum_local != checksum_remote:
#					self.__requestLevelFile()
#					self.__log(DEBUG,"MAPLEVEL CHANGED???: ([%x]!=%x" %(checksum_local,checksum_remote))
					pass
			else:
				self.__requestLevelFile()

	def putFile(self,filename):#doesnt work dont use!!!
		self.sendPublicMessage("*putfile " + filename, sound=SOUND_NONE) 

	def getFile(self,filename):
		self.sendPublicMessage("*getfile " + filename, sound=SOUND_NONE) 				

	def __handleWatchDamagePacket(self,packet):
		type,attacked,time_stamp = struct.unpack_from("<BHI",packet)
		packet = packet[7:]
		pattacked = self.findPlayerByPid(attacked)
		while len(packet) >= 9:
			attacker,weapons,energy_old,energy_lost = struct.unpack_from("<HHHH", packet)
			event = GameEvent(EVENT_WATCH_DAMAGE)
			event.attacked = pattacked
			event.attacker = self.findPlayerByPid(attacker)
			event.energy_old = energy_old
			event.energy_lost = energy_lost
			self.__parseWeapons(event,weapons)
			self.__addPendingEvent(event)
			packet = packet[9:]
			#print( "damage " + event.attacked.name +" damage:" + str(event.energy_lost) + " old:" + str(event.energy_old) + " from " + event.attacker.name)

	def __makePaddedString(self,data,size):
		d =  data + ((size - len(data)) * chr(0))
		assert(len(d) == size)
		return d
	def __sendRegistrationForm(self):#copied from twcore doesnt work, probably queueHugeChunkPacket broken?
		packet  = struct.pack("<B32s64s32s24sBBBBBHHI40s",
							0x17,
							self.__makePaddedString("thejunky",32),
							self.__makePaddedString("thejunky@gmail.com",64),
							self.__makePaddedString("WTF",32),
							self.__makePaddedString("WTF",24),
							77,20,1,1,1,586,0xC000,2036,
							self.__makePaddedString(self.name,40))
		packet += (self.__makePaddedString("PYCore",40) * 14)
							
		self.queuePacket(packet,True,PRIORITY_HIGH)
	
			
	
	def ProcessEventQueue(self):
		#xxx make sure large event lists dont starve the core, and i/o should probably be done between events...
		while len(self.__event_list) > 0:
			# give the core the chance to preprocess events, this is needed
			# because if the changes were made immediately when the event was received (as opposed to when the packet is removed from queue for processing)
			# the core's view of the game state might be incorrect
			event =  self.__event_list.pop(0)
			preprocessor = self.__event_preprocessors.get(event.type, None)
			if preprocessor:
				event = preprocessor(event)
			if event is None: continue
			self.__last_event_generated = event
			
			# this is whewrre the the events get conveyed to custom bot behaviors
			#........
			for bot in self.__botlist:
				bot.HandleEvents(self,event)
		self.flushOutboundQueues()
				
	def __addPendingEvent(self, game_event):
		self.__event_list.append(game_event)
		
		