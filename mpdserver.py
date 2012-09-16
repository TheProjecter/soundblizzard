#!/usr/bin/python
'''
Created on 20 Mar 2011

@author: sam
'''
#try:
#TODO: out = "<html>%(head)s%(prologue)s%(query)s%(tail)s</html>" % locals() change all var substitutions to this, it's faster, see http://wiki.python.org/moin/PythonSpeed/PerformanceTips
import socket, loggy, soundblizzard, re, config
from gi.repository import GObject
import traceback #TODO: put this in loggy
#except:
#    loggy.warn('Could not find required libraries: socket GObject loggy player')
#TODO: use is not ==

class mpdserver(object):
	'''
	MPD Server Class - creates MPD Server connection
	Settings - self.port = tcp_port
	self.host = tcp_host
	'''
	def __init__(self, sb):
		self.sb = soundblizzard.soundblizzard
		self.sb = sb
		self.queue = ''
		self.queueing = False
		self.ok_queueing = False
		self.startserver(self.sb.config.config['mpdhost'],int(self.sb.config.config['mpdport']))
	def startserver(self, host, port):
		self.host = host
		self.port = port
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			self.sock.bind((self.host, self.port)) #TODO: check port empty first
		except:
			loggy.warn('mpdserver failed to start on host %s port %s' % (self.host, self.port))
			return False
		self.sock.listen(1)
		loggy.log('mpdserver Interface Running on ' + host + ':' + str(port) )
		GObject.io_add_watch(self.sock, GObject.IO_IN, self.listener)
	def listener(self, sock, *args):
		'''Asynchronous connection listener. Starts a handler for each connection.'''
		self.conn, temp = sock.accept()
		loggy.log( "mpdserver connected from " + str(self.conn.getsockname()))
		GObject.io_add_watch(self.conn, GObject.IO_IN, self.handler)
		self.conn.send('OK MPD 0.16.0\n')
		return True
	def handler(self, conn, *args):
		'''Asynchronous connection handler. Processes each line from the socket.'''
		buff = conn.recv(4096) #TODO: handle if more on conn to recieve than 4096
		if not len(buff):
			loggy.log( "mpdserver Connection closed - no input." )
			return False
		elif len(buff)>4000:
			loggy.warn('mpdserver Connection buff full, data may be lost' . buff)
		#loggy.log('MPD Server got:' +buff)
		while '\n' in buff:
			(line, buff) = buff.split("\n", 1)
			output = ''
			if not len(line):
				loggy.log( "mpdserver Connection closed - no input." )
				return False
			else:
				arg = line.strip().split(' ', 1) #strips whitespace from right and left, then splits first word off as command
				command = arg[0].lower() # prevents case sensitivity
				#TODO: reimplement using a dict?
				if (len(arg)>1): # if there are arguments to the command
					args = arg[1].strip()
				else:
					args = ''
				#Tries to recognise command
				#Playback control
				func = None
				loggy.debug('mpdserver got {0} {1}'.format(command, args))
				# Makes sure command is not internal function
				if command in ('startsever', 'trackdetails', 'handler', 'listner'):
					loggy.warn('mpdserver attempt to access internals {0}'.format(command))
				else:
					#Searches for command in current class
					try:
						func = getattr(self, command)
					except Exception as detail:
						output = 'ACK 50@1 {{{0}}} Command not recognised\n'.format (command)
						loggy.warn('mpdserver: {0}'.format(output))
						self.queueing = False
						self.ok_queueing = False
					else:
						#Executes command
						try:
							output = func(args)
						except Exception as detail:
							output = 'ACK 50@1 {{{0}}} {1} {2} {3}\n'.format(command, detail, str(type(detail)), traceback.format_exc().replace('\n', '|')) 
							loggy.warn('mpdserver: {0}'.format(output))
							self.queueing = False
							self.ok_queueing = False
				#Handles output - with respect to list queueing
				if output.startswith('ACK'):
					self.queueing = False
					self.ok_queueing = False
					output = self.queue + output
					self.queue = ''
				elif self.ok_queueing:
					#if output[-3:-1] == 'OK':
						#output = output[:-3] + 'list_OK\n'
					output = output.replace("OK", "list_OK")
					self.queue += output
					output = ''
				elif self.queueing:
					self.queue += output
					output = ''
				#send output
				if (output != None):
					loggy.debug( 'MPD Server sending: {0}'.format( output) )
					conn.send(output)
		return True
				#TODO: reflection, stickers, client to client
	def trackdetails (self, pl):
		output = ''
		for index, item in enumerate(pl):
			values = self.sb.sbdb.get_id_db_info(item)
			if not values:
				values = self.sb.sbdb.blanktags
			print values
			#output = "%sfile: %s\nLast-Modified: %s\nTime: %s\nArtist: %s\nAlbumArtist: %s\nTitle: %s\nAlbum: %s Track: %s/%s\nDate: %s\nPos: %s\nId: %s\n" % \
			#(output, values['uri'], values['mtime'], values['duration'], values['artist'], values['album-artist'], values['title'], values['album'], \
			#values['track-number'], values['track-count'], values['date'],index, values['songid'])
			songinfo ='''{output}file: {values[uri]}
Last-Modified: {values[mtime]}
Time: {values[duration]}
Artist: {values[artist]}
AlbumArtist: {values[album-artist]}
Title: {values[title]}
Album: {values[album]}
Track: {values[track-number]}/{values[track-count]}
Date: {values[date]}
Pos: {index}
Id: {values[songid]}\n'''
			output = songinfo.format(output=output, values=values, index=index)		
		return output

