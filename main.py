import discord
import asyncio

import pafy

import urllib.request
import urllib.parse
import re
import json
import os.path
import sys
import logging
import time
from logging.handlers import RotatingFileHandler

from contextlib import suppress

import random


# Queue of songs to play
class SongPlayer:
	def __init__(self):
		self.songList = []
		self.voiceClient = None
		self.currentPlayer = None
		self.volume = 0.5
		self.currentSongFile = ""
		self.exception = None

	# Get the error that stopped the player
	def getPlayerError(self):
		if self.currentPlayer == None:
			return "No Error"
		
		if self.currentPlayer.error == None:
			return "No Error"

		return self.currentPlayer.error

	# Stop the player from streaming the song
	def stopPlayer(self):
		if self.currentPlayer != None:
			self.currentPlayer.stop()

	# Pause the current song
	def pause(self):
		if self.isSongPlaying():
			logging.info("Pausing player")
			self.currentPlayer.pause()

	# Resume the current song
	def resume(self):
		if self.currentPlayer != None:
			logging.info("Resuming player")
			self.currentPlayer.resume()
	
	# Update the volume of the voice player
	def updateVolume(self, volume):
		self.volume = volume	

		# Update the current player if it's there
		if self.currentPlayer != None:
			self.currentPlayer.volume = volume

	# Add a song to the song list
	def addSong(self, songName):
		self.songList.append(songName)
		logging.info("Added song")

	# Skip the current song
	async def skipSong(self):
		# There is no currentPlayer
		if self.currentPlayer == None:
			return

		# There is no song playing
		if not self.currentPlayer.is_playing():
			return

		# Skip the current song
		self.currentPlayer.stop()
		self.playNextSong()

	# Update the voice channel that the bot is in
	async def updateChannel(self, channelName, message):
		# Get the channel
		channel = discord.utils.get(message.server.channels, name=channelName, type=discord.ChannelType.voice)
		server = message.server
		voiceConnected = client.is_voice_connected(server)

		try:
			# Client is not is a channel
			if not voiceConnected:
				self.voiceClient = await client.join_voice_channel(channel)
			# Client is already in a channel
			else:
				await self.voiceClient.move_to(channel)
		except discord.InvalidArgument:
			logging.warning("Channel was not a voice channel")
			return
		except (discord.ClientException):
			logging.warning("You're already connected to a voice channel")			
			return

	def canPlaySong(self):
		# Don't have a client yet
		if self.voiceClient == None:
			return False

		# Song is already playing
		if self.currentPlayer != None and self.currentPlayer.is_playing():
			return False

		return True

	# Check if a song is currently playing
	def isSongPlaying(self):
		# Is there a player
		if self.currentPlayer == None:
			return false

		# Is the player playing a song
		return self.currentPlayer.is_playing()

	# Remove a song off the top of the list
	def popSong(self):
		#List is empty
		if len(self.songList) == 0:
			return None
		# One song left
		elif len(self.songList) == 1:
			returnSong = self.songList[0]
			self.songList = []

			return returnSong
		else:
			returnSong = self.songList[0]
			self.songList = self.songList[1:]

			return returnSong

	# Play the next song on the list
	def playNextSong(self):
		# Can the voice client play the song
		if not self.canPlaySong():
			logging.info("Voice client can't play the song")
			return

		# List is empty
		if len(self.songList) == 0:
			logging.info("Can't play song, the list is empty")
			return

		# Get the next song Url
		songUrl = self.popSong()
		
		# Get file to download
		video = pafy.new(songUrl)
		bestaudio = video.getbestaudio()
		songFileName = "songfile"
		songFilePath = "./" + songFileName + "." + bestaudio.extension

		# Update current songFile
		songPlayer.currentSongFile = songFilePath

		# Delete file if already exists
		if os.path.isfile(songFilePath):
			logging.info("Deleting file")
			os.remove(songFilePath)

		# Download the file
		logging.info("Downloading file")
		bestaudio.download(songFilePath)

		# Play the song
		logging.info("Creating ffmpeg player")
		ffmpeg_error_log = open('./ffmpeg-log.log', 'w')
		self.currentPlayer = self.voiceClient.create_ffmpeg_player(songFilePath, after=songFinished, stderr=ffmpeg_error_log)
		
		# Set the volume
		self.currentPlayer.volume = self.volume

		logging.info("Starting player")
		self.currentPlayer.start()
		ffmpeg_error_log.close()

	# Called if an exception happens
	async def exception(self):
		# No player
		if self.currentPlayer == None:
			return

		# Stop the player
		self.stopPlayer()

		# Reconnect voice
		channel = self.voiceClient.channel
		await self.voiceClient.disconnect()
		self.voiceClient = await client.join_voice_channel(channel)

		self.playNextSong()

