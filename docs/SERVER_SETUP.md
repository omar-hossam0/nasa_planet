# Server setup — Azure VM

One-time preparation of the Linux host that runs Trend Detective.

> **Bootstrap is not part of normal deployment.** It runs once, when the VM is created or
> repaired. Pushes to `main` never run it.

---

## 1. Target server

| Item | Value |
|---|---|
| Provider | Microsoft Azure |
| VM name | `nasa` |
| Resource group | `nasa_group` |
| Region | East US |
| Public IP | `172.174.114.48` |
| OS | Ubuntu (22.04 / 24.04 supported) |
| SSH port | 22 |
| Expected user | `azureuser` |

Verify the IP, user and port before relying on them — an unverified assumption here breaks
the whole pipeline.

---

## 2. Requirements

- SSH key authentication to the VM (password login is not used by CI).
- A user able to run `sudo` **once**, for the bootstrap only.
- Inbound TCP 22 (SSH) and TCP 80 (frontend) open in the Azure NSG.
- At least 2 GB RAM and 10 GB free disk for two images plus build cache.
- No GPU, no Azure subscription credentials, no database server.

---

## 3. What bootstrap does

`scripts/server/bootstrap.sh`:

1. Verifies the OS, architecture, RAM, disk and free inodes.
2. Installs base packages (`ca-certificates`, `curl`, `gnupg`, `jq`, `tar`).
3. Installs Docker Engine, CLI, containerd, Buildx and the Compose plugin from Docker's
   **official** apt repository — never a `curl | sh` script.
4. Enables and starts the Docker service.
5. Creates `/opt/trend-detective` with `state/` and `logs/`.
6. Adds `azureuser` to the `docker` group (documented, because docker group ≈ root).
7. Reports which ports are already bound.
8. Verifies the installation and only then writes
   `/var/lib/trend-detective/bootstrap.version`.

It does **not** touch SSH configuration, `authorized_keys`, firewall rules or Azure NSGs.

---

## 4. Running it

From your machine:

```bash
scp scripts/server/bootstrap.sh azureuser@172.174.114.48:/tmp/bootstrap.sh
ssh azureuser@172.174.114.48 'sudo bash /tmp/bootstrap.sh'
```

Or, if the repository is already cloned on the host:

```bash
cd /opt/trend-detective && sudo ./scripts/server/bootstrap.sh
```

Then verify:

```bash
ssh azureuser@172.174.114.48 'sudo bash /opt/trend-detective/scripts/server/verify.sh'
```

`verify.sh` is read-only. It exits non-zero when the host is not ready.

---

## 5. Idempotency

The script is safe to re-run. Every step checks before acting:

| Step | Already present | Behaviour |
|---|---|---|
| Docker install | `docker` + `compose` respond | skipped |
| apt key / repo | `/etc/apt/keyrings/docker.asc` exists | not re-downloaded |
| Directories | `install -d` | no-op, permissions refreshed |
| Docker group | user already in group | skipped |
| Marker | exists | logged, repaired if needed |

It never deletes images, volumes or application data, and never overwrites existing
configuration files.

---

## 6. Permissions

- Bootstrap needs `sudo` **once**. Afterwards the deploy user only needs `docker` group
  membership.
- Docker group membership is equivalent to root on the host. This is a known, accepted
  trade-off for a single-purpose demo VM; a hardened deployment would use a rootless Docker
  daemon.
- No passwordless sudo is configured by this script.

---

## 7. Recovering from a partial bootstrap

The marker is written **only** after verification passes, so a missing marker means the
host is not ready.

```bash
sudo bash scripts/server/bootstrap.sh    # re-run; it repairs what is missing
sudo bash scripts/server/verify.sh       # confirm
cat /var/lib/trend-detective/bootstrap.version
```

If apt is in a broken state, fix it first (`sudo apt-get -f install`) and re-run.

---

## 8. Initial-setup limitations

- The script was written and syntax-checked in the development environment, but **it has not
  been executed on the Azure VM** — no SSH key is available outside GitHub Secrets.
- The first real execution must be done by the repository owner (direct SSH) or by running
  the workflow with the key configured.
- Until bootstrap has run, `deploy.sh` exits with
  `host not bootstrapped (/var/lib/trend-detective/bootstrap.version missing)`.
