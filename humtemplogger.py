#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  humtemplogger.py
#  
#  Copyright 2025  <kevin@raspberrypi>
#
#  Author:  Jason P. Meyers
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

import os
import time
import adafruit_dht
import board
from statistics import mean

class InvalidPinError(Exception):
	""" Error for requesting an invalud data pin """
	
	def __init__(self, message):
		self.message = message
		super().__init__(self.message)

class Sensor:
	
	def __init__(self, gpio, devID=None):
		# Figure out which pin the sensor is connected to
		gpio = int(gpio)
		if gpio >= 0 and gpio <= 27:
			pin_name = f'board.D{gpio}'
			
			# The next line is bad and potentially unsafe coding but I don't know of
			# a better way of doing this.  It would be best to eliminate the need for
			# the eval function call.
			pin = eval(pin_name)
			self.pin = gpio
		else:
			raise InvalidPinError('Invalid pin number.  Must be between 0 and 27')
			
		self.sensor = adafruit_dht.DHT22(pin)
		
		if devID is None:
			# if no device id is given, use the pin name
			self.devID = pin_name
		else:
			self.devID = devID
		
		# set a flag to indicate an error ocurred while reading the sensor
		self.error = False
		self.error_message = None
		
		# Make the first reading of the sensor
		self.poll()
	
	def exit(self):
		# close out the sensor
		self.sensor.exit()

	def poll(self):
		# try to read the sensor
		try:
			self.temp = self.sensor.temperature
			self.humidity = self.sensor.humidity
		except RuntimeError as err:
			# clear any existing values
			self.temp = None
			self.humidity = None
			
			#set the error flag and store the error message
			self.error = True
			self.error_message = err

	def get_tempf(self):
		if self.temp:
			result = self.temp * ( 9.0 / 5.0) + 32.0
		else:
			result = self.temp
		
		return result

	def get_tempc(self):
		return self.temp
	
	def get_humidity(self):
		return self.humidity
	
	def get_error(self):
		# reset the rror flag
		self.error = False
		result = self.error_message
		self.error_message = None
		return result


class Logger:
	
	def __init__(self, sensor, logfile):
		# sensor is an instance of the Sensor class used to get readings
		self.sensor = sensor
		
		# logfile is the file to write the readings to
		self.datafile = logfile
		
		# create a lists to store the samples
		self.tempc = []
		self.tempf = []
		self.humidity = []
		
		# create storage for error messages
		self.error_message = ''

		# This is where we will open the data file for writing
		try:
			self.f = open(logfile, 'a+')
			if os.stat(logfile).st_size == 0:
					self.f.write('Device ID, Date, Time, Temperature C, Temperature F, Humidity, Errors\r\n')
		except:
			# I don't like this silent killing of any OS file open errors
			pass

	def __del__(self):
		# close things up
		self.f.close()
	
	def read_sensor(self):
		# request a reading
		self.sensor.poll()
		
		# if no errors detected, add readings to the samples
		if not self.sensor.error:
			self.tempc.append(self.sensor.get_tempc())
			self.tempf.append(self.sensor.get_tempf())
			self.humidity.append(self.sensor.get_humidity())
		else:
			# this line is needed to clear any detected errors
			# currently we don't do anything with the errors other
			# than storing them locally for future use
			self.error_message = self.sensor.get_error()
	
	def average_samples(self, samples):
		# calculate the mean of the list of samples
		# returns nan if sample size is zero
		if len(samples) > 0:
			# print(samples, end="   ")
			# print(mean(samples))
			return mean(samples)
		else:
			return float('nan')

	def log_data(self):
		# averages the samples and wrotes the data to the log file
		tempc = self.average_samples(self.tempc)
		tempf = self.average_samples(self.tempf)
		humidity = self.average_samples(self.humidity)
		
		# write the data
		# print('attempting to write:')
		# print(f"{self.sensor.devID}, {time.strftime('%m/%d/%y')}, {time.strftime('%H:%M:%S')}, {tempc}, {tempf}, {humidity}%\r\n")
		self.f.write(f"{self.sensor.devID}, {time.strftime('%m/%d/%y')}, {time.strftime('%H:%M:%S')}, {tempc}, {tempf}, {humidity}%\r\n")
		# print('done attempting to write.')
			
		# flush the write buffer
		self.f.flush()
		

def main(args):
	# args contins a list of strings of the command line used to start the program
	# print(args)
	
	# do a simple check for a help message request
	if len(args) > 1 and (args[1] == '--help' or args[1] == '-h'):
		print('humtemplogger ussage:  humtemplogger [datafile_prefix [pin numbers...]]')
		print('example:  humtemplogger beehive_1 4 17')
		
		# exit the program
		return 0
	
	# grap the log filename prefix from args if it exists
	if len(args) > 1:
		logfile_prefix = args[1]
	else:
		# set up the default filename
		logfile_prefix = 'humtemp'
		print(f'no data file specified, using default value:  {logfile}')

	# create a list of loggers for each sensor
	loggers = []
	
	# check to see if pins were specified on the command line
	if len(args) > 2:
		for i in range(2, len(args)):
			try:
				# TODO: add ability to specify the device ID
				sen = Sensor(args[i])
				logfile = logfile_prefix + '_' + sen.devID + '.csv'
				loggers.append(Logger(sen, logfile))

			except InvalidPinError as err:
				print(err)
				print(f'skipping pin #{args[i]}')
	else:
		# set up the default configuration
		print(f'no gpio data pins specified, using default value:  4')
		logfile = logfile_prefix + '_' + sen.devID + '.csv'
		loggers.append(Logger(sen, logfile))

	# This is for testing purposes only.
	# Create some kind of mechanism to control how long the data logging happens.
	readings = 5
	while readings > 0:

		samples = 10
		while samples > 0:
			# use the loggers to read the data
			for logger in loggers:
				logger.read_sensor()
			
			# show progress
			print(f'reading:  {readings}, sample #{samples}   \r', end="")

			# decrement the counter
			samples -= 1
			
			# Add flexibility by allowing the user to specify the sampling rate
			# currently it is hard coded for 1 second between sample reads
			time.sleep(1)
			
		# write out the data from the loggers
		for logger in loggers:
			logger.log_data()
		
		# decrement the counter
		readings -= 1

	# cleanup
	for logger in loggers:
		del logger

	return 0

if __name__ == '__main__':
	import sys
	sys.exit(main(sys.argv))
