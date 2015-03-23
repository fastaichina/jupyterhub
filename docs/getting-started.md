# Getting started with JupyterHub

This document describes some of the basics of configuring JupyterHub to do what you want.
JupyterHub is highly customizable, so there's a lot to cover.


## Installation

See [the readme](../README.md) for help installing JupyterHub.


## JupyterHub's default behavior

Let's start by describing what happens when you type `sudo jupyterhub`
after installing it, without any configuration.

**NOTE** The default is to run without SSL encryption.
You should not run JupyterHub without HTTPS if you can help it.
See [below](#Security) for how to configure JupyterHub to use SSL.


### Authentication

The default Authenticator that ships with JupyterHub
authenticates users with their system name and password (via [PAM][]).
Any user on the system with a password will be allowed to start a single-user notebook server.


### Spawning servers

The default Spawner starts servers locally as each user,
one for each user. These servers listen on localhost,
and start in the given user's home directory.


### Network

JupterHub consists of three main categories of processes:

- Proxy
- Hub
- Spawners

The Proxy is the public face of the service.
Users access the server via the proxy,
which listens on all public interfaces on port 8000.
You can access JupyterHub at:

    http://localhost:8000

or any other IP or domain pointing for your system.

The other services, Hub and Spawners, all communicate with each other on localhost only.
If you are going to separate these processes across machines or containers,
you may need to tell them to listen on addresses other than localhost.

See [below](#Security) for how to configure JupyterHub to use SSL.


### Files

Starting JupyterHub will write two files to disk in the current working directory:

- `jupyterhub.sqlite` is the sqlite database containing all of the state of the Hub.
  This file allows the Hub to remember what users are running and where,
  as well as other information enabling you to restart the Hub
  without restarting the proxy or single-user servers.
- `jupyterhub_cookie_secret` is the encryption key used for securing cookies.
  This file needs to persist in order for restarting the Hub server to avoid invalidating cookies.
  Conversely, deleting this file and restarting the server effectively invalidates all login cookies.
  The cookie secret file is discussed [below](#Security).

The location of these files can be specified via configuration, discussed below.


## How to configure JupyterHub

JupyterHub is configured in two ways:

- command-line arguments. see `jupyterhub -h` for information about the arguments,
  or `jupyterhub --help-all` for a list of everything configurable on the command-line.
- config files. The default config file is `jupyterhub_config.py`, in the current working directory.
  You can create an empty config file with `jupyterhub --generate-config`
  to see all the configurable values.
  You can load a specific config file with `jupyterhub -f /path/to/jupyterhub_config.py`.
  (see also: [general docs](http://ipython.org/ipython-doc/dev/development/config.html)
  on the config system Jupyter uses)


## Networking

When it starts, JupyterHub creates two processes:

- a proxy (`configurable-http-proxy`)
- the Hub itself

The proxy is the public-facing part of the application.
The default public IP is `''` (equivalent to `'0.0.0.0'`),
which means all interfaces on the machine.
The default port is 8000.
If you want to specify where the Hub application as a whole can be found,
modify these two values.
For example, if you want to listen on a particular IP,
rather than all interfaces,
and you want to use https on port 443,
you can do this at the command-line:

    jupyterhub --ip=10.0.1.2 --port=443

Or in a config file:

```python
c.JupyterHub.ip = '192.168.1.2'
c.JupyterHub.port = 443
```

The Hub service talks to the proxy via a REST API on a separately configurable interface.
By default, this is only on localhost on port 8001.
If you want to run the proxy separate from the Hub,
you may need to configure this ip and port with:

```python
# ideally a private network address
c.JupyterHub.proxy_api_ip = '10.0.1.4'
c.JupyterHub.proxy_api_port = 5432
```

The Hub service also listens only on localhost by default, on port 8081.
The Hub needs needs to be accessible from both the proxy and all
Spawners. When spawning local servers, localhost is fine,
but if *either* the proxy or (more likely) the Spawners will be remote
or isolated in containers, the Hub must listen on an IP that is accessible.

```python
c.JupyterHub.hub_ip = '10.0.1.4'
c.JupyterHub.hub_port = 54321
```

## Security

First of all, since JupyterHub includes authentication,
you really shouldn't run it without SSL (HTTPS).

To enable HTTPS, specify the path to the ssl key and/or cert
(some cert files also contain the key, in which case only the cert is needed):

```python
c.JupyterHub.ssl_key = '/path/to/my.key'
c.JupyterHub.ssl_cert = '/path/to/my.cert'
```

There are two other aspects of JupyterHub network security.
The Hub authenticates its requests to the proxy via an environment variable,
`CONFIGPROXY_AUTH_TOKEN`. If you want to be able to start or restart the proxy
or Hub independently of each other (not always necessary),
you must set this environment variable for both the hub and proxy:

```bash
export CONFIGPROXY_AUTH_TOKEN=`openssl rand -hex 32`
```

If you don't set this, the Hub will generate a random key itself,
which means that any time you restart the Hub you **must also restart the proxy**.
If the proxy is a subprocess of the Hub, this should happen automatically.

The cookie secret is another key, used to encrypt the cookies used for authentication.
If this value changes for the Hub, all single-user servers must also be restarted.
Normally, this value is stored in the file `jupyterhub_cookie_secret`, which can be specified with:

```python
c.JupyterHub.cookie_secret_file = '/path/to/cookie_secret'
```

If the cookie secret file doesn't exist when the Hub starts,
a new cookie secret is generated and stored in the file.

If you would like to avoid the need for files,
the value can be loaded in the Hub process from the `JPY_COOKIE_SECRET` env variable:

```bash
export JPY_COOKIE_SECRET=`openssl rand -hex 1024`
```


## Configuring Authentication

The default Authenticator uses [PAM][] to authenticate system users with their username and password.
The default behavior of this Authenticator is to allow any users with a password on the system to login.
You can restrict which users are allowed to login with `Authenticator.whitelist`:

```python
c.Authenticator.whitelist = {'mal', 'zoe', 'inara', 'kaylee'}
```

After starting the server, you can add and remove users in the whitelist via the `admin` panel,
which brings us to...

```python
c.Authenticator.admin_users = {'mal', 'zoe'}
```

Any users in the admin list are automatically added to the whitelist, if they are not already present.

Admin users have the ability to take actions on users' behalf,
such as stopping and restarting their servers, and adding and removing new users.
If `JupyterHub.admin_access` is True (not default),
then admin users have permission to log in *as other users* on their respective machines,
for debugging. **You should make sure your users know if admin_access is enabled.**

### Adding and removing users

Users can be added and removed to the Hub via the admin panel or REST API.
These users will be added to the whitelist and database.
Restarting the Hub will not require manually updating the whitelist in your config file,
as the users will be loaded from the database.
This means that after starting the Hub once,
it is not sufficient to remove users from the whitelist in your config file.
You must also remove them from the database, either by discarding the database file,
or via the admin UI.

The default PAMAuthenticator is one case of a special kind of authenticator,
called a LocalAuthenticator,
indicating that it manages users on the local system.
When you add a user to the Hub, a LocalAuthenticator checks if that user already exists.
Normally, there will be an error telling you that the user doesn't exist.
If you set the config value

```python
c.LocalAuthenticator.create_system_users = True
```

however, adding a user to the Hub that doesn't already exist on the system will result
in the Hub creating that user via the system `useradd` mechanism.
This option is typically used on hosted deployments of JupyterHub,
to avoid the need to manually create all your users before launching the service.
It is not recommended when running JupyterHub on 'real' machines with regular users.


## Configuring single-user servers

Since the single-user server is an instance of `ipython notebook`,
an entire separate multi-process application,
there is a lot you can configure,
and a lot of ways to express that configuration.

At the JupyterHub level, you can set some values on the Spawner.
The simplest of these is `Spawner.notebook_dir`,
which lets you set the root directory for a user's server.
`~` is expanded to the user's home directory.

```python
c.Spawner.notebook_dir = '~/notebooks'
```

You can also specify extra command-line arguments to the notebook server with

```python
c.Spawner.args = ['--debug', '--profile=PHYS131']
```

Since the single-user server extends the notebook server application,
it still loads configuration from the `ipython_notebook_config.py` config file.
Each user may have one of these files in `$HOME/.ipython/profile_default/`.
IPython also supports loading system-wide config files from `/etc/ipython/`,
which is the place to put configuration that you want to affect all of your users.


## External services

JupyterHub has a REST API that can be used to run external services.
More detail on this API will be added in the future.

### Example: separate notebook-dir from landing url


An example case:

You are hosting JupyterHub on a single cloud server,
using https on the standard https port, 443.
You want to use [GitHub OAuth][oauthenticator] for login,
but need the users to exist locally on the server.
You want users' notebooks to be served from `~/assignments`,
and you also want the landing page to be `~/assignments/Welcome.ipynb`,
instead of the directory listing page that is IPython's default.

Let's start out with `jupyterhub_config.py`:

```python
c = get_config()

import os
pjoin = os.path.join

runtime_dir = os.path.join('/var/run/jupyterhub')
ssl_dir = pjoin(runtime_dir, 'ssl')
if not os.path.exists(ssl_dir):
    os.makedirs(ssl_dir)


# https on :443
c.JupyterHub.port = 443
c.JupyterHub.ssl_key = pjoin(ssl_dir, 'ssl.key')
c.JupyterHub.ssl_cert = pjoin(ssl_dir, 'ssl.cert')

# put the JupyterHub cookie secret and state db
# in /var/run/jupyterhub
c.JupyterHub.cookie_secret_file = pjoin(runtime_dir, 'cookie_secret')
c.JupyterHub.db_file = pjoin(runtime_dir, 'jupyterhub.sqlite')
# or `--db=/path/to/jupyterhub.sqlite` on the command-line

# use GitHub OAuthenticator for local users

c.JupyterHub.authenticator_class = 'oauthenticator.LocalGitHubOAuthenticator'
c.GitHubOAuthenticator.oauth_callback_url = os.environ['OAUTH_CALLBACK_URL']
# create system users that don't exist yet
c.LocalAuthenticator.create_system_users = True

# specify users and admin
c.Authenticator.whitelist = {'rgbkrk', 'minrk', 'jhamrick'}
c.Authenticator.admin_users = {'jhamrick', 'rgbkrk'}

# start users in ~/assignments,
# with Welcome.ipynb as the default landing page
# this config could also be put in
# /etc/ipython/ipython_notebook_config.py
c.Spawner.notebook_dir = '~/assignments'
c.Spawner.args = ['--NotebookApp.default_url=/notebooks/Welcome.ipynb']
```

Using the GitHub Authenticator [requires a few additional env variables][oauth-setup],
which we will need to set when we launch the server:

```bash
export GITHUB_CLIENT_ID=github_id
export GITHUB_CLIENT_SECRET=github_secret
export OAUTH_CALLBACK_URL=https://example.com/hub/oauth_callback
export CONFIGPROXY_AUTH_TOKEN=super-secret
jupyterhub -f /path/to/aboveconfig.py
```

# Further reading

- TODO: troubleshooting
- [Custom Authenticators](authenticators.md)
- [Custom Spawners](spawners.md)


[oauth-setup]: https://github.com/jupyter/oauthenticator#setup
[oauthenticator]: https://github.com/jupyter/oauthenticator
[PAM]: http://en.wikipedia.org/wiki/Pluggable_authentication_module

