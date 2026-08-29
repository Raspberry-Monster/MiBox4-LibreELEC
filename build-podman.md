# Build container with Podman

This is the Podman version of the container instructions in the LibreELEC
`tools/docker/README.md`. Podman is compatible with the commands used here and
does not require a daemon.

## Available build containers

The container definitions currently include:

**Ubuntu**

- `jammy` (Ubuntu 22.04)
- `noble` (Ubuntu 24.04)
- `questing` (Ubuntu 25.10)
- `resolute` (Ubuntu 26.04)

**Debian**

- `bookworm` (Debian 12)
- `trixie` (Debian 13)

Install Podman using your distribution's package manager before starting.

## Build the image

Change to the root of your LibreELEC.tv checkout first (adjust the path if you
cloned it elsewhere):

```bash
cd ~/LibreELEC.tv
```

The example uses the
Ubuntu 22.04 (`jammy`) container; replace `jammy` with another directory above
if needed.

```bash
podman build --pull=always -t libreelec tools/docker/jammy
```

## Build LibreELEC inside the container

The checkout must contain the LibreELEC `Makefile`. Mount the current directory
at `/build` and run the desired build command:

```bash
podman run --rm --log-driver none --userns=keep-id \
  -v "$(pwd)":/build -w /build -it \
  libreelec make image
```

Pass build-system settings with `--env`, `-e`, or `--env-file`, for example:

```bash
podman run --rm --log-driver none --userns=keep-id \
  -v "$(pwd)":/build -w /build -it \
  -e PROJECT=Amlogic -e ARCH=aarch64 -e DEVICE=AMLGX -e UBOOT_SYSTEM=mibox4 \
  libreelec make image
```

This selects the dedicated Mi Box 4 board target and produces an image whose
name ends in `-mibox4.img.gz`. The image already contains the fixed Mi Box 4
DTB selection; it is not the AMLGX Generic Box Image.

`--rm` removes the stopped container while retaining the `libreelec` image.
`--userns=keep-id` maps the host user's UID and GID into the rootless container,
so the non-root build user can write generated files to the mounted checkout.
Ensure the checkout is writable by your host user. On macOS or Windows, it must also
be shared with the Podman machine and `$(pwd)` must resolve to a path visible
inside that machine.

For more build options, see the
[LibreELEC build basics](https://wiki.libreelec.tv/development/build-basics.md)
documentation.
