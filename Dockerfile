FROM ubuntu:21.04
ARG run_volk_profile

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update -q \
    && apt-get -y upgrade

RUN apt-get -y install -q \
        git \
        ca-certificates \
        cmake \
        build-essential \
        pkg-config \
        librtlsdr0 \
        gr-osmosdr \
        gnuradio \
        gnuradio-dev \
        libvolk2-dev \
        libvolk2-bin \ 
        libvolk2.4 \
        --no-install-recommends
RUN apt-get clean
RUN apt-get autoclean

RUN if [ -n "$run_volk_profile" ] ; then volk_profile ; fi

# Install discord.py requisites
RUN apt-get -y install -q \
        libffi-dev \
        libnacl-dev \
        libopus-dev \
        python3-dev \
        python3-pip \
        --no-install-recommends

RUN pip3 install discord.py[voice]==1.7.2

ADD stereo_fm.py /opt/stereo_fm.py

ENTRYPOINT ["/usr/bin/python3", "/opt/stereo_fm.py"]