# Class for interacting with youtube
class Youtube:
	def __init__(self):
		pass

	# Filter to find the target video from the HTMl
	def filterResults(self, html_content):
		# Find the video ID
		search_results = re.findall(r'href=\"\/watch\?v=(.{11})', html_content)

		# Filter for the video
		alreadySearched = set()
		maxSearches = 6
		count = 0
		for url in search_results:
			# Already searched this video
			if url in alreadySearched:
				continue

			count += 1
			if count > maxSearches:
				break

			alreadySearched.add(url)
			video = pafy.new(url)	

			# ----------- FILTERS ------------
			# Video in the music category
			if video.category != "Music":
				continue

			return url

		# Didn't find any - return ""
		return ""

	# Return the video url from the video name
	def searchForVideo(self, videoName):
		# Get the HTML content from youtube
		query_string = urllib.parse.urlencode({"search_query" : videoName})
		html_object = urllib.request.urlopen("http://www.youtube.com/results?" + query_string)
		html_content = html_object.read().decode()

		# Filter for the desired results
		returnUrl = self.filterResults(html_content)

		# There are no results
		if returnUrl == "":
			logging.info("There were no Youtube results")
			return ""

		# Return the URL for the video
		return returnUrl

# Callback for when a song is done
def songFinished():
	# Check exception
	if songPlayer.exception == None:
		songPlayer.playNextSong()

# Globals
client = discord.Client()
youtube = Youtube()

configurationFilePath = "./res/configuration.json"
configuration = {}

songPlayer = SongPlayer()


@client.event
async def on_ready():
	print('Logged in as')
	print(client.user.name)
	print(client.user.id)
	print('----------')
	logging.info("Client is ready")

# Error handler for the discord client
@client.event
async def on_error(event, *args, **kwargs):
	logging.error(str(sys.exc_info()))

@client.event
async def on_message(message):

	# Get the message content
	content = message.content

	# Not a command
	if not content.startswith("!"):
		return

	# Get the command
	command = content.partition(' ')[0]
	
# --------------------------- BOT COMMANDS ------------------------------
	# Join a voice channel
	if command == "!join":
		global voiceClient

		words = content.split(' ')

		# Empty Name
		if len(words) == 1:
			return

		channelName = words[1]

		await songPlayer.updateChannel(channelName, message)


	# Add a song to the queue
	elif command == "!play":
		# Get the song name
		songNameWords = content.partition(' ')[1:]
		songName = " ".join(songNameWords)

		# Check for empty song name
		if songName == "":
			return

		# Get the Youtube URL
		songUrl = youtube.searchForVideo(songName)
		if songUrl == "":
			return

		# Add the URL to the songPlayer
		songPlayer.addSong(songUrl)

		# Try to play the song (works if no song is playing)
		songPlayer.playNextSong()

	# Print help message
	elif command == "!help":
		help_message = """
		Commands:
		!play [SONG NAME] - Play the song (searches YouTube).
		!skip - Skips the current song and starts playing the next.
		!join [CHANNEL NAME] - Move the bot to the voice channel (case sensitive)
		!volume [volume] - Set the music volume (Number between 0.0 - 2.0)
		!volume - Show the current music volume
		!pause - Pause the current song
		!resume - Resume the current song
		!help - Gives a list of commands
		!restart - Restarts the music bot (leave and join channel)
		"""
		await client.send_message(message.channel, help_message)

	# Skip the current song
	elif command == "!skip":
		await songPlayer.skipSong()	

	# Set the volume for the bot
	elif command == "!volume":
		volume = content.partition(' ')[2]

		# No volume found - report the volume
		if volume == "":
			botMessage = "Current Volume: " + str(songPlayer.volume)
			await client.send_message(message.channel, botMessage)
			return

		# Bad volume syntax
		volumeFloat = 0.0	
		try:
			volumeFloat = float(volume)
		except ValueError:
			botMessage = "Volume must be a number between 0.0 - 2.0"
			await client.send_message(message.channel, botMessage)
			return

		# Number out of range
		if not (0.0 <= volumeFloat <= 2.0):
			botMessage = "Volume must be a number between 0.0 - 2.0"
			await client.send_message(message.channel, botMessage)
			return

		# Update the volume
		songPlayer.updateVolume(volumeFloat)

	# Pause the current song
	elif command == "!pause":
		songPlayer.pause()

	# Resume the current song
	elif command == "!resume":
		songPlayer.resume()

	# Restart the client
	elif command == "!restart":
		restartClient()

	# Random Number
	elif command == "!roll":
		logging.info("Generating random number")
		number = content.partition(' ')[2]

		# Bad volume syntax
		numberInt = 0
		try:
			numberInt = int(number)
		except ValueError:
			botMessage = "Number must be an integer"
			await client.send_message(message.channel, botMessage)
			return

		randomNumber = random.randint(0, numberInt)
		author = message.author.name
		botMessage = str(author + ": " + str(randomNumber))
		await client.send_message(message.channel, botMessage)

	elif command.startswith("!"):
		help_message = """
		Type !help for a list of commands
		"""
		await client.send_message(message.channel, help_message)
		

