import sys

def write_file_beginning(docker_compose_file):
    docker_compose_file.write("""version: '3'
services:
  server:
    container_name: server
    image: server:latest
    entrypoint: python3 /main.py
    environment:
      - PYTHONUNBUFFERED=1
      - SERVER_PORT=12345
      - SERVER_LISTEN_BACKLOG=7
      - LOGGING_LEVEL=DEBUG
    networks:
      - testing_net""")

def write_file_clients(docker_compose_file, number_of_clients):
    for i in range(number_of_clients):
        client_number = i + 1
        docker_compose_file.write(f"""

  client{client_number}:
    container_name: client{client_number}
    image: client:latest
    entrypoint: /client
    environment:
      - CLI_ID={client_number}
      - CLI_SERVER_ADDRESS=server:12345
      - CLI_LOOP_LAPSE=1m2s
      - CLI_LOG_LEVEL=DEBUG
    networks:
      - testing_net
    depends_on:
      - server""")

def write_file_end(docker_compose_file):
    docker_compose_file.write("""

networks:
  testing_net:
    ipam:
      driver: default
      config:
        - subnet: 172.25.125.0/24""")

def write_file(clients_amount):
    file_pointer = open("docker-compose-dev.yaml", "w")
    write_file_beginning(file_pointer)
    write_file_clients(file_pointer, clients_amount)
    write_file_end(file_pointer)

def main():
    argv = sys.argv
    args_amounts = len(argv)
    if (args_amounts != 2):
        raise Exception("Command line arguments should have the amount of clients as it's only argument")
    number_of_clients = int(argv[1])
    if (number_of_clients < 1):
        raise Exception("The file needs 1 or more clients")
    write_file(number_of_clients)

main()