#Command list functions
	def command_list_begin(self, arg):
		self.queueing = True
		return ''
	def command_list_ok_begin(self, arg):
		self.ok_queueing = True
		return ''
	def command_list_end(self, arg):
		self.queueing = False
		self.ok_queueing = False
		output = self.queue + 'OK\n'
		self.queue = ''
		return output
#Querying MPD Status
	def clearerror(self, arg):
		return 'OK\n'
	def currentsong(self, arg):
			output = 'file: %s\n' % (self.sb.player.uri)#TODO: convert from uri low priority
			output += 'Last-Modified: 2012-08-21T21:18:58Z\n' # TODO: change to format instead of % and not +=
			output += 'Time: %i\n' % (self.sb.player.dursec)
			output += 'Artist: %s\n' % str(self.sb.player.tags.get('artist'))
			output += 'AlbumArtist: %s\n' % str(self.sb.player.tags.get('album-artist'))
			output += 'Title: %s\n' % str(self.sb.player.tags.get('title'))
			output += 'Album: %s\n' % str(self.sb.player.tags.get('artist'))
			output += 'Track: %s\n' % (str(self.sb.player.tags.get('track-number'))+'/'+str(self.sb.player.tags.get('track-count')))
			output += 'Date: %s\n' % str(self.sb.player.tags.get('date').year)
			output += 'Genre: %s\n' % str(self.sb.player.tags.get('genre'))
			output += 'Pos: %i\n' % (self.sb.playlist.position)
			output += 'Id: %i\n' % (self.sb.sbdb.get_uri_db_info(self.sb.player.uri)['songid'])#TODO: put all info into tags
			output += 'OK\n'
			return output
	def idle(self, arg):
		return 'changed: database update stored_playlist playlist player mixer output options sticker subscription message\nOK\n'#TODO: handle properly
	def status(self, arg):
		output = 'volume: %i\n' % (self.sb.player.vol) #TODO: get rid of % and +=
		output += 'repeat: %i\n' % (int(self.sb.playlist.repeat.get()))
		output += 'random: %i\n' % (int(self.sb.playlist.random.get()))
		output += 'single: %i\n' % (int(self.sb.playlist.single.get()))
		output += 'consume: %i\n' % (int(self.sb.playlist.consume.get()))
		output += 'playlist: %i\n' % (1)
		output += 'playlistlength: %i\n' % (2)
		output += 'xfade: %i\n' % (0)
		output += 'state: %s\n' % (self.sb.player.state)
		output += 'song: %i\n' % (1)
		output += 'songid: %i\n' % (1)
		output += 'time: %s:%s\n' % (self.sb.player.possec, self.sb.player.dursec)
		output += 'elapsed: %s.000\n' % (self.sb.player.possec)
		output += 'bitrate: %i\n' % (1)
		output += 'audio: %s\n' % ('x')
		output += 'nextsong: %i\n' % (1)
		output += 'nextsongid: %i\n' % (1)
		output += 'OK\n'
		return output
	def stats(self, arg):
		return 'artists: %i\nalbums: %i\nsongs: %i\nuptime: %i\nplaytime: %i\ndb_playtime: %i\ndb_update: %i\nOK\n' % (1,1,1,1,1,1,1) #TODO: stats
