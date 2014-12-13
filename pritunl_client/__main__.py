import optparse
import sys
import os
import re
import subprocess
import signal
import time
import hashlib
import json

def client_gui():
    from pritunl_client import app
    parser = optparse.OptionParser()
    parser.add_option('--version', action='store_true', help='Print version')
    (options, args) = parser.parse_args()

    if options.version:
        print '%s v%s' % (pritunl.__title__, pritunl.__version__)
    else:
        client_app = app.App()
        client_app.main()

def client():
    from pritunl_client import click
    from pritunl_client import utils

    @click.group()
    def cli():
        pass

    @click.command(name='list')
    def list_cmd():
        response = utils.request.get(
            'http://localhost:9797/list',
        )

        if response.status_code == 200:
            click.echo(response.content)
        else:
            click.echo(response.content)
            sys.exit(1)
    cli.add_command(list_cmd)

    @click.command(name='import')
    @click.argument('profile_in')
    def import_cmd(profile_in):
        data = {}
        if os.path.exists(profile_in):
            data['profile_path'] = os.path.abspath(profile_in)
        else:
            data['profile_uri'] = profile_in

        response = utils.request.post(
            'http://localhost:9797/import',
            json_data=data,
        )

        if response.status_code == 200:
            click.echo('Successfully imported profile')
        else:
            click.echo(response.content)
            sys.exit(1)
    cli.add_command(import_cmd)

    @click.command(name='remove')
    @click.argument('profile_ids', nargs=-1)
    def remove_cmd(profile_ids):
        for profile_id in profile_ids:
            response = utils.request.delete(
                'http://localhost:9797/remove/%s' % profile_id,
            )

            if response.status_code == 200:
                click.echo('Successfully removed profile')
            else:
                click.echo(response.content)
                sys.exit(1)
    cli.add_command(remove_cmd)

    @click.command(name='start')
    @click.argument('profile_ids', nargs=-1)
    @click.option('--password', default=None)
    def start_cmd(profile_ids, password):
        for profile_id in profile_ids:
            if password:
                data = {
                    'passwd': password,
                }
            else:
                data = None

            response = utils.request.put(
                'http://localhost:9797/start/%s' % profile_id,
                json_data=data,
            )

            if response.status_code == 200:
                click.echo('Successfully started profile')
            else:
                click.echo(response.content)
                sys.exit(1)
    cli.add_command(start_cmd)

    @click.command(name='stop')
    @click.argument('profile_ids', nargs=-1)
    def stop_cmd(profile_ids):
        for profile_id in profile_ids:
            response = utils.request.put(
                'http://localhost:9797/stop/%s' % profile_id,
            )

            if response.status_code == 200:
                click.echo('Successfully stopped profile')
            else:
                click.echo(response.content)
                sys.exit(1)
    cli.add_command(stop_cmd)

    @click.command(name='enable')
    @click.argument('profile_ids', nargs=-1)
    def enable_cmd(profile_ids):
        for profile_id in profile_ids:
            response = utils.request.put(
                'http://localhost:9797/enable/%s' % profile_id,
            )

            if response.status_code == 200:
                click.echo('Successfully enabled profile')
            else:
                click.echo(response.content)
                sys.exit(1)
    cli.add_command(enable_cmd)

    @click.command(name='disable')
    @click.argument('profile_ids', nargs=-1)
    def disable_cmd(profile_ids):
        for profile_id in profile_ids:
            response = utils.request.put(
                'http://localhost:9797/disable/%s' % profile_id,
            )

            if response.status_code == 200:
                click.echo('Successfully disabled profile')
            else:
                click.echo(response.content)
                sys.exit(1)
    cli.add_command(disable_cmd)

    cli()

def _pk_start(autostart=False):
    regex = r'(?:/pritunl_client/profiles/[a-z0-9]+\.ovpn)$'
    if not re.search(regex, sys.argv[1]):
        raise ValueError('Profile must be in home directory')
    if autostart:
        with open(sys.argv[1], 'r') as profile_file:
            profile_hash = hashlib.sha1(profile_file.read()).hexdigest()
        profile_hash_path = os.path.join(os.path.abspath(os.sep),
            'etc', 'pritunl_client', profile_hash)
        if not os.path.exists(profile_hash_path):
            raise ValueError('Profile not authorized to autostart')

    args = ['openvpn', '--config', sys.argv[1]]

    if len(sys.argv) > 2:
        os.chown(sys.argv[2], os.getuid(), os.getgid())
        args.append('--auth-user-pass')
        args.append(sys.argv[2])

    try:
        process = subprocess.Popen(args)
        def sig_handler(signum, frame):
            process.send_signal(signum)
        signal.signal(signal.SIGINT, sig_handler)
        signal.signal(signal.SIGTERM, sig_handler)
        sys.exit(process.wait())
    finally:
        if len(sys.argv) > 2:
            os.remove(sys.argv[2])

def pk_start():
    _pk_start(False)

def pk_autostart():
    _pk_start(True)

def pk_stop():
    pid = int(sys.argv[1])
    cmdline_path = '/proc/%s/cmdline' % pid
    regex = r'/pritunl_client/profiles/[a-z0-9]+\.ovpn'
    if not os.path.exists(cmdline_path):
        return
    with open('/proc/%s/cmdline' % pid, 'r') as cmdline_file:
        cmdline = cmdline_file.read().strip().strip('\x00')
        if not re.search(regex, cmdline):
            raise ValueError('Not a pritunl client process')
    os.kill(pid, signal.SIGTERM)
    for i in xrange(int(5 / 0.1)):
        time.sleep(0.1)
        if not os.path.exists('/proc/%s' % pid):
            break
        os.kill(pid, signal.SIGTERM)

def pk_set_autostart():
    regex = r'(?:/pritunl_client/profiles/[a-z0-9]+\.ovpn)$'
    if not re.search(regex, sys.argv[1]):
        raise ValueError('Profile must be in home directory')
    with open(sys.argv[1], 'r') as profile_file:
        profile_hash = hashlib.sha1(profile_file.read()).hexdigest()
    etc_dir = os.path.join(os.path.abspath(os.sep),
        'etc', 'pritunl_client')
    if not os.path.exists(etc_dir):
        os.makedirs(etc_dir)
    profile_hash_path = os.path.join(etc_dir, profile_hash)
    with open(profile_hash_path, 'w') as profile_hash_file:
        pass

def pk_clear_autostart():
    profile_hash_path = os.path.join(os.path.abspath(os.sep),
        'etc', 'pritunl_client', sys.argv[1])
    if os.path.exists(profile_hash_path):
        os.remove(profile_hash_path)
