FROM ubuntu:22.04

# Instalar dependencias y Kamailio
RUN apt update && apt install -y \
    default-mysql-server \
    kamailio \
    kamailio-mysql-modules \
    kamailio-presence-modules \
    kamailio-json-modules\
    && apt clean
RUN apt-get install sudo
RUN apt install net-tools

RUN service mysql start

# Copiar configuración personalizada
COPY kamailio.cfg /etc/kamailio/kamailio.cfg
COPY kamctlrc /etc/kamailio/kamctlrc

# Exponer puertos para SIP (UDP y TCP)
EXPOSE 5060/udp 5060/tcp

# Exponer puertos RTP
EXPOSE 10000-20000/udp

# 3 letras "y"

# Mantener el contenedor en ejecución para poder acceder al bash
CMD ["bash"]