#Playback options
	def consume(self, arg):
		self.sb.playlist.consume.set(int(arg))
		return 'OK\n'
	def crossfade(self, arg):
		return 'OK\n'
	def mixrampdb(self, arg):
		return 'OK\n'
	def mixrampdelay(self, arg):
		return 'OK\n'	
	def random(self, arg):
		self.sb.playlist.random.set(int(arg))
		return 'OK\n'
	def repeat(self, arg):
		self.sb.playlist.repeat.set(int(arg))
		return 'OK\n'
	def setvol(self, arg):
		self.sb.player.setvol(int(arg))
		return 'OK\n'
	def single(self, arg):
		self.sb.playlist.single.set(int(arg))
		return 'OK\n'
	def replay_gain_mode(self, arg):
		return 'OK\n'
	def replay_gain_status(self, arg):
		return 'OK\n'
#Controlling playback
	def next(self, arg):
		self.sb.playlist.get_next()
		return 'OK\n'
	def pause(self, arg):
		if len(arg)>0:
			if int(arg):
				self.sb.player.play()
			else:
				self.sb.player.pause()
		else:
			self.sb.player.playpause()
		return 'OK\n'
	def play(self, arg):
		if len(arg)>0:
			self.sb.playlist.load_pos(int(arg))
		else:
			self.sb.player.play()
		return 'OK\n'
	def playid(self, arg):
		self.sb.playlist.load_id(int(arg))
		return 'OK\n'
	def previous(self, arg):
		self.sb.playlist.get_prev()
		return'OK\n'
	def seek(self, arg):
		arg = arg.split()
		if len(arg)>1:
			self.sb.playlist.load_pos(int(arg[0]))
			self.sb.player.setpos(int(arg[1])*self.sb.player.SECOND)
			#TODO: seek doesn't work after load on this or seekid
		else:
			self.sb.player.setpos(int(arg[0])*self.sb.player.SECOND)
		return 'OK\n'
	def seekid(self, arg):
		arg = arg.split()
		if len(arg)>1:
			self.sb.playlist.load_id(int(arg[0]))
			self.sb.player.setpos(int(arg[1]) * self.sb.player.SECOND)
		else:
			self.sb.player.setpos(int(arg[0]) * self.sb.player.SECOND)
		return 'OK\n'
	def seekcur(self, arg):
		if len(arg) > 0:
			self.sb.player.setpos(int(arg) * self.sb.player.SECOND)
		return 'OK\n'
	def stop(self, arg):
		self.sb.player.stop()
		return 'OK\n'
#Current Playlist
	def add(self, arg):
		songid = self.sb.playlist.add_uri(str(arg).strip('\"\''))
		if songid is not False:
			output = 'OK\n'
		else:
			output = 'ACK could not add file - not located in db\n'
		return output
	def addid(self, arg):
		match = re.search('(.*)\s+(\d+)$', arg) #TODO: implement mpdserver.addid - does not remove pos
		if match:
			pos = int(match.group(2))
			uri = match.group(1).strip('\s\'\"')
		else:
			uri = arg.strip('\s\'\"')
			pos = None
		loggy.debug('mpdserver.addid {0}:{1}'.format(uri,pos))
		songid = self.sb.playlist.add_uri(uri, pos)
		if songid is not False:
			return'OK\n'
		raise Exception('could not add file - not located in db')
	def clear(self, arg):
		self.sb.playlist.load_playlist([])
		return 'OK\n'
	def delete(self, arg):
		arg = arg.split(':')
		if len(arg)>1:
			self.sb.playlist.delete_pos(int(arg[0]),int(arg[1]))
		else:
			self.sb.playlist.delete_pos(int(arg[0]))
		return 'OK\n'
