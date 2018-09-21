# Copyright (C) 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Sample that implements a gRPC client for the Google Assistant API."""
#time.sleep(5)
import concurrent.futures
import json
import logging
import os
import os.path
import pathlib2 as pathlib
import sys
import time
import uuid
import RPi.GPIO as GPIO
import wave
from threading import Thread
from multiprocessing import Process,Pipe
import serial
import cv2
import requests
import binascii
import TezCmd
import MPR121 as MPR121
####################################
import face_recognition as fr
import cv2
import sys
import pickle
from socketIO_client_nexus import SocketIO, LoggingNamespace

####################################
import click
import grpc
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials
#from scipy.io import wavfile as wf

from google.assistant.embedded.v1alpha2 import (
	embedded_assistant_pb2,
	embedded_assistant_pb2_grpc
)
from tenacity import retry, stop_after_attempt, retry_if_exception

try:
	from . import (
		assistant_helpers,
		audio_helpers,
		browser_helpers,
		device_helpers
	)
except (SystemError, ImportError,ValueError):
	import assistant_helpers
	import audio_helpers
	import browser_helpers
	import device_helpers


ASSISTANT_API_ENDPOINT = 'embeddedassistant.googleapis.com'
END_OF_UTTERANCE = embedded_assistant_pb2.AssistResponse.END_OF_UTTERANCE
DIALOG_FOLLOW_ON = embedded_assistant_pb2.DialogStateOut.DIALOG_FOLLOW_ON
CLOSE_MICROPHONE = embedded_assistant_pb2.DialogStateOut.CLOSE_MICROPHONE
PLAYING = embedded_assistant_pb2.ScreenOutConfig.PLAYING
DEFAULT_GRPC_DEADLINE = 60 * 3 + 5
GPIO.setmode(GPIO.BCM)
query="hi"
#set GPIO Pins
GPIO_TRIGGER = 23
GPIO_ECHO = 24
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)
resp_text=""
mute=True
startMouth=True
#~ num=""
beep=False
socket = SocketIO('127.0.0.1', 8000, LoggingNamespace)
faceFound=False
name2=[]
onceface=False
keyboard_on=False
class SampleAssistant(object):
	"""Sample Assistant that supports conversations and device actions.

	Args:
	  device_model_id: identifier of the device model.
	  device_id: identifier of the registered device instance.
	  conversation_stream(ConversationStream): audio stream
		for recording query and playing back assistant answer.
	  channel: authorized gRPC channel for connection to the
		Google Assistant API.
	  deadline_sec: gRPC deadline in seconds for Google Assistant API call.
	  device_handler: callback for device actions.
	"""

	def __init__(self, language_code, device_model_id, device_id,
				 conversation_stream, display,
				 channel, deadline_sec, device_handler):
		self.language_code = language_code
		self.device_model_id = device_model_id
		self.device_id = device_id
		self.conversation_stream = conversation_stream
		self.display = display

		# Opaque blob provided in AssistResponse that,
		# when provided in a follow-up AssistRequest,
		# gives the Assistant a context marker within the current state
		# of the multi-Assist()-RPC "conversation".
		# This value, along with MicrophoneMode, supports a more natural
		# "conversation" with the Assistant.
		self.conversation_state = None
		# Force reset of first conversation.
		self.is_new_conversation = True

		# Create Google Assistant API gRPC client.
		self.assistant = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(
			channel
		)
		self.deadline = deadline_sec

		self.device_handler = device_handler

	def __enter__(self):
		return self

	def __exit__(self, etype, e, traceback):
		if e:
			return False
		self.conversation_stream.close()

	def is_grpc_error_unavailable(e):
		is_grpc_error = isinstance(e, grpc.RpcError)
		if is_grpc_error and (e.code() == grpc.StatusCode.UNAVAILABLE):
			logging.error('grpc unavailable error: %s', e)
			return True
		return False

	@retry(reraise=True, stop=stop_after_attempt(3),
		   retry=retry_if_exception(is_grpc_error_unavailable))
	#a=0

						
		
	def assist(self):
		"""Send a voice request to the Assistant and playback the response.

		Returns: True if conversation should continue.
		"""
		user_query=""
		global updt_time,resp_text,mute,startMouth,mouthMove
		t2status=False
		def mouthMove():
		#~ global startMouth
			while True:
				#~ print "mouth"
				TezHead.SetMouth(0xFFF10E00)
				time.sleep(0.1)
				TezHead.SetMouth(0xFFF1F10E)
				time.sleep(0.1)
				TezHead.SetMouth(0xFFFF0E00)
				time.sleep(0.1)
				TezHead.SetMouth(0x00FF0000)
				time.sleep(0.1)
		t2 = Process(target=mouthMove)
		continue_conversation = True
		device_actions_futures = []

		self.conversation_stream.start_recording()
		logging.info('Recording audio request.')

		def iter_log_assist_requests():
			for c in self.gen_assist_requests():
				assistant_helpers.log_assist_request_without_audio(c)
				yield c
			logging.debug('Reached end of AssistRequest iteration.')

		# This generator yields AssistResponse proto messages
		# received from the gRPC Google Assistant API.
		for resp in self.assistant.Assist(iter_log_assist_requests(),
										  self.deadline):
			assistant_helpers.log_assist_response_without_audio(resp)
			if resp.event_type == END_OF_UTTERANCE:
				logging.info('End of audio request detected.')
				logging.info('Stopping recording.')
				self.conversation_stream.stop_recording()
				if mute==False and user_query!="":
					print user_query
					socket.emit('event-user-message',user_query)
				user_query=""

				
			if resp.speech_results:
				for r in resp.speech_results:
					user_query=r.transcript
				#~ for r in resp.speech_results:
					#~ user_query=r.transcript
					
			if len(resp.audio_out.audio_data) > 0 and mute==False:
				if not self.conversation_stream.playing:
					resp.dialog_state_out.supplemental_display_text
 
					self.conversation_stream.stop_recording()
					t2.start()
					t2status=True
					self.conversation_stream.start_playback()
					logging.info('Playing assistant response.')
					updt_time=time.time()
					

					#mouthMove(True)https://askubuntu.com/questions/895397/microphone-is-not-working-on-ubuntu-16-04
					mute=False
					
					#print text
				#wf.write("/home/pi/hello.wav",44100,resp.audio_out.audio_data)
				#print resp.audio_out.audio_data
				self.conversation_stream.write(resp.audio_out.audio_data)
				
			if resp.dialog_state_out.conversation_state:
				conversation_state = resp.dialog_state_out.conversation_state
				#DialogStateOut.supplemental_display_text()
				logging.debug('Updating convhttps://askubuntu.com/questions/895397/microphone-is-not-working-on-ubuntu-16-04ersation state.')
				self.conversation_state = conversation_state
			if resp.dialog_state_out.supplemental_display_text:
				resp_text=resp.dialog_state_out.supplemental_display_text
				updt_time=time.time()
							#updt_time=time.time()

				if mute==False:
					socket.emit('event-robot-message', resp_text)
					logging.info('Resp: %s',resp_text)

					
			if resp.dialog_state_out.volume_percentage != 0:
				volume_percentage = resp.dialog_state_out.volume_percentage
				logging.info('Setting volume to %s%%', volume_percentage)
				self.conversation_stream.volume_percentage = volume_percentage
			if resp.dialog_state_out.microphone_mode == DIALOG_FOLLOW_ON:
				continue_conversation = True
				logging.info('Expecting follow-on query from user.')
			elif resp.dialog_state_out.microphone_mode == CLOSE_MICROPHONE:
				continue_conversation = True
			if resp.device_action.device_request_json:
				device_request = json.loads(
					resp.device_action.device_request_json
				)
				fs = self.device_handler(device_request)
				if fs:
					device_actions_futures.extend(fs)
			if self.display and resp.screen_out.data:
				system_browser = browser_helpers.system_browser
				system_browser.display(resp.screen_out.data)

		if len(device_actions_futures):
			logging.info('Waiting for device executions to complete.')
			concurrent.futures.wait(device_actions_futures)

		if t2status==True:
			print "stopped"
			time.sleep(0.5)
			t2.terminate()
			TezHead.SetMouth(0x110E00)
		logging.info('Finished playing assistant response.')

		#mute=False
		self.conversation_stream.stop_playback()
		time.sleep(0.5)
		
		return continue_conversation

	def gen_assist_requests(self):
		"""Yields: AssistRequest messages to send to the API."""
		global query
		config = embedded_assistant_pb2.AssistConfig(
			audio_in_config=embedded_assistant_pb2.AudioInConfig(
				encoding='LINEAR16',
				sample_rate_hertz=self.conversation_stream.sample_rate,
			),
			audio_out_config=embedded_assistant_pb2.AudioOutConfig(
				encoding='LINEAR16',
				sample_rate_hertz=self.conversation_stream.sample_rate,
				volume_percentage=self.conversation_stream.volume_percentage,
			),
			dialog_state_in=embedded_assistant_pb2.DialogStateIn(
				language_code=self.language_code,
				conversation_state=self.conversation_state,
				is_new_conversation=self.is_new_conversation,
			),
			device_config=embedded_assistant_pb2.DeviceConfig(
				device_id=self.device_id,
				device_model_id=self.device_model_id,
			)
		)
		config1 = embedded_assistant_pb2.AssistConfig(
				audio_out_config=embedded_assistant_pb2.AudioOutConfig(
					encoding='LINEAR16',
					sample_rate_hertz=16000,
					volume_percentage=self.conversation_stream.volume_percentage,
				),
				dialog_state_in=embedded_assistant_pb2.DialogStateIn(
					language_code=self.language_code,
					conversation_state=self.conversation_state,
					is_new_conversation=self.is_new_conversation,
				),
				device_config=embedded_assistant_pb2.DeviceConfig(
					device_id=self.device_id,
					device_model_id=self.device_model_id,
				),
				text_query=query,
			)
		if self.display:
			config.screen_out_config.screen_mode = PLAYING
		# Continue current conversation with later requests.
		self.is_new_conversation = False
		# The first AssistRequest must contain the AssistConfig
		# and no audio data.
		print query
		if query=="audio":
			print "audio"
			yield embedded_assistant_pb2.AssistRequest(config=config)
			for data in self.conversation_stream:
