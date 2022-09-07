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
    def __init__(self, process_id, server_socket, file_writer_queue, sockets_queue):
        self.current_connection = None
        self.process_id = process_id
        self._server_socket = server_socket
        self.file_writer_queue = file_writer_queue 
        self.sockets_queue = sockets_queue
        self.processes = []
        signal.signal(signal.SIGTERM, self.close_connection)
    
    def add_connection(self, socket):
        self.current_connection = socket

    def delete_connection(self):
        self.current_connection = None

    def add_children(self, children):
        self.processes.extend(children)

    def close_connection(self, *args):
        logging.info("[Process {}] Main process SIGTERM received".format(self.process_id))
        for child in self.processes:
            child.terminate()
        logging.info("[Process {}] Sent SIGTERM to all child processes".format(self.process_id))
        self._server_socket.close()
        logging.info("[Process {}] Closed server socket".format(self.process_id))
        if (not (self.current_connection is None)):
            self.current_connection.close()
            logging.info("[Process {}] Closed dangling socket connection".format(self.process_id))
        self.file_writer_queue.close()
        self.file_writer_queue.join_thread()
        logging.info("[Process {}] Closed file writer process queue".format(self.process_id))
        self.sockets_queue.close()
        self.sockets_queue.join_thread()
        logging.info("[Process {}] Closed file sockets queue".format(self.process_id))
        for child in self.processes:
            child.join()
        logging.info("[Process {}] Joined all child processes".format(self.process_id))
        logging.info("[Process {}] Exiting main process".format(self.process_id))
        sys.exit(143)

class ClientProcessStatus:
    def __init__(self, process_id, file_writer_queue, sockets_queue):
        self.file_writer_queue: mp.Queue = file_writer_queue
        self.sockets_queue: mp.Queue = sockets_queue
        self.process_id = process_id
        self.connection: ClientSocket = None
        signal.signal(signal.SIGTERM, self.close_resources)

    def add_connection(self, socket):
        self.connection = socket

    def delete_connection(self):
        self.connection = None

    def close_resources(self, *args):
        logging.info("[Process {}] Client process SIGTERM received".format(self.process_id))
        if (not (self.connection is None)):
            self.connection.close()
            logging.info("[Process {}] Closed dangling socket connection".format(self.process_id))
        self.file_writer_queue.close()
        self.file_writer_queue.join_thread()
        logging.info("[Process {}] Closed file writer process queue".format(self.process_id))
        is_queue_empty = False
        while (not is_queue_empty):
            try:
                self.sockets_queue.get_nowait().close()
                logging.info("[Process {}] Closed dangling queue socket connection".format(self.process_id))
            except queue.Empty:
                is_queue_empty = True
        self.sockets_queue.close()
        self.sockets_queue.join_thread()
        logging.info("[Process {}] Closed sockets queue".format(self.process_id))
        logging.info("[Process {}] Exiting client process".format(self.process_id))
        sys.exit(143)



def handle_client_connection(process_id: int, file_writer_queue: mp.Queue, sockets_queue: mp.Queue):
    """
    Read message from a specific client socket and closes the socket

    If a problem arises in the communication with the client, the
    client socket will also be closed
    """
    # should_keep_iterating = AtomicVariable(True)

     # Since this thread will just wait for the queue message, and the process has a
     # lot of I/O operations, this thread should not affect performance

    process_status = ClientProcessStatus(process_id, file_writer_queue, sockets_queue)

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
                logging.info("[Process {}] Error while reading socket: {}".format(process_id, str(e)))
                handled_exception = True
            except ClosedSocket:
                logging.info("[Process {}] Socket closed".format(process_id))
                handled_exception = True
            except Exception as e:
                logging.info("[Process {}] Error: {}".format(process_id, str(e)))
                logging.info("[Process {}] Error traceback: {}".format(process_id, traceback.format_exc()))
                handled_exception = True
                client_sock.send_error_message(str(e))
            if handled_exception:
                connection_is_alive = False
                handled_exception = False
                client_sock.close()
                process_status.delete_connection()

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

        self.connection_status = MainProcessStatus(0, self._server_socket, file_writer_queue, sockets_queue)

        writer_process = mp.Process( target = update_winners_file, args = [1, file_writer_queue])
        writer_process.start()

        self.connection_status.add_children([writer_process])

        clients_processes = []
        for i in range(client_processes_amount):
            client_process = mp.Process(target = handle_client_connection, args = [i + 2, file_writer_queue, sockets_queue])
            client_process.start()
            clients_processes.append(client_process)
        # TODO: Modify this program to handle signal to graceful shutdown
        # the server
        self.connection_status.add_children(clients_processes)
        while True:
            sockets_queue.put(self.__accept_new_connection())
            self.connection_status.delete_connection()
            logging.info("[Process {}] Accepted new connection".format(0))

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


