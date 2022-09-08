# Agustín Cambiano - 102291

# TP0: Docker + Comunicación + Sincronización

En el presente repositorio se provee un ejemplo de cliente-servidor el cual corre en containers con la ayuda de [docker-compose](https://docs.docker.com/compose/). El mismo es un ejemplo práctico brindado por la cátedra para que los alumnos tengan un esqueleto básico de cómo armar un proyecto de cero en donde todas las dependencias del mismo se encuentren encapsuladas en containers. El cliente (Golang) y el servidor (Python) fueron desarrollados en diferentes lenguajes simplemente para mostrar cómo dos lenguajes de programación pueden convivir en el mismo proyecto con la ayuda de containers.

Por otro lado, se presenta una guía de ejercicios que los alumnos deberán resolver teniendo en cuenta las consideraciones generales descriptas al pie de este archivo.

## Instrucciones de uso
El repositorio cuenta con un **Makefile** que posee encapsulado diferentes comandos utilizados recurrentemente en el proyecto en forma de targets. Los targets se ejecutan mediante la invocación de:

* **make \<target\>**
El target principal a utilizar es **docker-compose-up** el cual permite inicializar el ambiente de desarrollo (buildear docker images del servidor y client, inicializar la red a utilizar por docker, etc.) y arrancar los containers de las aplicaciones que componen el proyecto.

Los targets disponibles son:
* **docker-compose-up**: Inicializa el ambiente de desarrollo (buildear docker images del servidor y client, inicializar la red a utilizar por docker, etc.) y arranca los containers de las aplicaciones que componen el proyecto.
* **docker-compose-down**: Realiza un `docker-compose stop` para detener los containers asociados al compose y luego realiza un `docker-compose down` para destruir todos los recursos asociados al proyecto que fueron inicializados. Se recomienda ejecutar este comando al finalizar cada ejecución para evitar que el disco de la máquina host se llene.
* **docker-compose-logs**: Permite ver los logs actuales del proyecto. Acompañar con grep para lograr ver mensajes de una aplicación específica dentro del compose.
* **docker-image**: Buildea las imágenes a ser utilizadas tanto en el client como el server. Este target es utilizado por **docker-compose-up**, por lo cual se lo puede utilizar para testear nuevos cambios en las imágenes antes de arrancar el proyecto.
* **build**: Compila la aplicación cliente en el host en lugar de Docker. La compilación de esta forma es mucho más rápida pero requiere tener el entorno de Golang instalado en la máquina.

### Servidor
El servidor del presente ejemplo es un EchoServer: los mensajes recibidos por el cliente son devueltos inmediatamente. El servidor actual funciona de la siguiente forma:
1. Servidor acepta una nueva conexión.
2. Servidor recibe mensaje del cliente y procede a responder el mismo.
3. Servidor desconecta al cliente.
4. Servidor procede a recibir una conexión nuevamente.

Al ejecutar el comando `make docker-compose-up` para comenzar la ejecución del ejemplo y luego el comando `make docker-compose-logs`, se observan los siguientes logs:

```
efeyuk@Helena:~/Development/tp0-base$ make docker-compose-logs
docker-compose -f docker-compose-dev.yaml logs -f
Attaching to client1, server
server     | 2020-04-10 23:10:54 INFO     Proceed to accept new connections.
server     | 2020-04-10 23:10:55 INFO     Got connection from ('172.24.125.3', 60392).
server     | 2020-04-10 23:10:55 INFO     Message received from connection. ('172.24.125.3', 60392). Msg: b'[CLIENT 1] Message number 1 sent.'
server     | 2020-04-10 23:10:55 INFO     Proceed to accept new connections.
server     | 2020-04-10 23:11:05 INFO     Got connection from ('172.24.125.3', 60400).
server     | 2020-04-10 23:11:05 INFO     Message received from connection. ('172.24.125.3', 60400). Msg: b'[CLIENT 1] Message number 2 sent.'
client1    | time="2020-04-10T23:10:55Z" level=info msg="[CLIENT 1] Message from server: Your Message has been received: b'[CLIENT 1] Message number 1 sent.'"
client1    | time="2020-04-10T23:11:05Z" level=info msg="[CLIENT 1] Message from server: Your Message has been received: b'[CLIENT 1] Message number 2 sent.'"
server     | 2020-04-10 23:11:05 INFO     Proceed to accept new connections.
server     | 2020-04-10 23:11:15 INFO     Got connection from ('172.24.125.3', 60406).
server     | 2020-04-10 23:11:15 INFO     Message received from connection. ('172.24.125.3', 60406). Msg: b'[CLIENT 1] Message number 3 sent'
client1    | time="2020-04-10T23:11:15Z" level=info msg="[CLIENT 1] Message from server: Your Message has been received: b'[CLIENT 1] Message number 3 sent.'"
server     | 2020-04-10 23:11:35 INFO     Message received from connection.
client1    | time="2020-04-10T23:12:05Z" level=info msg="[CLIENT 1] Main loop finished."
client1 exited with code 0
```

## Parte 1: Introducción a Docker
En esta primera parte del trabajo práctico se plantean una serie de ejercicios que sirven para introducir las herramientas básicas de Docker que se utilizarán a lo largo de la materia. El entendimiento de las mismas será crucial para el desarrollo de los próximos TPs.

### Ejercicio N°1:
Modificar la definición del DockerCompose para agregar un nuevo cliente al proyecto.

Para resolver este ejercicio se realizó únicamente una copia del servicio del cliente ya existente, modificándole el nombre para que no generara 
conflictos en docker.  

### Ejercicio N°1.1:
Definir un script (en el lenguaje deseado) que permita crear una definición de DockerCompose con una cantidad configurable de clientes.

Para resolver este ejercicio se desarrolló un script en python que genera el archivo llamado "docker-compose-dev.yaml". Para ejecutarlo se debe correr en el root de la carpeta del repositorio el comando "python3 compose_generator.py <cantidad_de_clientes>", siendo cantidad_de_clientes un número entero mayor a 0.

### Ejercicio N°2:
Modificar el cliente y el servidor para lograr que realizar cambios en el archivo de configuración no requiera un nuevo build de las imágenes de Docker para que los mismos sean efectivos. La configuración a través del archivo debe ser inyectada al ejemplo y persistida afuera del mismo (hint: `docker volumes`).

Para resolver este ejercicio se crearon en el archivo de docker compose volúmenes para los archivos config del cliente y del servidor, y además se generó un archivo .dockerignore, donde se agregaron los archivos de configuración. De esta forma se asegura que no van a existir los archivos en el container si no están localmente en el path especificado en el compose cada configuración del cliente y servidor.

### Ejercicio N°3:
Crear un script que permita testear el correcto funcionamiento del servidor utilizando el comando `netcat`. Dado que el servidor es un EchoServer, se debe enviar un mensaje el servidor y esperar recibir el mismo mensaje enviado. Netcat no debe ser instalado en la máquina host y no se puede exponer puertos del servidor para realizar la comunicación (hint: `docker network`).

Para resolver este ejercicio se creó un script en go que ejecuta un enviado del mensaje `my_message` llamando al comando de consola `echo my_message | nc -N server 12345`. Se pide luego el resultado de esta operación y se compara el mensaje resultante con el enviado, para corroborar que el server realmente es un echo server. Para utilizar netcat sin instalarlo localmente se creó otro servicio en el docker compose llamado nc, este descarga una imagen de golang para compilar y guardar el código del script descripto previamente, y luego baja una imagen de netcat para poder utilizarlo en el script. Una vez levantado el container se procede a llamar al script de comparación de input y resultado. Para ejecutar el programa se debe simplemente correr make docker-compose-up.

### Ejercicio N°4:
Modificar el cliente y el servidor para que el programa termine de forma gracefully al recibir la signal SIGTERM. Terminar la aplicación de forma gracefully implica que todos los sockets y threads/procesos de la aplicación deben cerrarse/joinearse antes que el thread de la aplicación principal muera. Loguear mensajes en el cierre de cada recurso (hint: Verificar que hace el flag `-t` utilizado en el comando `docker-compose down`).

Para resolver este ejercicio se debió implementar el manejo de SIGTERM tanto en el cliente como en el servidor. Las explicaciones de las implementaciones realizadas son las siguientes:  

- Servidor: al ser implementado en python, el manejo de SIGTERM se da implementando una función handler que se ejecutará cuando se reciba la señal. Debido a esto se creo la clase `ConnectionStatus`, cuya instancia se encarga de almacenar el accepter socket del server, e ir guardando y descartando los sockets de nuevas conexiones a medida que son aceptadas. Se define como handler de SIGTERM su método `close_connection`, donde se hace un cierre del accepter socket y del client socket (accesibles ya que el handler es un método de `ConnectionStatus`, por lo que se pueden acceder a sus atributos), en caso de que este último se encuentre presente. Una vez cerrados todos los recursos se cierra el programa con el código 143, que es el de sigterm.

- Cliente: al ser implementado en go, el manejo de SIGTERM se da creando una cola configurada de forma tal que espera al enviado de SIGTERM al programa. En la implementación del cliente se realiza un manejo de recursos distinto al del servidor. Al tratarse de una lectura de un channel y no de un cambio de contexto de ejecución, se decidió hacer una lectura no bloqueante del canal al final de cada iteración del loop de conexiones del cliente (aquel de la función `StartClientLoop`. En caso de leerse algo del channel se procede a cerrar el programa (no se cierran los recursos ya que se posicionó el handler de forma tal que en caso de tener que ejecutarse los programas ya estarán cerrados) con el código 143.

## Parte 2: Repaso de Comunicación y Sincronización

En esta segunda parte del trabajo práctico se plantea un caso de uso denominado **Lotería Nacional** descompuesto en tres ejercicios. Para la resolución de los mismos deberán utilizarse como base tanto los clientes como el servidor introducidos en la primera parte, con las modificaciones agregadas en el quinto ejercicio.

### Ejercicio N°5:
Modificar la lógica de negocio tanto de los clientes como del servidor para nuestro nuevo caso de uso. 

Por el lado de los clientes (quienes emularán _agencias de quiniela_) deberán recibir como variables de entorno los siguientes datos de una persona: nombre, apellido, documento y fecha de nacimiento. Dichos datos deberán ser enviados al servidor para saber si corresponden a los de un ganador, información que deberá loguearse. Por el lado del servidor (que emulará la _central de Lotería Nacional_), deberán recibirse los datos enviados desde los clientes y analizar si corresponden a los de un ganador utilizando la función provista `is_winner(...)`, para luego responderles.

Deberá implementarse un módulo de comunicación entre el cliente y el servidor donde se maneje el envío y la recepción de los paquetes, el cual se espera que contemple:
* Serialización de los datos.
* Definición de un protocolo para el envío de los mensajes.
* Correcto encapsulamiento entre el modelo de dominio y la capa de transmisión.
* Empleo correcto de sockets, incluyendo manejo de errores y evitando el fenómeno conocido como _short-read_.

Para la resolución de este ejercicio se implementaron tanto en el servidor como en el clientes abstracciones de enviado de mensajes serializados que contienen datos de un cliente. Estos se usaron para generar una interfaz que oculte la comunicación por sockets, y que cada programa pueda preocuparse en el alto nivel únicamente por la lógica del programa (definir si un usuario ganó o no, imprimir por pantalla el resultado, etc). Para que estos pudiesen comunicarse correctamente entre sí se armó un protocolo, el cual se describe a continuación.

En una conexión puede enviarse información de un cliente o un mensaje de error, por esto se comienza enviando 1 byte que indica de qué tipo de mensaje se trata. En caso de enviarse un mensaje que contenga datos del participante a evaluar se enviará el código 0, y en caso de que se quiera enviar un mensaje de error se enviará el código 1.  

Antes de explicar los mensajes que siguen al código de tipo de mensaje, es necesario aclarar que los strings son enviados con un encoding de tipo utf-8, y son precedidos por su largo en cantidad de bytes, escrito en un número de 4 bytes en big endian, de la siguiente forma: | 4 bytes big endian | string utf8 |

Dicho esto, lo que sigue al código de mensaje es:  
- Código 1: lo sigue un string que indica el error que tuvo lugar. El tipo de error a enviar es lógico de aplicación, no de comunicación de sockets. En esta implementación es utilizado únicamente por el servidor para indicarle al cliente si una fecha se recibió en un formato no procesable. Un mensaje de este tipo sería el siguiente: | 1 | string de error |, tomando en cuenta la forma de enviar strings mencionada previamente.
- Código 0: si lo recibe el servidor, se envía en forma de string los 4 datos del cliente, en orden First name, Last name, Document, Birthdate. Un mensaje de este tipo sería el siguiente: | 0 | string first name | string last name | string document | string birthdate |, tomando siempre en cuenta la forma de enviar strings explicada previamente. Si por otro lado lo recibe el cliente, entonces al código le seguirá 1 byte que indica si el participante enviado previamente ganó o no, siendo 1 el valor que indica que ganó, y 0 el que indica que no.  

Los posibles flujos de mensajes son los siguientes:  
- Sin errores:  
cliente -> | 0 | string first name | string last name | string document | string birthdate | -> servidor  
cliente <- | 0 | 0 o 1 según perdió o ganó | <- servidor  

- Con error en birthdate:
cliente -> | 0 | string first name | string last name | string document | string birthdate | -> servidor  
cliente <- | 0 | string descriptivo con el error | <- servidor  

No se realizaron modificaciones en el manejo de recursos con SIGTERM tanto en el cliente como en el servidor, aunque el cliente, al enviar ahora un único mensaje, chequea por SIGTERM únicamente luego de terminar la conversación.

Es necesario aclarar que, al ser el código de error sobre lógica de aplicación, no se puede enviar en el medio del protocolo, será interpretado como un byte más del mensaje.

### Ejercicio N°6:
Modificar los clientes para que levanten los datos de los participantes desde los datasets provistos en los archivos de prueba en lugar de las variables de entorno. Cada cliente deberá consultar por todas las personas de un mismo set (los cuales representan a los jugadores de cada agencia) en forma de batch, de manera de poder hacer varias consultas en un solo request. El servidor por otro lado deberá responder con los datos de todos los ganadores del batch, y cada cliente al finalizar las consultas deberá loguear el porcentaje final de jugadores que hayan ganado en su agencia.

Para facilitar la representación de los bytes del protocolo, se representará al conjunto de bytes | string first name | string last name | string document | string birthdate | como | Participant | o | Winner |  

Para la implementación de este ejercicio se tuvo que leer de un archivo csv, donde se encontraban todos los participantes a procesar. Se incluyó la lectura y enviado de participantes en la abstracción de procesamiento de participantes (clase `ParticipantsManager`). El dataset que utiliza cada cliente, junto con la cantidad de participantes por batch es configurada en variables de entorno en el archivo de docker-compose.

En este ejercicio el cliente se conecta al servidor, envía un batch de participantes, espera a la respuesta que indica los datos de los participantes que ganaron la lotería, los imprime por pantalla, y vuelve a repetir este proceso. Esto se realiza hasta que haya algún error o se termine el archivo que se quiere procesar, momento en el cual se imprime por pantalla la proporción de usuarios que ganó la lotería.

Al pasar de enviarse un único participante a enviar y recibir un array, se debió realizar cambios en el protocolo de comunicación. Para pasar a enviar el array se decidió establecer el número delimitador `0xFFFFFFFF` (4 bytes), que permite indicarle al recibidor que luego de este no recibirá más participantes en ese batch. La forma de serializar un participante particular no fue modificada, por lo que el número delimitador será tomado como un set de bytes más si está en el medio de un string (ya sea porque se usa intencionalmente o por error de posicionamiento del delimitador). Cuando se está por leer un participante se lee primero el tamaño del primer string, si es el número delimitador entonces se sabe que no vendrán más participantes, sino se procede a leer el participante como ya se hacía previamente (el número leído termina siendo el largo del string del nombre del participante).

Esto aplica tanto para el enviado de participantes del cliente al servidor como para el enviado de ganadores del servidor al cliente, utilizan el mismo protocolo, remplazando así la respuesta booleana que se utilizaba antes para el enviado de un único participante.

Un flujo normal de comunicación de un batch sin errores entre cliente y servidor sería el siguiente:

cliente -> | 0 | Participant 1 | Participant 2 | ... | Participant n | 0xFFFFFFFF | -> servidor
cliente <- | 0 | Winner 1 | Winner 2 | ... | Winner m | 0xFFFFFFFF | <- servidor

El manejo de SIGTERM continúa sin tener cambios para la liberación de recursos, con la diferencia de que se vuelve a leer en loop de forma no bloqueante el  channel de la señal en el cliente.

### Ejercicio N°7:
Modificar el servidor actual para que el mismo permita procesar mensajes y aceptar nuevas conexiones en paralelo. Además, deberá comenzar a persistir la información de los ganadores utilizando la función provista `persist_winners(...)`. Considerar los mecanismos de sincronización a utilizar para el correcto funcionamiento de dicha persistencia.

En caso de que el alumno desee implementar un nuevo servidor en Python,  deberán tenerse en cuenta las [limitaciones propias del lenguaje](https://wiki.python.org/moin/GlobalInterpreterLock).

Para resolver este ejercicio no se realizaron modificaciones en el protocolo. Se resolvió lo pedido creando procesos que leen de una cola sockets de clientes aceptados, en los que se realiza el mismo procedimiento que en el ejercicio 6. La diferencia en este caso consiste en que, además de responder los ganadores que resultaron del batch, estos deben persistirse en un archivo. Para lograrlo, se creó un proceso escritor cuya única tarea es leer listas de ganadores de una cola y escribirlas en el archivo al cual únicamente él tiene acceso. De esta forma los distintos procesos envían concurrentemente ganadores para persistir, pero estos son persistidos de forma serial por un único proceso.

En este ejercicio sí se realizaron cambios en la liberación de recursos al recibir un SIGTERM, en el servidor. Al utilizarse colas bloqueantes para comunicación entre procesos, y procesos en sí, al recibir un sigterm cada proceso debe asegurarse de cerrar bien todas sus colas de comunicación. Además de esto los clientes deben asegurarse de cerrar la conexión que estén manejando actualmente, y de consumir y cerrar todas las conexiones pendientes que queden en la cola de enviado de sockets. Para el caso del proceso principal, además del cerrado de colas y sockets, se debe hacer un join de todos los procesos que generó.

### Ejercicio N°8:
Agregar en los clientes una consulta por el número total de ganadores de todas las agencias, por lo cual se deberá modificar el servidor para poder llevar el trackeo de dicha información.

En caso de que alguna agencia consulte a la central antes de que esta haya completado el procesamiento de las demás, deberá recibir una respuesta parcial con el número de agencias que aún no hayan finalizado su carga de datos y volver a consultar tras N segundos.

Para realizar este ejercicio se agregó en el cliente una goroutine que se encarga de cada N segundos (configurable en el archivo de docker compose) abre una conexión, pide información sobre la cantidad total de ganadores, y cierra la conexión. Esto lo hace mientras reciba que faltan conexiones por procesar, una vez que reciba la cantidad final de ganadores dejará de mandar estos mensajes.

Como para enviar el pedido de la cantidad de ganadores se abre una nueva conexión cada vez, se modificó el protocolo para que, al comenzar una conexión entre el cliente y el servidor, el cliente envíe 1 byte que indique si es una conexión para procesar participantes (enviando el número 0) o para obtener la cantidad total de ganadores (enviando el número 0). En caso de que se trate de una conexión para procesamiento de participantes se envía el socket a la cola de sockets para que sea procesado por los procesos hijos, en caso de que se trate de una conexión para conseguir la cantidad de ganadores se ve si quedan o no procesos por terminar (lo cual se trackea utilizando una cola en la que los procesos van enviando la cantidad de ganadores que resultaron de procesar su última conexión), y envían según esto la cantidad de ganadores totales o la cantidad de procesos que faltan terminar. Para este último mensaje se envía un número de 4 bytes big endian, seguido por 1 byte que vale 1 si es una respuesta final (terminaron de procesar conexiones todos los clientes) y vale 0 si todavía hay procesos trabajando con clientes.  

Ejemplos de posibles flujos de mensajes son los siguientes:  
- Procesamiento de participantes:  
cliente -> | 0 | 0 | Participant 1 | Participant 2 | ... | Participant n | 0xFFFFFFFF | -> servidor  
cliente <- | 0 | Winner 1 | Winner 2 | ... | Winner m | 0xFFFFFFFF | <- servidor  
cliente -> | 0 | Participant 1 | Participant 2 | ... | Participant n | 0xFFFFFFFF | -> servidor  
cliente <- | 0 | Winner 1 | Winner 2 | ... | Winner m | 0xFFFFFFFF | <- servidor  
...  
Notar que únicamente en el primer mensaje del cliente se envía el byte que indica el tipo de conexión.  

- Obtención de cantidad de ganadores con procesos trabajando:  
cliente -> | 1 | -> servidor  
cliente <- | cantidad de trabajadores | 0 | <- servidor  

- Obtención de cantidad de ganadores sin procesos trabajando:  
cliente -> | 1 | -> servidor  
cliente <- | cantidad de ganadores | 1 | <- servidor  

Al haber ahora una cola más en el servidor se debe tener en cuenta a la hora de procesar el SIGTERM. Por otro lado, en el cliente se debe esperar a que finalice la ejecución de la goroutine que se encarga de pedir la cantidad de ganadores, por lo que al recibir SIGTERM se le envía por un channel que se chequea luego de cada consulta al server que debe terminar su ejecución, y luego se utiliza ese mismo channel para esperar a que esta goroutine termine de ejecutarse, esperando a que envíe un mensaje al momento de terminar de ejecutarse. 

## Consideraciones Generales
Se espera que los alumnos realicen un fork del presente repositorio para el desarrollo de los ejercicios, el cual deberá contar con un README que explique cómo correr cada uno de estos. Para la segunda parte del TP también será necesaria una sección donde se explique el protocolo de comunicación implementado y los mecanismos de sincronización utilizado en el último ejercicio. Finalmente, se pide a los alumnos leer atentamente y **tener en cuenta** los criterios de corrección provistos [en el campus](https://campus.fi.uba.ar/course/view.php?id=761).
