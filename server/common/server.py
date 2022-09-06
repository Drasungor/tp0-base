import socket
import logging
import signal
import sys
# import time
import traceback
import multiprocessing as mp
import concurrent.futures as fut
import threading

from common.utils import ClientSocket, ClosedSocket, is_winner, update_winners_file


class AtomicVariable:
    def __init__(self, value):
        self.lock = threading.Lock()
        self.value = value

    def atomic_write(self, value):
        self.lock.acquire()
        self.value = value 
        self.lock.release()

    def atomic_read(self):
        self.lock.acquire()
        ret_value = self.value
        self.lock.release()
        return ret_value

def await_closing_message(message_queue: mp.Queue, should_keep_iterating: AtomicVariable):
    message_queue.get()
    should_keep_iterating.atomic_write(False)

def handle_client_connection(file_writer_queue: mp.Queue, connections_processors_queue: mp.Queue, client_sock: ClientSocket):
    """
    Read message from a specific client socket and closes the socket

    If a problem arises in the communication with the client, the
    client socket will also be closed
    """
    should_keep_iterating = AtomicVariable(True)

     # Since this thread will just wait for the queue message, and the process has a
     # lot of I/O operations, this thread should not affect performance
    queue_reader_thread = threading.Thread(target = connections_processors_queue, args = (connections_processors_queue, should_keep_iterating))
    queue_reader_thread.start()                                          
    try:
        while should_keep_iterating.atomic_read():
            contestants = client_sock.recv_contestants()

            # BORRAR
            # for contestant in contestants:
            #     logging.info("First name: {}".format(contestant.first_name))
            #     logging.info("Last name: {}".format(contestant.last_name))
            #     logging.info("Document: {}".format(contestant.document))
            #     logging.info("Birthdate name: {}".format(contestant.birthdate))

            winners = filter(lambda contestant: is_winner(contestant), contestants)
            # client_sock.send_lottery_result(is_winner(contestant))
            client_sock.send_contestants(winners)
            file_writer_queue.put(winners)
    except OSError:
        logging.info("Error while reading socket {}".format(client_sock))
    except ClosedSocket:
        logging.info("Socket closed unexpectedly")
    except Exception as e:
        logging.info("Error: {}".format(str(e)))
        logging.info("Error traceback: {}".format(traceback.format_exc()))
        client_sock.send_error_message(str(e))
    finally:
        client_sock.close()
        connections_processors_queue.close()
        connections_processors_queue.join_thread()
        file_writer_queue.close()
        file_writer_queue.join_thread()
        queue_reader_thread.join()

class ConnectionStatus:
    def __init__(self, server_socket):
        self.current_connection = None
        self._server_socket = server_socket
        signal.signal(signal.SIGTERM, self.close_connection)
    
    def add_connection(self, socket):
        self.current_connection = socket

    def delete_connection(self):
        self.current_connection = None

    def close_connection(self, *args):
        self._server_socket.close()
        logging.info("SIGTERM received")
        logging.info("Closed server socket")
        if (not (self.current_connection is None)):
            self.current_connection.close()
            logging.info("Closed dangling socket connection")
        sys.exit(143)

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self.connection_status = ConnectionStatus(self._server_socket)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """
        file_writer_queue = mp.Queue()
        connections_processors_queue = mp.Queue()
        mp.Process(target = update_winners_file, args = [file_writer_queue])

        pools_available_processes = mp.cpu_count() - 2
        processors_pool = fut.ProcessPoolExecutor(pools_available_processes) # Since we will have this and the file writer processes

        # TODO: Modify this program to handle signal to graceful shutdown
        # the server
        not_done_tasks = []
        while True:
            while len(not_done_tasks) < pools_available_processes:
                client_sock = self.__accept_new_connection()
                # handle_client_connection(connections_processors_queue, client_sock)
                not_done_tasks.append(processors_pool.submit(handle_client_connection, file_writer_queue, connections_processors_queue, client_sock))
            _, not_done_tasks = mp.wait(not_done_tasks, return_when = mp.FIRST_COMPLETED)
        # TODO: cerrar cola de file process en sigterm


    def __accept_new_connection(self) -> ClientSocket:
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info("Proceed to accept new connections")
        c, addr = self._server_socket.accept()
        self.connection_status.add_connection(c)
        logging.info('Got connection from {}'.format(addr))
        return ClientSocket(c)
