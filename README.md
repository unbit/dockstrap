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

```sh
pip install dockstrap
```

should be enough


Usage
=====

```sh
Usage: dockstrap [OPTIONS] IMAGE PATH

Options:
  --baseurl TEXT   set the base url for registry api access
  --cachedir TEXT  set the directory on which to store/cache image files
  --help           Show this message and exit.
  ```
  
The script downloads and extract docker images in the specified directory.

When downloading a new image file (that could be big) a cache directory is checked (already downloaded images will be reused).

By default the cache directory is in ~/dockstrap_cache you are free to remove it (or some of the items in it) whenever you want

By default the scripts connects to the https://index.docker.io url

You can run the script as root or as an unprivileged user, in this second case characters and block devices will be ignored, and already present files (in the destination directory) will be removed to avoid permissions problems during overwrite.

In root mode, only device files are removed before applying a new image (read: expliding the tarball)

Examples
========

```sh
# clone ubuntu image to 'foobuntu' directory
dockstrap ubuntu foobuntu
# chroot to it and run ls
chroot foobuntu ls
# clone tag 14.0.4 of ubuntu repository into 'trusty' directory
dockstrap ubuntu:14.04 trusty
# clone redis into /tmp/redis using /tmp/cache as cachedir
dockstrap --cachedir /tmp/cache redis /tmp/redis
```
