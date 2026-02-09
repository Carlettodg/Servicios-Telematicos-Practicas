# coding=utf-8
#!/usr/bin/env python3

import socket
import selectors    #https://docs.python.org/3/library/selectors.html
import select
import types        # Para definir el tipo de datos data
import argparse     # Leer parametros de ejecución
import os           # Obtener ruta y extension
from datetime import datetime, timedelta # Fechas de los mensajes HTTP
import time         # Timeout conexión
import sys          # sys.exit
import re           # Analizador sintáctico
import logging      # Para imprimir logs



BUFSIZE = 8192 # Tamaño máximo del buffer que se puede utilizar
TIMEOUT_CONNECTION = 20 # Timout para la conexión persistente
MAX_ACCESOS = 10

# Extensiones admitidas (extension, name in HTTP)
filetypes = {"gif":"image/gif", "jpg":"image/jpg", "jpeg":"image/jpeg", "png":"image/png", "htm":"text/htm", 
             "html":"text/html", "css":"text/css", "js":"text/js"}

# Configuración de logging
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s.%(msecs)03d] [%(levelname)-7s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()


def enviar_mensaje(cs, data):
    """ Esta función envía datos (data) a través del socket cs
        Devuelve el número de bytes enviados.
    """
    if isinstance(data, str):
       data =  data.encode()

    bytes_env = cs.send(data)
    return bytes_env


    pass


def recibir_mensaje(cs):
    """ Esta función recibe datos a través del socket cs
        Leemos la información que nos llega. recv() devuelve un string con los datos.
    """
    datos = cs.recv(BUFSIZE)

    return datos
    pass


def cerrar_conexion(cs):
    """ Esta función cierra una conexión activa.
    """
    cs.close()

    pass


def process_cookies(headers,  cs):
    """ Esta función procesa la cookie cookie_counter
        1. Se analizan las cabeceras en headers para buscar la cabecera Cookie
        2. Una vez encontrada una cabecera Cookie se comprueba si el valor es cookie_counter
        3. Si no se encuentra cookie_counter , se devuelve 1
        4. Si se encuentra y tiene el valor MAX_ACCESSOS se devuelve MAX_ACCESOS
        5. Si se encuentra y tiene un valor 1 <= x < MAX_ACCESOS se incrementa en 1 y se devuelve el valor
    """

    contador = 1     #valor por defecto 

    for header in headers : 
        (antes, sep, despues) = header.partition("Cookie:")   #buscamos la cabecera cookie            HELLO Cookie: cookie_counter:2

        if sep == "Cookie:" :
            (v1, vsep, v2) = despues.partition("cookie_counter:") 

        if vsep == "cookie_counter:" :
            lista_valores = v2.split(";")               #cogemos el valor por si tenemos un ; despues 

            valor = lista_valores[0]

            try:
                contador = int(valor)

                if contador >= MAX_ACCESOS:
                    return MAX_ACCESOS
            
                else:
                    contador += 1

            except ValueError:
                    contador = 1
    
    return contador


    """EJEMPLO DE PARTICION DE UNA CADENA
    Buscamos: Usamos if "Cookie:" in header.


    Partimos: Usamos header.partition("cookie_counter=").

    Esto nos devuelve: ("Cookie: ", "cookie_counter=", "5; session=abc").


    Limpiamos: Al tercer elemento ("5; session=abc") le aplicamos .split(';').

    Nos devuelve una lista: ["5", " session=abc"].

    Resultado: El primer elemento de esa lista ("5") es nuestro número.

    """

    """El servidor no guarda estado de cada lista de usuario o algo asi degún el profesor
    No hace falta generar una tabla nueva cada vez que viene un nuevo usuario"""


    
    pass


def process_web_request(cs, webroot):
    #Procesamiento principal de los mensajes recibidos.Típicamente se seguirá un procedimiento similar al siguiente (aunque el alumno puede modificarlo si lo desea)

        #Bucle para esperar hasta que lleguen datos en la red a través del socket cs con select()
        while True:
            rsublist, _, _ = select.select([cs], [], [], TIMEOUT_CONNECTION)  # rsublist contendrá el socket si hay caracteres disponibles para leer
            #Se comprueba si hay que cerrar la conexión por exceder TIMEOUT_CONNECTION segundos
       
            if not rsublist: 
                logger.info("Conexión cerrada por timeout. ")
                cerrar_conexion(cs)
                break
               
            # Si no es por timeout y hay datos en el socket cs.
                # Leer los datos con recv.
            datos_socket = recibir_mensaje (cs)        
            
            if not datos_socket:
                cerrar_conexion(cs)
                break
    
                        
              # Analizar que la línea de solicitud y comprobar está bien formateada según HTTP 1.1
            linea_solicitud = datos_socket.decode()

            lineas = linea_solicitud.split('\r\n')

            if len(lineas) < 1:
                    continue            #evitamos que el programa falle

                    # Devuelve una lista con los atributos de las cabeceras.

            atributos = lineas[0].split()    #Esta linea contiene Método, URL y versión

            if len(atributos) !=3:
                enviar_mensaje(cs, "HTTP/1.1 400 Bad Request\r\n\r\n")
                break
                        
            metodo = atributos[0]
            urlcomp = atributos[1]
            version = atributos[2]

         # Comprobar si la versión de HTTP es 1.1     MENSAJE TIPO: GET /perfil.html?user=pepe HTTP/1.1
            if version != "HTTP/1.1":
                 enviar_mensaje(cs, "HTTP/1.1 505 HTTP Version Not Supported\r\n\r\n")
                 break
            # Comprobar si es un método GET o POST. Si no devolver un error Error 405 "Method Not Allowed".

            if metodo not in ["GET", "POST"]:
                logger.error("Error 405 Method Not Allowed")
                enviar_mensaje(cs, "HTTP/1.1 405 Method Not Allowed\r\n\r\n")
                continue
            

            # Leer URL y eliminar parámetros si los hubiera       

            (url, sep, params) = urlcomp.partition('?')

            # Comprobar si el recurso solicitado es /, En ese caso el recurso es index.html

            if url == "/":
                url = "/index.html"


            # Construir la ruta absoluta del recurso (webroot + recurso solicitado)
            ruta_absoluta = webroot + url
            
            # Comprobar que el recurso (fichero) existe, si no devolver Error 404 "Not found"

            if not os.path.isfile(ruta_absoluta):
                logger.error("Error 404 Not Found")
                enviar_mensaje(cs, "HTTP/1.1 404 Not Found\r\n\r\n")
                continue
            
            # Analizar las cabeceras. Imprimir cada cabecera y su valor. Si la cabecera es Cookie comprobar
            # el valor de cookie_counter para ver si ha llegado a MAX_ACCESOS.
            # Si se ha llegado a MAX_ACCESOS devolver un Error "403 Forbidden"

            cabeceras = lineas[1:]
            for c in cabeceras:
                if c == "": break # Línea vacía indica fin
                print("Cabecera recibida: {}".format(c))

            nuevo_contador = process_cookies(cabeceras, cs)
            if nuevo_contador >= MAX_ACCESOS:
                logger.warning("Acceso denegado: MAX_ACCESOS alcanzado")
                enviar_mensaje(cs, "HTTP/1.1 403 Forbidden\r\n\r\n")
                continue
    
             
            # Obtener el tamaño del recurso en bytes.
            tamano = os.stat(ruta_absoluta).st_size
                    
            # Extraer extensión para obtener el tipo de archivo. Necesario para la cabecera Content-Type
            partes_url = url.split('.')
            extension = partes_url[-1]      #si era .jpg cogemos lo ultimo, lo que va dsp del `punto
            tipo = filetypes.get(extension, "text/html")
                    
            # Preparar respuesta con código 200. Construir una respuesta que incluya: la línea de respuesta y
            # las cabeceras Date, Server, Connection, Set-Cookie (para la cookie cookie_counter),
            # Content-Length y Content-Type.

            fecha =  datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

            respuesta_cabeceras = "HTTP/1.1 200 OK\r\n"
            respuesta_cabeceras += "Date: {}\r\n".format(fecha)
            respuesta_cabeceras += "Server: Servidor_ST_UMU\r\n"
            respuesta_cabeceras += "Connection: keep-alive\r\n" 
            respuesta_cabeceras += "Set-Cookie: cookie_counter={}\r\n".format(nuevo_contador)
            respuesta_cabeceras += "Content-Length: {}\r\n".format(tamano)
            respuesta_cabeceras += "Content-Type: {}\r\n".format(tipo)
            respuesta_cabeceras += "\r\n"


            # Leer y enviar el contenido del fichero a retornar en el cuerpo de la respuesta.
            enviar_mensaje(cs, respuesta_cabeceras)

            # Se abre el fichero en modo lectura y modo binario

            with open(ruta_absoluta, 'rb') as f:         #f = open(ruta, modo) r = lect, b = binario
                while True: 
                    # Se lee el fichero en bloques de BUFSIZE bytes (8KB)
                    bloque  = f.read(BUFSIZE)

                    # Cuando ya no hay más información para leer, se corta el bucle
                    if not bloque: 
                        break
                        
                    enviar_mensaje(cs, bloque)
    


def main():
    """ Función principal del servidor
    """

    try:

        # Argument parser para obtener la ip y puerto de los parámetros de ejecución del programa. IP por defecto 0.0.0.0
        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--port", help="Puerto del servidor", type=int, required=True)
        parser.add_argument("-ip", "--host", help="Dirección IP del servidor o localhost", required=True)
        parser.add_argument("-wb", "--webroot", help="Directorio base desde donde se sirven los ficheros (p.ej. /home/user/mi_web)")
        parser.add_argument('--verbose', '-v', action='store_true', help='Incluir mensajes de depuración en la salida')
        args = parser.parse_args()


        if args.verbose:
            logger.setLevel(logging.DEBUG)

        logger.info('Enabling server in address {} and port {}.'.format(args.host, args.port))

        logger.info("Serving files from {}".format(args.webroot))

         #Funcionalidad a realizar

        #Crea un socket TCP (SOCK_STREAM)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

         #Permite reusar la misma dirección previamente vinculada a otro proceso. Debe ir antes de sock.bind
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSADDR, 1)

         #Vinculamos el socket a una IP y puerto elegidos
        sock.bind((args.host, args.port))

         #Escucha conexiones entrantes

        sock.listen()


         #Bucle infinito para mantener el servidor activo indefinidamente
        while True:
            # Aceptamos la conexión
            cs, addr = sock.accept()

            # Creamos un proceso hijo
            pid = os.fork()

            # Si es el proceso hijo se cierra el socket del padre y procesar la petición con process_web_request()
            if pid == 0:
            
                sock.close()
                process_web_request(cs, args.webroot)
                cs.close() #lo pongo porque el hijo atiende al cliente y cuando termina cierra el socket
                sys.exit(0)
            
            # Si es el proceso padre cerrar el socket que gestiona el hijo.
            else:
                cs.close()
        
    except KeyboardInterrupt:
        True

if __name__== "__main__":
    main()
