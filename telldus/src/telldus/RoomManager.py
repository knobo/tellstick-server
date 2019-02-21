# -*- coding: utf-8 -*-

from base import \
	ISignalObserver, \
	Plugin, \
	Settings, \
	implements, \
	signal
from tellduslive.base import TelldusLive, LiveMessage, ITelldusLiveObserver

__name__ = 'telldus'  # pylint: disable=W0622

class RoomManager(Plugin):
	"""The roommanager holds and manages all the rooms in the server"""
	implements(ISignalObserver)
	implements(ITelldusLiveObserver)
	public = True

	def __init__(self):
		self.rooms = {}
		self.settings = Settings('telldus.rooms')
		self.rooms = self.settings.get('rooms', {})

	def setMode(self, roomId, mode):
		"""
		Set a room to a new mode
		"""
		room = self.rooms.get(roomId, None)
		if not room:
			return
		if room['mode'] != mode:
			room['mode'] = mode
			self.settings['rooms'] = self.rooms
			live = TelldusLive(self.context)
			if live.registered and room.get('responsible', '') == live.uuid:
				# Notify live if we are the owner
				msg = LiveMessage('RoomModeSet')
				msg.append({
					'id': roomId,
					'mode': mode
				})
				live.send(msg)
		self.__modeChanged(roomId, mode, 'room', room.get('name', ''))

	@signal('modeChanged')
	def __modeChanged(self, objectId, modeId, objectType, objectName):
		"""
		Called every time the mode changes for a room
		"""
		pass

	@TelldusLive.handler('room')
	def __handleRoom(self, msg):
		data = msg.argument(0).toNative()
		if 'name' in data:
			if isinstance(data['name'], int):
				data['name'] = str(data['name'])
			else:
				data['name'] = data['name'].decode('UTF-8')
		live = TelldusLive(self.context)
		if data['action'] == 'set':
			oldResponsible = ''
			if data['id'] in self.rooms:
				# existing room
				room = self.rooms[data['id']]
				oldResponsible = room['responsible']
				validKeys = ['name', 'color', 'content', 'icon', 'responsible']
				for key in validKeys:
					if key in data:
						room[key] = data.get(key, '')
				self.rooms[data['id']] = room
			else:
				# new room
				self.rooms[data['id']] = {
					'name': data.get('name', ''),
					'parent': data.get('parent', ''),
					'color': data.get('color', ''),
					'content': data.get('content', ''),
					'icon': data.get('icon', ''),
					'responsible': data['responsible'],
					'mode': data.get('mode', ''),
				}
			if live.registered and \
			    (data['responsible'] == live.uuid or oldResponsible == live.uuid):
				room = self.rooms[data['id']]
				msg = LiveMessage('RoomSet')
				msg.append({
					# No need to call get() on room here since we know every value has at least a
					# default value above
					'id': data['id'],
					'name': room['name'],
					'parent': room['parent'],
					'color': room['color'],
					'content': room['content'],
					'icon': room['icon'],
					'responsible': room['responsible'],
					'mode': room['mode'],
				})
				live.send(msg)
			self.settings['rooms'] = self.rooms
			return

		if data['action'] == 'remove':
			room = self.rooms.pop(data['id'], None)
			if room is None:
				return
			live = TelldusLive(self.context)
			if live.registered and room['responsible'] == live.uuid:
				msg = LiveMessage('RoomRemoved')
				msg.append({'id': data['id']})
				live.send(msg)
			self.settings['rooms'] = self.rooms
			return

		if data['action'] == 'setMode':
			self.setMode(data.get('id', None), data.get('mode', ''))
			return