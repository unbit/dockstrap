import requests
import click
import os
import os.path
from subprocess import call


def setup_dir(path):
    if not os.path.isdir(path):
        os.mkdir(path)


def is_gzip(path):
    with open(path, 'rb') as f:
        gzip_header = f.read(2)
        if gzip_header[0] != 0x1F:
            return False
        if gzip_header[1] != 0x8B:
            return False
    return True


def get_tags(baseurl, image):
    r = requests.get('{0}/v1/repositories/{1}/tags'.format(baseurl, image))
    if r.status_code != 200:
        raise click.ClickException("repository {0} not found".format(image))
    return r.json()


def get_images(baseurl, image):
    r = requests.get('{0}/v1/repositories/{1}/images'.format(baseurl, image),
                     headers={'X-Docker-Token': 'true'})
    return (r.headers['x-docker-token'],
            r.headers['x-docker-endpoints'],
            r.json())


def get_checksum(image_id, images):
    for image in images:
        if image['id'] == image_id:
            if not image['checksum']:
                return None
            return image['checksum']
    return None


def download_layers(endpoint, token, image_id, cachedir, checksums):
    layers = []
    while True:
        r = requests.get('https://{0}/v1/images/{1}/json'.format(endpoint,
                                                                 image_id),
                         headers={'Authorization': 'Token {0}'.format(token)})
        image_json = r.json()
        if 'parent' in image_json:
            if not image_json['parent']:
                break
            image_id = image_json['parent']
            layers.insert(0, image_id)
        else:
            break

    # start downloading layers (if needed)
    for layer in layers:
        r = requests.get('https://{0}/v1/images/{1}/layer'.format(endpoint,
                                                                  layer),
                         headers={'Authorization': 'Token {0}'.format(token)},
                         stream=True)
        destination = os.path.join(cachedir, layer)
        content_length = int(r.headers['content-length'])

        # first of all check if the file exists
        if os.path.isfile(destination):
            # does the filesize matches ?
            if os.path.getsize(destination) == content_length:
                # do we need to compute the checksum ?
                checksum = get_checksum(layer, checksums)
                # TODO do something with checksum
                if checksum:
                    pass
                click.echo("reusing cached {0}".format(layer))
                continue
        remains = content_length
        with open(destination, 'w') as targz:
            while remains > 0:
                chunk = r.raw.read(32768)
                if not chunk:
                    break
                remains -= len(chunk)
                downloaded = content_length - remains
                click.echo("\rdownloading layer {0}"
                           " {1}/{2}".format(layer,
                                             downloaded,
                                             content_length),
                           nl=False)
                targz.write(chunk)
        click.echo('')
    return layers


@click.command()
@click.option('--baseurl', default='https://index.docker.io',
              help='set the base url for registry api access')
@click.option('--cachedir', default=os.path.expanduser('~/.dockstrap_cache'),
              help='set the directory on which to store/cache image files')
@click.option('--verbose', default=False,
              is_flag = True,
              help='set verbose mode')
@click.argument('image')
@click.argument('path')
def dockstrap_run(baseurl, cachedir, image, path, verbose):
    setup_dir(cachedir)
    setup_dir(path)
    click.echo("using baseurl: {0}".format(baseurl))
    click.echo("using cachedir: {0}".format(cachedir))
    tag = 'latest'
    force_tag = False
    # does the user specified a tag ?
    if ':' in image:
        force_tag = True
        image, tag = image.split(':', 1)
    # get the tags list
    tags = get_tags(baseurl, image)
    # check the requested tag exists:
    layer = None
    for tag_item in tags:
        if tag_item['name'] == tag:
            layer = tag_item['layer']
            break
    # if no tag is found, get the first one
    if not layer:
        if not force_tag:
            layer = tags[0]['layer']
            tag = tags[0]['name']
        else:
            raise click.ClickException("unable to find tag {0}"
                                       " for repository {1}".format(tag,
                                                                    image))

    click.echo("using image: {0}".format(image))
    click.echo("using tag: {0}".format(tag))

    """
    get the list of repository images
    this list will be used for managing
    checksums.
    the function returns the authentication token
    end the registry endpoints too
    """
    token, endpoints, images = get_images(baseurl, image)
    image_id = None
    for image_item in images:
        if image_item['id'].startswith(layer):
            image_id = image_item['id']
            break
    if not image_id:
        raise click.ClickException("unable to find image id"
                                   " starting with '{0}'".format(layer))
    endpoint = endpoints.split(' ')[0]
    click.echo("using endpoint: {0}".format(endpoint))
    # now start iterating layers
    # and download them
    layers = download_layers(endpoint,
                             token,
                             image_id,
                             cachedir,
                             images)
    am_i_root = False
    if os.getuid() == 0:
        am_i_root = True

    for layer in layers:
        source = os.path.join(cachedir, layer)
        flags = ['-', 'x', 'f']
        if is_gzip(source):
            flags.insert(1, 'z')
        if verbose:
            flags.insert(1, 'v')
        click.echo("extracting {0} to {1}".format(layer, path))
        if not am_i_root:
            ret = call(['tar',
                        '--exclude=dev', '-C', path, ''.join(flags), source])
        else:
            ret = call(['tar', '-C', path, ''.join(flags), source])
        if ret != 0:
            raise click.ClickException("tar failed")
    click.echo("your filesystem is ready at {0}".format(path))
