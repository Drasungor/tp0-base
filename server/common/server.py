import socket
import logging
import signal
import sys
# import time

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

        # TODO: Modify this program to handle signal to graceful shutdown
        # the server
        while True:
            client_sock = self.__accept_new_connection()
            self.__handle_client_connection(client_sock)

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            msg = client_sock.recv(1024).rstrip().decode('utf-8')
            logging.info(
                'Message received from connection {}. Msg: {}'
                .format(client_sock.getpeername(), msg))
            client_sock.send("Your Message has been received: {}\n".format(msg).encode('utf-8'))
        except OSError:
            logging.info("Error while reading socket {}".format(client_sock))
        finally:
            # logging.info("Wait before socket closure")
            # time.sleep(10)
            client_sock.close()
            self.connection_status.delete_connection()
            # logging.info("Wait after socket closure and deletion")
            # time.sleep(10)

    def __accept_new_connection(self):
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
        return c