##            Subsequent requests need audio data, but not config.
				yield embedded_assistant_pb2.AssistRequest(audio_in=data)
		else:
			yield embedded_assistant_pb2.AssistRequest(config=config1)

@click.command()
@click.option('--api-endpoint', default=ASSISTANT_API_ENDPOINT,
			  metavar='<api endpoint>', show_default=True,
			  help='Address of Google Assistant API service.')
@click.option('--credentials',
			  metavar='<credentials>', show_default=True,
			  default=os.path.join(click.get_app_dir('google-oauthlib-tool'),
								   'credentials.json'),
			  help='Path to read OAuth2 credentials.')
@click.option('--project-id',
			  metavar='<project id>',
			  help=('Google Developer Project ID used for registration '
					'if --device-id is not specified'))
@click.option('--device-model-id',
			  metavar='<device model id>',
			  help=(('Unique device model identifier, '
					 'if not specifed, it is read from --device-config')))
@click.option('--device-id',
			  metavar='<device id>',
			  help=(('Unique registered device instance identifier, '
					 'if not specified, it is read from --device-config, '
					 'if no device_config found: a new device is registered '
					 'using a unique id and a new device config is saved')))
@click.option('--device-config', show_default=True,
			  metavar='<device config>',
			  default=os.path.join(
				  click.get_app_dir('googlesamples-assistant'),
				  'device_config.json'),
			  help='Path to save and restore the device configuration')
