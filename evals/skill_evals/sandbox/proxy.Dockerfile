# Allowlist proxy: the sandbox reaches the internet only through this container, and it forwards
# HTTPS CONNECT requests only to the hosts in proxy-allow.txt.
FROM alpine:3.20
RUN apk add --no-cache tinyproxy=1.11.2-r0
COPY tinyproxy.conf /etc/tinyproxy/tinyproxy.conf
COPY proxy-allow.txt /etc/tinyproxy/allow.txt
USER nobody
EXPOSE 8888
CMD ["tinyproxy", "-d", "-c", "/etc/tinyproxy/tinyproxy.conf"]
