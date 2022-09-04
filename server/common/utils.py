import socket
import time
import datetime
import common.constants as constants

""" Winners storage location. """
STORAGE = "./winners"


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
def persist_winners(winners: list[Contestant]) -> None:
	with open(STORAGE, 'a+') as file:
		for winner in winners:
			file.write(f'Full name: {winner.first_name} {winner.last_name} | Document: {winner.document} | Date of Birth: {winner.birthdate.strftime("%d/%m/%Y")}\n')

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
		received_bytes = b''
		while (len(received_bytes) < bytes_amount):
			received_bytes = self.socket.recv(bytes_amount - len(received_bytes))
		return received_bytes

	def __read_string(self):
		string_length = int.from_bytes(self.__recv_all(constants.attributes_length_bytes_amount), "big")
		return self.__recv_all(string_length).decode()

	def __send_string(self, message: str):
		string_bytes = bytes(message, "utf8")
		self.socket.sendall(len(string_bytes).to_bytes(constants.attributes_length_bytes_amount, "big"))
		self.socket.sendall(string_bytes)

	def send_lottery_result(self, user_won: bool):
		number_to_send = 0
		if (user_won):
			number_to_send = 1
		self.__send_normal_message_code()
		self.socket.sendall(number_to_send.to_bytes(constants.bool_bytes_amount, "big"))


	def recv_contestant(self) -> Contestant:
		if (self.__read_message_code() != constants.normal_message_code):
			raise Exception(f"Error received: {self.__read_string()}")
		first_name = self.__read_string()
		last_name = self.__read_string()
		document = self.__read_string()
		birthdate = self.__read_string()
		return Contestant(first_name, last_name, document, birthdate)

	def send_error_message(self, message: str):
		self.__send_error_message_code()
		self.__send_string(message)

	def close(self):
		self.socket.close()

# Protocol:

# message_type_code: 0 (normal code) or 1 (error code), 1 byte

# if error code: 4 bytes big endian number depicting message length, followed by that number of string bytes encoded in utf8
# if normal code: message that has to be sent depending on the conversation that is being had at the moment