@click.option('--lang', show_default=True,
			  metavar='<language code>',
			  default='en-IN',
			  help='Language code of the Assistant')
@click.option('--display', is_flag=True, default=False,
			  help='Enable visual display of Assistant responses in HTML.')
@click.option('--verbose', '-v', is_flag=True, default=False,
			  help='Verbose logging.')
@click.option('--input-audio-file', '-i',
			  metavar='<input file>',
			  help='Path to input audio file. '
			  'If missing, uses audio capture')
@click.option('--output-audio-file', '-o',
			  metavar='<output file>',
			  help='Path to output audio file. '
			  'If missing, uses audio playback')
@click.option('--audio-sample-rate',
			  default=audio_helpers.DEFAULT_AUDIO_SAMPLE_RATE,
			  metavar='<audio sample rate>', show_default=True,
			  help='Audio sample rate in hertz.')
@click.option('--audio-sample-width',
			  default=audio_helpers.DEFAULT_AUDIO_SAMPLE_WIDTH,
			  metavar='<audio sample width>', show_default=True,
			  help='Audio sample width in bytes.')
@click.option('--audio-iter-size',
			  default=audio_helpers.DEFAULT_AUDIO_ITER_SIZE,
			  metavar='<audio iter size>', show_default=True,
			  help='Size of each read during audio stream iteration in bytes.')
@click.option('--audio-block-size',
			  default=audio_helpers.DEFAULT_AUDIO_DEVICE_BLOCK_SIZE,
			  metavar='<audio block size>', show_default=True,
			  help=('Block size in bytes for each audio device '
					'read and write operation.'))
@click.option('--audio-flush-size',
			  default=audio_helpers.DEFAULT_AUDIO_DEVICE_FLUSH_SIZE,
			  metavar='<audio flush size>', show_default=True,
			  help=('Size of silence data in bytes written '
					'during flush operation'))