#TODO: which is faster regex or string formatting - see above?
#		match = re.search('(\d+):*(\d*)', arg)
#		if match:
#			self.sb.playlist.delete(int(match.group(1)), int(match.group(2)))
#		else:
#			return 'ACK 50@1 {{delete}} incorrect format - delete [{POS} | {START:END}]\n'
	def deleteid(self, arg):
		self.sb.playlist.delete_songid(int(arg))
		return 'OK\n'
	def move(self, arg):
		match = re.search('(?P<fromstart>\d+):*(?P<fromend>\d*)\s*(?P<moveto>\d*)', arg)
		if match:
			fromstart = int(match.group('fromstart'))
			if match.group('fromend').isdigit():
				fromend = int(match.group('fromend'))
			else:
				fromend = fromstart+1
			if match.group('moveto').isdigit():
				moveto = int(match.group('fromend'))
			else:
				moveto = None
			self.sb.playlist.move(fromstart, fromend, moveto)
			return 'OK\n'
		else:
			return 'ACK 50@1 {{move}} incorrect format - move [{FROM} | {START:END}] {TO}\n'  #TODO: switch all these to raise
	def moveid(self, arg):
		songid,pos = arg.split
		self.sb.playlist.move_id(songid, pos)
		return 'OK\n'
		#TODO implement -ve item
	def playlist(self, arg):
		output = []
		for index, item in enumerate(self.sb.playlist.playlist):
			uri = self.sb.sbdb.get_id_db_info(item)
			if uri:
				uri = uri['uri']
			else:
				uri = ''
			output.append('{0}:file: {1}\n'.format(index,uri)) #TODO: ?need to strip uri to file?
		output.append('OK\n')
		return ''.join(output)
	def playlistfind(self, arg):
		return 'OK\n' #TODO: implement mpdserver.playlistfind
	def playlistid(self, arg):
		if len(arg)>0:
			output = self.trackdetails([int(arg)])
		else:
			output = self.trackdetails(self.sb.playlist.playlist)
		output += 'OK\n'
		return output
	def playlistinfo(self, arg):
		temp = arg.split(':')
		if len(temp)>1:
			start = temp[0]
			end = temp[1]
		else:
			start = temp[0]
			end = start
		output = self.trackdetails(self.sb.playlist.playlist[start:end])
		output.append('OK\n')
		return ''.join(output)
	def playlistsearch(self, arg):
		return 'OK\n' #TODO: implement mpdserver.playlistsearch
	def plchanges(self, arg):
		return self.playlistid('') #TODO: implement mpdserver.plchanges
	def plchangesposid(self, arg):
		return self.playlistid('') #TODO: implement mpdserver.plchanges
	def prio(self, arg):
		return 'OK\n' #TODO: implement mpdserver.prio and mpdserver.prioid
	def prioid(self, arg):
		return 'OK\n'
	def swap(self, arg): # TODO: implement mpdserver.swap and mpdserver.swapid
		return 'OK\n'
	def swapid(self, arg):
		return 'OK\n'
	
	
	
	
	
	
	
	
	
	
	
			
		
if __name__ == "__main__":
	#player1 = player.player()
	#player1.load_file('/data/Music/Girl Talk/All Day/01 - Girl Talk - Oh No.mp3')
	mpdserver1 = mpdserver(None)
	mpdserver1.startserver('', 6600)
	GObject.MainLoop().run()
	#TODO: handle address lost
