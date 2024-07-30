https://kamailio.org/docs/tutorials/devel/kamailio-install-guide-deb/

# Instalación Kamailio en Ubuntu 22.04

```
sudo apt update
sudo apt install default-mysql-server -y
sudo apt install kamailio kamailio-mysql-modules -y
```

Para revisar donde se instaló kamailio: ```which kamailio```

Para ver todos los paquetes específicos: ```sudo apt search kamailio```

## Archivos de configuración

Las configuraciones están en ```/etc/kamailio```

El archivo ```/etc/kamailio/kamctlrc``` tiene configuraciones de **direcciones IP y MYSQL**. Dentro del archivo, hay que realizar los siguientes cambios:

```sudo nano /etc/kamailio/kamctlrc```

Y dentro del archivo, descomentar modificiar las siguientes líneas:

```
SIP_DOMAIN=localhost

DBENGINE=MYSQL

DBHOST=localhost

DBPORT=3306

DBNAME=kamailio

DBRWUSER="kamailio"
DBRWPW="kamailiorw1"

DBROUSER="kamailioro"
DBROPW="kamailioro1"

DBROOTUSER="root"
DBROOTPW="dbrootpw1"

CHARSET="utf16"
```

EL archivo ```/etc/kamailio/kamailio.cfg``` tiene las configuraciones de kamailio como tal. Dentro del archivo, agregar los siguiente debajo de la primera línea:

```sudo nano /etc/kamailio/kamailio.cfg```

```
#!define WITH_MYSQL
#!define WITH_AUTH
#!define WITH_USRLOCDB
#!define DBURL "mysql://kamailio:kamailiorw1@localhost/kamailio"
```

Notar que ```kamailiorw1``` corresponde al valor de ```DBRWPW``` en el archivo ```/etc/kamailio/kamctlrc```

# Crear base de datos

Para crear la base de datos, ejecutar

```sudo kamdbctl create```

Se deben ignorar los warnings. Cada vez que pregunte, escribir la letra **y**, luego apretar ENTER.

**Nota: En caso de que no encuentre el archivo .mysql:**

buscar el archivo kamdbctl.mysql
```sudo find / -type f -name "kamdbctl.mysql" 2>/dev/null```

ruta_original = ruta donde se encuentra kamdbctl.mysql
ruta_final = ruta donde debería estar kamdbctl.mysql y donde lo busca mysql

```sudo cp ruta_original ruta_final```


# Scripts para iniciar el servicio

El servicio de kamailio ya debería estar ejecutándose. Se puede revisar con

```systemctl | grep running```

y confirmar que se está ejecutando. Se puede iniciar y detener con:

```
systemctl start kamailio
systemctl stop kamailio
```

También se puede configurar en consola para que inicie de forma automática al bootear (no sé si funciona bien):

```
sudo update-rc.d kamailio defaults
sudo update-rc.d kamailio enable
```
# Agregar usuarios

Se pueden añadir usuarios a la base de datos usando:

```kamctl add username password```

Ejemplo:

```
kamctl add diego 9856
kamctl add tablet 9856
kamctl add 123 9856
kamctl add 456 9856
```
# Logs (NO funciona bien) 

Mover logs de Kamailio a otro archivo.

https://www.kamailio.org/wikidocs/tutorials/3.2.x/syslog/#kamailio-with-syslog-and-log-rotate

Los logs se guardarán en el archivo ```/var/log/kamailio.log```

Crear el archivo ```10-kamailio.conf``` en la carpeta ```/etc/rsyslog.d```

```
sudo nano /etc/rsyslog.d/10-kamailio.conf
```
Dentro del archivo, agregar lo siguiente:
```
# log messages with LOG_LOCAL0 in /var/log/kamailio.log
local0.*            -/var/log/kamailio.log
```

Finalmente, resetear rsyslog

```sudo systemctl restart rsyslog```


## Crear Log Rotate para kamailio.log (NO funciona bien)

```sudo nano /etc/logrotate.d/kamailio```

y dentro del archivo agregar lo siguiente:

```
/var/log/kamailio.log {
    missingok
    size 50M
    create 0644 root root
    postrotate
        systemctl restart rsyslog > /dev/null 2>&1 || true
    endscript
}
```
Luego, ejecutar:

```
sudo chmod 755 /var/log/
systemctl restart rsyslog
```

Se puede revisar que se borró el log con

```sudo logrotate -f /etc/logrotate.d/kamailio```