@click.option('--grpc-deadline', default=DEFAULT_GRPC_DEADLINE,
			  metavar='<grpc deadline>', show_default=True,
			  help='gRPC deadline in seconds')
@click.option('--once', default=False, is_flag=True,
			  help='Force termination after a single conversation.')


	
def main(api_endpoint, credentials, project_id,
		 device_model_id, device_id, device_config,
		 lang, display, verbose,
		 input_audio_file, output_audio_file,
		 audio_sample_rate, audio_sample_width,
		 audio_iter_size, audio_block_size, audio_flush_size,
		 grpc_deadline, once, *args, **kwargs):
	"""Samples for the Google Assistant API.

	Examples:
	  Run the sample with microphone input and speaker output:

		$ python -m googlesamples.assistant

	  Run the sample with file input and speaker output:

		$ python -m googlesamples.assistant -i <input file>

	  Run the sample with file input and output:

		$ python -m googlesamples.assistant -i <input file> -o <output file>
	"""
############################################################################3
	global updt_time,query,resp_text,mute,startmouth,TezHead,beep,faceFound,name2,onceface,facerec_en,keyboard_on

	# Setup logging.
	Kpx = 1
	Kpy = 1
	Ksp = 40

	## Head X and Y angle limits
	time.sleep(5)
	Xmax = 725
	Xmin = 290
	Ymax = 550
	Ymin = 420
	keyboard_on=False
	## Initial Head position

	Xcoor = 511
	Ycoor = 450
	Facedet = 0

	## Time head wait turned
	touch_wait = 2

	no_face_tm = time.time()
	face_det_tm = time.time()
	last_face_det_tm = time.time()
	touch_tm = 0
	touch_samp = time.time()
	qbo_touch = 0
	touch_det = False
	face_not_found_idx = 0
	mutex_wait_touch = False
	faceFound = False
	onceface=False
	dist=100
	audio_response1 = '/home/pi/Reebo_Python/up.wav'
	wavep = wave.open(audio_response1, 'rb')
	audio_response2 = '/home/pi/Reebo_Python/HiTej.wav'
	wavep2 = wave.open(audio_response2, 'rb')
	facerec_en=False

