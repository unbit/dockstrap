import requests
import click
import os
import os.path
import tarfile
import stat


def setup_cachedir(path):
    if not os.path.isdir(path):
        os.mkdir(path)


def get_tags(baseurl, image):
    r = requests.get('{0}/v1/repositories/{1}/tags'.format(baseurl, image))
    return r.json()


def get_images(baseurl, image):
    r = requests.get('{0}/v1/repositories/{1}/images'.format(baseurl, image),
                     headers={'X-Docker-Token': 'true'})
    return (r.headers['x-docker-token'],
            r.headers['x-docker-endpoints'],
            r.json())


def download_layers(endpoint, token, image_id, cachedir):
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

    # start downloading layers
    # TODO verify checksum to avoid re-downloading
    for layer in layers:
        r = requests.get('https://{0}/v1/images/{1}/layer'.format(endpoint,
                                                                  layer),
                         headers={'Authorization': 'Token {0}'.format(token)},
                         stream=True)
        destination = os.path.join(cachedir, layer)
        content_length = long(r.headers['content-length'])
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
@click.argument('image')
@click.argument('path')
def dockstrap_run(baseurl, cachedir, image, path):
    setup_cachedir(cachedir)
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
    checksum = None
    image_id = None
    for image_item in images:
        if image_item['id'].startswith(layer):
            image_id = image_item['id']
            checksum = image_item['checksum']
            break
    if not image_id:
        raise click.ClickException("unable to find image id"
                                   " starting with '{0}'".format(layer))
    endpoint = endpoints.split(' ')[0]
    click.echo("using endpoint: {0}".format(endpoint))
    # now start iterating layers
    # and download them
    layers = download_layers(endpoint, token, image_id, cachedir)
    am_i_root = False
    if os.getuid() == 0:
        am_i_root = True

    for layer in layers:
        source = os.path.join(cachedir, layer)
        tarball = tarfile.open(source)
        # this list is filled only if
        # i am not uid 0
        members = []
        for taritem in tarball:
            if taritem.name.startswith('/'):
                raise click.ClickException("Security error, item {0} starts"
                                           " with /".format(taritem.name))
            if taritem.name.startswith('../'):
                raise click.ClickException("Security error, item {0} starts"
                                           " with ../".format(taritem.name))
            if not am_i_root and not taritem.ischr() and not taritem.isdev():
                destination = os.path.join(path, taritem.name)
                # ensure the user has write permissions on
                # an already existing regular file
                if os.path.isfile(destination) and \
                   not os.path.islink(destination):
                        mode = os.stat(destination).st_mode
                        os.chmod(destination, mode | stat.S_IWUSR)
                members.append(taritem)
        click.echo("extracting {0} to {1}".format(layer, path))
        if am_i_root:
            tarball.extractall(path=path)
        else:
            tarball.extractall(path=path, members=members)
    click.echo("your filesystem is ready at {0}".format(path))
