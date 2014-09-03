dockstrap
=========

Like debootstrap but uses docker registry

This simple tool allows you to download docker images in a directory out of the docker context.

You can use it to get a working rootfs for your chroots, or to get the power of the docker hub and combine it
with other namespace/containing/virtualization technologies, like plain lxc, uWSGI namespaces, qemu filesystem passing, and so on ...

Requirements
============

The tool is written in python and uses the requests (http://docs.python-requests.org/en/latest/) and click (http://click.pocoo.org/) modules

Installation
============


Usage
=====

Usage: dockstrap.py [OPTIONS] IMAGE PATH

Options:
  --baseurl TEXT   set the base url for registry api access
  --cachedir TEXT  set the directory on which to store/cache image files
  --help           Show this message and exit.