############################################################################3
	logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

	# Load OAuth 2.0 credentials.
	try:
		with open(credentials, 'r') as f:
			credentials = google.oauth2.credentials.Credentials(token=None,
																**json.load(f))
			http_request = google.auth.transport.requests.Request()
			credentials.refresh(http_request)
	except Exception as e:
		logging.error('Error loading credentials: %s', e)
		logging.error('Run google-oauthlib-tool to initialize '
					  'new OAuth 2.0 credentials.')
		sys.exit(-1)

	# Create an authorized gRPC channel.
	grpc_channel = google.auth.transport.grpc.secure_authorized_channel(
		credentials, http_request, api_endpoint)
	logging.info('Connecting to %s', api_endpoint)

	# Configure audio source and sink.
	audio_device = None
	if input_audio_file:
		audio_source = audio_helpers.WaveSource(
			open(input_audio_file, 'rb'),
			sample_rate=audio_sample_rate,
			sample_width=audio_sample_width
		)
	else:
		audio_source = audio_device = (
			audio_device or audio_helpers.SoundDeviceStream(
				sample_rate=audio_sample_rate,
				sample_width=audio_sample_width,
				block_size=audio_block_size,
				flush_size=audio_flush_size
			)
		)
	if output_audio_file:
		audio_sink = audio_helpers.WaveSink(
			open(output_audio_file, 'wb'),
			sample_rate=audio_sample_rate,
			sample_width=audio_sample_width
		)
	else:
		audio_sink = audio_device = (
			audio_device or audio_helpers.SoundDeviceStream(
				sample_rate=audio_sample_rate,
				sample_width=audio_sample_width,
				block_size=audio_block_size,
				flush_size=audio_flush_size
			)
		)
	# Create conversation stream with the given audio source and sink.
	conversation_stream = audio_helpers.ConversationStream(
		source=audio_source,
		sink=audio_sink,
		iter_size=audio_iter_size,
		sample_width=audio_sample_width,
	)

	if not device_id or not device_model_id:
		try:
			with open(device_config) as f:
				device = json.load(f)
				device_id = device['id']
				device_model_id = device['model_id']
				logging.info("Using device model %s and device id %s",
							 device_model_id,
							 device_id)
		except Exception as e:
			logging.warning('Device config not found: %s' % e)
			logging.info('Registering device')
			if not device_model_id:
				logging.error('Option --device-model-id required '
							  'when registering a device instance.')
				sys.exit(-1)
			if not project_id:
				logging.error('Option --project-id required '
							  'when registering a device instance.')
				sys.exit(-1)
			device_base_url = (
				'https://%s/v1alphapi@raspber2/projects/%s/devices' % (api_endpoint,
															 project_id)
			)
			device_id = str(uuid.uuid1())
			payload = {
				'id': device_id,
				'model_id': device_model_id,
				'client_type': 'SDK_SERVICE'
			}
			session = google.auth.transport.requests.AuthorizedSession(
				credentials
			)
			r = session.post(device_base_url, data=json.dumps(payload))
			if r.status_code != 200:
				logging.error('Failed to register device: %s', r.text)
				sys.exit(-1)
			logging.info('Device registered: %s', device_id)
			pathlib.Path(os.path.dirname(device_config)).mkdir(exist_ok=True)
			with open(device_config, 'w') as f:
				json.dump(payload, f)

	device_handler = device_helpers.DeviceRequestHandler(device_id)

	@device_handler.command('action.devices.commands.OnOff')
	def onoff(on):
		if on:
			logging.info('Turning device on')
		else:
			logging.info('Turning device off')

	@device_handler.command('com.example.commands.BlinkLight')
	def blink(speed, number):
		logging.info('Blinking device %s times.' % number)
		delay = 1
		if speed == "slowly":
			delay = 2
		elif speed == "quickly":
			delay = 0.5
		for i in range(int(number)):
			logging.info('Device is blinking.')
			time.sleep(delay)
	#~ def findquery():
	
	

		
	#############################   FACEREC THREAD     ##################################################33
	def facerec():
		
		global name2
		
		f=open("/home/pi/Reebo_Python/face_features.pkl",'rb')
		details=pickle.load(f)
		
		# Initialize some variables
		face_locations = []
		face_encodings = []
		face_names = []
		name2= []
		unknown_picture = fr.load_image_file("/home/pi/Reebo_Python/test.jpg")

		# Grab a single frame of video
		# frame = unknown_picture

		# Resize frame of video to 1/4 size for faster face recognition processing
		# small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

		# Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
		# rgb_small_frame = small_frame[:, :, ::-1]

		# Find all the faces and face encodings in the current frame of video
		face_locations = fr.face_locations(unknown_picture)
		face_encodings = fr.face_encodings(unknown_picture, face_locations)

		print("{0} persons identified".format(len(face_locations)))

		face_names = []
		for face_encoding in face_encodings:
			matches = fr.compare_faces(details['encodings'], face_encoding,0.45)
			name = "Unknown"

			# If a match was found in known_face_encodings, just use the first one.
			if True in matches:
				first_match_index = matches.index(True)
				name = details["name"][first_match_index]

			face_names.append(name)

	
		print(face_names)
		for i in range(0,len(face_names)):
			
			name_temp=str(face_names[i]).replace('photos/',"")
			name_temp=str(name_temp).replace(']\'',"")
			name2.append(str(name_temp))
		print name2
		n=open("/home/pi/Reebo_Python/names.txt",'w')
		for i in face_names:
			n.write(i+"\n")

		n.close()

		for (top,right,bottom,left),name in zip(face_locations,face_names):
			if not name:
				continue
			if name=="warner":
				cv2.rectangle(unknown_picture, (left, top), (right, bottom), (255, 0, 0), 2)
				cv2.rectangle(unknown_picture, (left, bottom - 25), (right, bottom), (255, 0, 0), 1)
				font = cv2.FONT_HERSHEY_DUPLEX
				cv2.putText(unknown_picture, name, (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)
			else:
				cv2.rectangle(unknown_picture, (left, top), (right, bottom), (0, 0, 255), 2)
				cv2.rectangle(unknown_picture, (left, bottom - 25), (right, bottom), (0, 0, 255),1)
				font = cv2.FONT_HERSHEY_DUPLEX
				cv2.putText(unknown_picture, name, (left + 6, bottom - 6), font, 0.5, (255, 255, 255), 1)
			cv2.imwrite("/home/pi/Reebo_Python/result.png",unknown_picture)	
			
				
	def findFace():
		global name2,faceFound,onceface,facerec_en,updt_time
		found_tm=time.time()
		onceface=False
		touch_samp=time.time()
		Xmax = 725
		Xmin = 290
		Ymax = 550
		Ymin = 420
		qbo_touch= 0

		while True :
			#print("find face " + str(time.time()))
			try:
				
				faceFound = False
			#    while not faceFound :
					   # This variable is set to true if, on THIS loop a face has already been found
										# We search for a face three diffrent ways, and if we have found one already-
										# there is no reason to keep looking.
				#thread.start_new_thread(WaitForSpeech, ())
			#	WaitForSpeech()
			#    ServoHome()
				Cface = [0,0]
				t_ini = time.time()
				while time.time()-t_ini < 0.01: # wait for present frame
					t_ini = time.time()
					aframe = webcam.read()[1]           #print "t: " + str(time.time()-t_ini)
				
				fface = frontalface.detectMultiScale( aframe,1.3,4,(cv2.cv.CV_HAAR_DO_CANNY_PRUNING + cv2.cv.CV_HAAR_FIND_BIGGEST_OBJECT + cv2.cv.CV_HAAR_DO_ROUGH_SEARCH),(60,60))
				pfacer = profileface.detectMultiScale( aframe,1.3,4,(cv2.cv.CV_HAAR_DO_CANNY_PRUNING + cv2.cv.CV_HAAR_FIND_BIGGEST_OBJECT + cv2.cv.CV_HAAR_DO_ROUGH_SEARCH),(80,80))
				if  fface != ():                 # if we found a frontal face...
						for f in  fface:         # f in fface is an array with a rectangle representing a face
								 faceFound = True
								 face = f
								
				elif  pfacer != ():                # if we found a profile face...
						for f in  pfacer:
								 faceFound = True
								 face = f
								   
				if  faceFound:
						updt_time=time.time()
						#facerec()
						if onceface==False:
							cv2.imwrite("/home/pi/Reebo_Python/test.jpg",aframe)
							
							onceface=True
						found_tm=time.time()
						x,y,w,h =  face
						Cface = [(w/2+x),(h/2+y)]       # we are given an x,y corner point and a width and height, we need the center
						TezHead.SetNoseColor(4)
						#print "face ccord: " + str(Cface[0]) + "," + str(Cface[1])
						faceOffset_X = 160 -  Cface[0]
						if (faceOffset_X > 20) | (faceOffset_X < -20):
								time.sleep(0.002)                    
								# acquire mutex
								TezHead.SetAngleRelative(1, faceOffset_X >> 1 )
								# release mutex
								#wait for move
								time.sleep(0.05)
								#print "MOVE REL X: " + str(faceOffset_X >> 1)
						faceOffset_Y =  Cface[1] - 120
						if (faceOffset_Y > 20) | (faceOffset_Y < -20):
								time.sleep(0.002)
								# acquire mutex
								TezHead.SetAngleRelative(2, faceOffset_Y >> 1 )
								# release mutex
								#wait for move
								time.sleep(0.05)
				if time.time()-found_tm>0.5:
					TezHead.SetNoseColor(0)
					
				
			except Exception as e:
				print e
				pass
			try:
				current_touched = cap.touched()
				#last_touched = cap.touched()
				cap.set_thresholds(10,6)
				# Check each pin's last and current state to see if it was pressed or released.
				i=0
				for i in [1,11]:
					pin_bit = 1 << i
					# Each pin is represented by a bit in the touched value.  A value of 1
					# First check if transitioned from not touched to touched.
					if current_touched & pin_bit : #and not last_touched & pin_bit:
						print('{0} touched!'.format(i))
						qbo_touch= int(i)
			##            # Next check if transitioned from touched to not touched.
			##            if not current_touched & pin_bit and last_touched & pin_bit:
			##                print('{0} released!'.format(i))
			##        # Update last state and wait a short period before repeating.
			##        last_touched = current_touched
				#time.sleep(0.1)
			except :
				#print sys.exc_info()
				#print "error"
				pass
				
			if (time.time() - touch_samp > 0.5): # & (time.time() - last_face_det_tm > 3):
				touch_samp = time.time()
				#~ time.sleep(0.002)
				if qbo_touch in [1,11]:
						if qbo_touch == 1:
								print("right")
								TezHead.SetServo(1, Xmax - 50, 100)
								time.sleep(0.002)
								TezHead.SetServo(2, Ymin - 5, 100)
								#thread.start_new_thread(WaitTouchMove, ())
								# wait for begin touch move.
								time.sleep(1)
								qbo_touch=0
						elif qbo_touch == [2]:
								#~ time.sleep(0.002)
								TezHead.SetServo(2, Ymin - 5, 100)
								thread.start_new_thread(WaitTouchMove, ())
								# wait for begin touch move.
								time.sleep(1)
								qbo_touch=0

						elif qbo_touch == 11:
								print("left")
								TezHead.SetServo(1, Xmin + 50, 100)
								time.sleep(0.002)
								TezHead.SetServo(2, Ymin - 5, 100)
								#thread.start_new_thread(WaitTouchMove, ())
								# wait for begin touch move.
								time.sleep(1)
								qbo_touch=0


	def distance():
		# set Trigger to HIGH
		GPIO.output(GPIO_TRIGGER, True)
	 
		# set Trigger after 0.01ms to LOW
		time.sleep(0.00001)
		GPIO.output(GPIO_TRIGGER, False)
	 
		StartTime = time.time()
		StopTime = time.time()
	 
		# save StartTime
		while GPIO.input(GPIO_ECHO) == 0:
			StartTime = time.time()
	 
		# save time of arrival
		while GPIO.input(GPIO_ECHO) == 1:
			StopTime = time.time()
	 
		# time difference between start and arrival
		TimeElapsed = StopTime - StartTime
		# multiply with the sonic speed (34300 cm/s)
		# and divide by 2, because there and back
		distance = (TimeElapsed * 34300) / 2
		 
		return distance
		##################################  SOCKET THREAD   ######################################################
	def socket_thread(conn):
		
		print 'Socket.IO Thread Started.'
	
		def empid_received():
			socket.emit('event-ask-cardno')
			print "ASK CARD NO"
		def cardno_received():
			print "Card No received"
			conn.send(False)
			
		socket.on('event-empid-received',empid_received)
		socket.on('event-cardno-received',cardno_received)
		socket.wait()
			
		
	def findquery(parent_conn):
		global resp_text,mute,query,beep
		keyboard_on=False
		if resp_text=="Sorry, I can't help.":
			query="Talk to Reebo"
			mute=True
		elif resp_text=="Alright! Say Cheese!":
			print "camera"
			aframe=webcam.read()[1]
			cv2.imwrite("/home/pi/reebo-backend/selfie.jpg",aframe)
			socket.emit('event-take-selfie')
			#mute=False

		elif resp_text.startswith("Can you please smile for the camera?"):
			mute=False
			beep=False
			print "BEEP"
			time.sleep(5)
			aframe=webcam.read()[1]
			cv2.imwrite("/home/pi/reebo-backend/selfie.jpg",aframe)
			socket.emit('event-take-selfie')
			query="Say@#$: Thank you. Please enter your employee ID and card number"
			assistant.assist()
			socket.emit('event-ask-empid')
			keyboard_on=True
			print "KEYBOARD in findquery: ",keyboard_on
			keyboard_on=parent_conn.recv()
			query="Say@#$: Thank You. You will be granted access shortly"
			mute=False
			beep=False
	if len(sys.argv) > 1:
			port = sys.argv[1]
	else:
			port = '/dev/serial0'

	try:
			# Open serial port
			ser = serial.Serial(port, baudrate=115200, bytesize = serial.EIGHTBITS, stopbits = serial.STOPBITS_ONE, parity = serial.PARITY_NONE, rtscts = False, dsrdtr =False, timeout = 0)
			print "Open serial port sucessfully."
			print(ser.name)
	except Exception as e:
			print e
			print "Error opening serial port."
			sys.exit()

	try :
		cap = MPR121.MPR121()
		time.sleep(3)
		#
		if not cap.begin():
			print('Error initializing MPR121.  Check your wiring!')
	except Exception as e:
		print(e)
		pass
		
	TezHead = TezCmd.Controller(ser)
	TezHead.SetMouth(0x110E00)

	time.sleep(1)
	#TezHead.SetPid(1, 26, 12, 16)
	TezHead.SetPid(1, 26, 2, 16)

	#TezHead.SetPid(2, 26, 12, 16)
	TezHead.SetPid(2, 26, 2, 16)
	time.sleep(1)
	TezHead.SetServo(1, Xcoor, 100)
	TezHead.SetServo(2, Ycoor, 100)
	time.sleep(1)
	TezHead.SetNoseColor(0)



	webcam = cv2.VideoCapture(-1)				# Get ready to start getting images from the webcam
	webcam.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 320)		# I have found this to be about the highest-
	webcam.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 240)	# resolution you'll want to attempt on the pi
	#webcam.set(cv2.CV_CAP_PROP_BUFFERSIZE, 2)		# frame buffer storage

	if not webcam:
		print "Error opening WebCAM"
		sys.exit(1)
		
	#open = False

	frontalface = cv2.CascadeClassifier("/home/pi/Documents/Python projects/haarcascade_frontalface_alt2.xml")		# frontal face pattern detection
	profileface = cv2.CascadeClassifier("/home/pi/Documents/Python projects/haarcascade_profileface.xml")		# side face pattern detection
	#parent_conn, child_conn = Pipe()
	
	t1 = Thread(target=findFace)
	t1.start()
	t3 = Thread(target=facerec)
	parent_conn, child_conn = Pipe()
	socket_thd = Thread(target=socket_thread, args=(child_conn,))
	socket_thd.start()
			
	with SampleAssistant(lang, device_model_id, device_id,
						 conversation_stream, display,
						 grpc_channel, grpc_deadline,
						 device_handler) as assistant:
		# If file arguments are supplied:
		# exit after the first turn of the conversation.
		if input_audio_file or output_audio_file:
			assistant.assist()
			return

		# If no file arguments supplied:
		# keep recording voice requests using the microphone
		# and playing back assistant response using the speaker.
		# When the once flag is set, don't wait for a trigger. Otherwise, wait.
		wait_for_user_trigger = not once
		button_once=False
		#playsound('/home/pi/env/HiTej.wav')
		print "playsound"
		mute=True
		query="Talk to Reebo"
		print query
	#################################################################################3
		#~ query,mute=findquery()
	#####################################FIND QUERY AND MUTE#####################3
		assistant.assist()
		mute=False
		query="audio"
		time.sleep(1)
		updt_time=time.time()
		stream=conversation_stream
		num_frames = wavep.getnframes() # number of frames in audio response file
		resp_samples = wavep.readframes(num_frames) # get frames from wav file
		num_frames2 = wavep2.getnframes() # number of frames in audio response file
		resp_samples2 = wavep2.readframes(num_frames2) # get frames from wav file
		name=""
		while True:
			#if wait_for_user_trigger:
			
				#logging.info('Press key')
				#x=raw_input()
			#~ stream.start_recording() # unelegant method to access private methods..
			
			findquery(parent_conn)
			if mute==False or beep==True:
				print "beep"
				stream.start_playback()
				#~ stream.stop_recording()
				stream.write(resp_samples) # write response sample to output stream
				print "HI"
				stream.stop_playback()

			assistant.assist()
			beep=False
			query="audio"
			mute=False
			#updt_time=time.time()
			print time.time()-updt_time
			dist=distance()
			#~ if dist<50:
				#~ print dist
				#~ updt_time=time.time()
			if time.time()-updt_time>10:
				name2=""
				if onceface==True:
					facerec_en=False
					print "Thread Status" , t3.is_alive()
					if t3.is_alive():
						t3.terminate()
						t3.join(1)
						print "t3 terminated"
					print facerec_en
					onceface=False
				print("in loop")
				query="audio"
				dist=distance()
				print faceFound
				while faceFound==False:
					time.sleep(0.1)
					#print "FACE FALSE"
				#~ if dist>60:
					#~ #mute=False
					#~ updt_time=time.time()
					#~ print query
					#~ while dist>60:
						#~ dist=distance()
						#~ time.sleep(0.1)
						#~ print dist
					#~ query="Hi"
					#~ print query
					#~ assistant.assist()
					#~ print ("playback")
					#~ socket.emit('event-robot-message',"Hi! Do you want some help ?")
				print "Thread Status" , t3.is_alive()
				t3 = Thread(target=facerec)
				t3.start()

				#~ query="Talk to Tej"
				#~ mute=True
				#~ assistant.assist()
				#time.sleep(3)
				stream.start_playback()
				#~ stream.stop_recording()
				stream.write(resp_samples2) # write response sample to output stream
				socket.emit('event-robot-message',"Hi! My Name is Reebo. I\'ll be your personal assistant for today")
				stream.stop_playback()
				query="Say:@#$: "
				if len(name2)>=1:
					for i in range(0,len(name2)):
						if name2[i]!="" and name2[i]!="Unknown":
							query=query+" Hi "+str(name2[i]) + "!"
				
				query=query + "What can I do for you?"
				mute=False
				print query
				assistant.assist()
				#time.sleep(0.1)
				#~ stream.start_playback()
				#~ stream.stop_recording()
				#~ stream.write(resp_samples2) # write response sample to output stream
				#~ stream.stop_playback()
				#~ #query="Talk to Tej"
				#~ mute=True
				#~ assistant.assist()
				
				#~ updt_time= time.time()
				query="audio"
				mute=False
				

# Socket Thread



if __name__ == '__main__':
	main()