# Load configuration file and decode JSON to a dictionary
def loadConfiguration(configurationFilePath):

	with open(configurationFilePath, 'r') as f:
		fileContents = f.read()
#		configuration = json.loads(fileContents)

def loadKey(client_key_path):
	with open(client_key_path, 'r') as f:
		key = f.read().split('\n')
		return key[0]

# Initialize logging
def loggingSetup(fileName):
	logPath = "./"
	logFile = logPath + fileName
	maxFileSizeBytes = 5*1024*1024

	logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
	rootLogger = logging.getLogger()

	# Log to file
	rotatingFileHandler = RotatingFileHandler(logFile, mode='a', maxBytes=maxFileSizeBytes, backupCount=2, encoding=None, delay=0)
	rotatingFileHandler.setFormatter(logFormatter)
	rootLogger.addHandler(rotatingFileHandler)

	# Log to console
	consoleHandler = logging.StreamHandler()
	consoleHandler.setFormatter(logFormatter)
	rootLogger.addHandler(consoleHandler)

	# Set the logging level
	rootLogger.setLevel(logging.INFO)

# Exception handler for the event loop
def exceptionHandler(loop, context):
	# Flag that an exception happened
	songPlayer.exception = Exception('Error playing song')

	typ, val, trace = sys.exc_info()
	logging.error("Handling Exception")
	logging.error(val)
	logging.error(context)

# Restart the discord client
async def restartClient():
	logging.info("Restarting Client")

	# Stop the player if it's playing
	songPlayer.stopPlayer()

	# Reconnect voice connection
	channel = songPlayer.voiceClient.channel
	await songPlayer.voiceClient.disconnect()
	await asyncio.sleep(0.5)
	songPlayer.voiceClient = await client.join_voice_channel(channel)

	# Clear the exception
	songPlayer.exception = None

	# Go to next song
	songPlayer.playNextSong()

# Periodically check for an exception
# If there is an exception, reset the voice client
async def exceptionCheck(delay):
	while True:
		if songPlayer.exception != None:
			await restartClient()
		await asyncio.sleep(delay)

# Main function
if __name__ == "__main__":
	# Set up logging
	loggingSetup(fileName="music_bot_log.log")

	# Load config file
	loadConfiguration(configurationFilePath)
	logging.info("Configuration Loaded")

	client_key_path = "./client.key"
	client_key = loadKey(client_key_path)
	client_key.strip()
	logging.info("Client Key Loaded")

	# Load OPUS library for voice
	opusLib = "/usr/lib/arm-linux-gnueabihf/libopus.so.0.5.3"
	try:
		discord.opus.load_opus(opusLib)
	except:
		logging.error("Error loading opusLib: " + sys.exc_info()[0])
	logging.info("Opus loaded")

	# Get the event loop and add exception handler
	loop = asyncio.get_event_loop()
	loop.set_exception_handler(exceptionHandler)

	# Start the application
	try:
		loop.run_until_complete(asyncio.gather(
			exceptionCheck(5),
			client.start(client_key),
		))
	except KeyboardInterrupt:
		loop.run_until_complete(client.logout())
	finally:
		loop.close()
