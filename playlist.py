try:
	import loggy, player, random, soundblizzard
except:
	loggy.warn('Could not find required libraries: loggy, player, gobject')
from gi.repository import GObject
class playlist():
	playlist = []
	position = -1
	history = []
	def __init__(self, sb):
		self.sb = soundblizzard.soundblizzard # fakes for tab completion - assigns it to the class
		self.sb = sb #self.sb is now the parent soundblizzard instance
		self.sb.player.connect("eos", self.get_next)
		self.random = self.toggle(False) #TODO emit signal when these change - see set attr
		self.repeat = self.toggle(False)
		self.consume = self.toggle(False)
		self.single = self.toggle(False)
	class toggle(GObject.GObject):
		toggle = False # holds boolean
		__gsignals__ = {'changed' : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,(GObject.TYPE_BOOLEAN,)),}	
		def __init__(self, value=None):	
			GObject.GObject.__init__(self)
			if value:
				self.toggle = value
		def get(self):
			return self.toggle
		def set(self, value):
			value = bool(value)
			if self.toggle != value:
				self.toggle = value
				loggy.debug('playlist.set {0}'.format(value))
				self.emit('changed', value)				
	def load_playlist(self, filename):
		self.playlist = [0,1,2,3,4,5]
		self.position = -1
		self.history = []
		self.get_next()
	def get_next(self, *data):
		if self.single.get():
			if self.repeat.get():
				None #stay on same file
			else:
				return #TODO: emit end of playlist signal
		elif self.random.get():
			self.position = random.randint(0, len[self.playlist]-1)
		else:
			self.position += 1
			if self.position >= (len(self.playlist)):
				if self.repeat.get():
					self.position = 0
				else:
					self.position = 0
					return #TODO: emit end of playlist signal
		#TODO: implement consume
		self.load_id(self.playlist[self.position])
	def load_pos(self, pos):
		'''
		Starts playing playlist at position pos
		'''
		self.position = pos
		self.load_id(self.playlist[self.position])
	def load_id(self, songid):
		#self.sb.player.load_uri(self.sb.sbdb.get_id_db_info(id)['uri'])
		try:
			self.sb.player.load_uri(self.sb.sbdb.get_id_db_info(songid)['uri'])
		except TypeError:
			loggy.warn('could not get next playlist item, skipping')
			self.get_next()
	def get_prev(self):
		self.position -= 1
		if (self.position<0):
			self.position = 0
		self.load_id(self.playlist[self.position])

if __name__ == "__main__":
	player1 = player.player()
	player1.playlist = playlist(player1)

	GObject.MainLoop().run()
	#TODO: handle address lost

