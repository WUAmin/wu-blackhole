FROM ubuntu:16.04

MAINTAINER WUAmin <wuamin@gmail.com>

RUN cd && \
  # Update system
  apt-get update -yy && \
  # apt-get upgrade -yy && apt-get dist-upgrade -yy && \
  apt-get install -yy git python3-dev python3-pip libgirepository1.0-dev libcairo2-dev libpango1.0-dev libwebkitgtk-3.0-0 gir1.2-webkit-3.0 libcairo2-dev fuse libfuse2 libssl-dev && \
  apt-get clean && rm -rf /var/lib/apt/lists/* && rm -rf /var/cache/apt/archives

CMD /project/docker/_linux-build.sh
