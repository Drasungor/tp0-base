from io import TextIOWrapper
import socket
import time
import datetime
import logging
import common.constants as constants
import signal
import multiprocessing as mp

""" Winners storage location. """
STORAGE = "./winners"


class FileWriterStatus:
	def __init__(self, winners_queue):
		self.winners_queue: mp.Queue = winners_queue
		self.file: TextIOWrapper = None
		signal.signal(signal.SIGTERM, self.free_resources)

	def add_file(self, file):
		self.file = file

	def remove_file(self):
		self.file = None

	def free_resources(self, *args):
		self.winners_queue.close()
		self.winners_queue.join_thread()
		logging.info("Closed file writer process queue")
		if (not (self.file is None)):
			self.file.close()

""" Contestant data model. """
class Contestant:
	def __init__(self, first_name, last_name, document, birthdate):
		""" Birthdate must be passed with format: 'YYYY-MM-DD'. """
		self.first_name = first_name
		self.last_name = last_name
		self.document = document
		self.birthdate = datetime.datetime.strptime(birthdate, '%Y-%m-%d')
		
	def __hash__(self):
		return hash((self.first_name, self.last_name, self.document, self.birthdate))


""" Checks whether a contestant is a winner or not. """
def is_winner(contestant: Contestant) -> bool:
	# Simulate strong computation requirements using a sleep to increase function retention and force concurrency.
	time.sleep(0.001)
	return hash(contestant) % 17 == 0

""" Persist the information of each winner in the STORAGE file. Not thread-safe/process-safe. """
def persist_winners(status_manager: FileWriterStatus, winners: "list[Contestant]") -> None:
	with open(STORAGE, 'a+') as file:
		status_manager.add_file(file)
		for winner in winners:
			file.write(f'Full name: {winner.first_name} {winner.last_name} | Document: {winner.document} | Date of Birth: {winner.birthdate.strftime("%d/%m/%Y")}\n')
		status_manager.remove_file()

def update_winners_file(winners_queue: mp.Queue):
	status_manager = FileWriterStatus(winners_queue)
	received_message = winners_queue.get()
	while received_message != None:
		persist_winners(status_manager, received_message)
		received_message = winners_queue.get()
	winners_queue.close()
	winners_queue.join_thread()


class ClosedSocket(Exception):
	pass

class ClientSocket:
	def __init__(self, socket: socket):
		self.socket = socket

	def __send_normal_message_code(self):
		self.socket.sendall(constants.normal_message_code.to_bytes(constants.message_code_bytes_amount, "big"))

	def __send_error_message_code(self):
		self.socket.sendall(constants.error_message_code.to_bytes(constants.message_code_bytes_amount, "big"))

	def __read_message_code(self):
		return int.from_bytes(self.__recv_all(constants.message_type_code_bytes_amount), "big")

	def __recv_all(self, bytes_amount: int):
		total_received_bytes = b''
		while (len(total_received_bytes) < bytes_amount):
			received_bytes = self.socket.recv(bytes_amount - len(total_received_bytes))
			if (len(received_bytes) == 0):
				raise ClosedSocket
			total_received_bytes += received_bytes
		return total_received_bytes

	def __read_string(self):
		string_length = int.from_bytes(self.__recv_all(constants.attributes_length_bytes_amount), "big")
		return self.__recv_all(string_length).decode()

	def __send_string(self, message: str):
		# string_bytes = bytes(message, "utf8")
		string_bytes = message.encode()
		self.socket.sendall(len(string_bytes).to_bytes(constants.attributes_length_bytes_amount, "big"))
		self.socket.sendall(string_bytes)

	def send_lottery_result(self, user_won: bool):
		number_to_send = 0
		if (user_won):
			number_to_send = 1
		self.__send_normal_message_code()
		self.socket.sendall(number_to_send.to_bytes(constants.bool_bytes_amount, "big"))

	def recv_contestants(self) -> "list[Contestant]":
		received_contestants = []
		if (self.__read_message_code() != constants.normal_message_code):
			raise Exception(f"Error received: {self.__read_string()}")
		read_number = int.from_bytes(self.__recv_all(constants.attributes_length_bytes_amount), "big")
		while (read_number != constants.last_participant_delimiter):
			first_name = self.__recv_all(read_number).decode()
			last_name = self.__read_string()
			document = self.__read_string()
			birthdate = self.__read_string()
			received_contestants.append(Contestant(first_name, last_name, document, birthdate))
			read_number = int.from_bytes(self.__recv_all(constants.attributes_length_bytes_amount), "big")
		return received_contestants

	def send_contestants(self, contestants: "list[Contestant]"):
		self.__send_normal_message_code()
		for contestant in contestants:
			self.__send_string(contestant.first_name)
			self.__send_string(contestant.last_name)
			self.__send_string(contestant.document)
			self.__send_string(str(contestant.birthdate.date()))
		self.socket.sendall(constants.last_participant_delimiter.to_bytes(constants.attributes_length_bytes_amount, "big"))


	def send_error_message(self, message: str):
		self.__send_error_message_code()
		self.__send_string(message)

	def close(self):
		self.socket.close()

# Protocol:

# message_type_code: 0 (normal code) or 1 (error code), 1 byte

# if error code: 4 bytes big endian number depicting message length, followed by that number of string bytes encoded in utf8
# if normal code: message that has to be sent depending on the conversation that is being had at the moment