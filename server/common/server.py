import socket
import logging
import signal
import sys
# import time
import traceback
import multiprocessing as mp
import queue

from common.utils import ClientSocket, ClosedSocket, is_winner, update_winners_file


class MainProcessStatus:
    def __init__(self, server_socket, file_writer_queue, sockets_queue):
        self.current_connection = None
        self._server_socket = server_socket
        signal.signal(signal.SIGTERM, self.close_connection)
    
    def add_connection(self, socket):
        self.current_connection = socket

    def delete_connection(self):
        self.current_connection = None

    def close_connection(self, *args):
        logging.info("SIGTERM received")
        self._server_socket.close()
        logging.info("Closed server socket")
        if (not (self.current_connection is None)):
            self.current_connection.close()
            logging.info("Closed dangling socket connection")
        self.file_writer_queue.close()
        self.file_writer_queue.join_thread()
        logging.info("Closed file writer process queue")
        self.sockets_queue.close()
        self.sockets_queue.join_thread()
        logging.info("Closed file sockets queue")
        sys.exit(143)

class ClientProcessStatus:
    def __init__(self, file_writer_queue, sockets_queue):
        self.file_writer_queue: mp.Queue = file_writer_queue
        self.sockets_queue: mp.Queue = sockets_queue
        self.connection: ClientSocket = None
        signal.signal(signal.SIGTERM, self.close_resources)

    def add_connection(self, socket):
        self.connection = socket

    def delete_connection(self):
        self.connection = None

    def close_resources(self, *args):
        logging.info("SIGTERM received")
        if (not (self.connection is None)):
            self.connection.close()
            logging.info("Closed dangling socket connection")
        self.file_writer_queue.close()
        self.file_writer_queue.join_thread()
        logging.info("Closed file writer process queue")
        is_queue_empty = False
        while (not is_queue_empty):
            try:
                self.sockets_queue.get_nowait().close()
                logging.info("Closed dangling queue socket connection")
            except queue.Empty:
                is_queue_empty = True
        self.sockets_queue.close()
        self.sockets_queue.join_thread()
        logging.info("Closed sockets queue")
        sys.exit(143)



def handle_client_connection(file_writer_queue: mp.Queue, sockets_queue: mp.Queue):
    """
    Read message from a specific client socket and closes the socket

    If a problem arises in the communication with the client, the
    client socket will also be closed
    """
    # should_keep_iterating = AtomicVariable(True)

     # Since this thread will just wait for the queue message, and the process has a
     # lot of I/O operations, this thread should not affect performance

    process_status = ClientProcessStatus(file_writer_queue, sockets_queue)

    connection_is_alive = False
    handled_exception = False
    while True:
        client_sock: ClientSocket = sockets_queue.get()
        process_status.add_connection(client_sock)
        connection_is_alive = True
        while connection_is_alive:
            try:
                contestants = client_sock.recv_contestants()
                winners = list(filter(is_winner, contestants))
                client_sock.send_contestants(winners)
                file_writer_queue.put(winners)
            except OSError as e:
                logging.info("Error while reading socket: {}".format(str(e)))
                handled_exception = True
            except ClosedSocket:
                logging.info("Socket closed")
                handled_exception = True
            except Exception as e:
                logging.info("Error: {}".format(str(e)))
                logging.info("Error traceback: {}".format(traceback.format_exc()))
                handled_exception = True
                client_sock.send_error_message(str(e))
            if handled_exception:
                connection_is_alive = False
                handled_exception = False
                client_sock.close()
                process_status.delete_connection()

            # TODO: mover al sigterm handler
            # sockets_queue.close()
            # sockets_queue.join_thread()
            # file_writer_queue.close()
            # file_writer_queue.join_thread()


class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """
        client_processes_amount = max(mp.cpu_count() - 2, 1)

        file_writer_queue = mp.Queue()
        sockets_queue = mp.Queue(client_processes_amount)

        self.connection_status = MainProcessStatus(self._server_socket, file_writer_queue, sockets_queue)

        writer_process = mp.Process(target = update_winners_file, args = [file_writer_queue])
        writer_process.start()

        clients_processes = []
        for _ in range(client_processes_amount):
            client_process = mp.Process(target = handle_client_connection, args = [file_writer_queue, sockets_queue])
            client_process.start()
            clients_processes.append(client_process)
        # TODO: Modify this program to handle signal to graceful shutdown
        # the server
        while True:
            sockets_queue.put(self.__accept_new_connection())
            logging.info("Accepted new connection")

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
