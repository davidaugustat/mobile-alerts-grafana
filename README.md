![Example Grafana dashboard that can be built with using project](img/example-dashboard.png)
Example for a Grafana dashboard that can be built using this project

# Mobile Alerts Grafana Dashboard
This project
1. Periodically fetches the current temperature from one or multiple [Mobile Alerts](https://mobile-alerts.eu/) temperature sensors.
2. Stores the retrieved values in a TimescaleDB database for **long-term** storage.
3. Makes the stored measurements available to a Grafana instance.

This project can be used to create a nice Grafana dashboard visualizing temperature data from your smart home.

Additional features:
- Compatible with [Traefik](https://traefik.io/traefik) for easy hosting with a domain and HTTPS
- SQL and CSV data export
- Healthcheck restarts the data fetcher if no new data arrives for more than 30 minutes

## Data Flow Diagram
This diagram visualized the flow of data:
![](img/data-flow-diagram.png)

The Mobile Alerts REST API is documented in [this PDF file](https://mobile-alerts.eu/info/public_server_api_documentation.pdf).

## Tech Stack
- [Docker Compose](https://docs.docker.com/compose/) (everything is a container)
- [Python](https://www.python.org/) (data fetcher script)
- [TimescaleDB](https://github.com/timescale/timescaledb) for data storage
- [Grafana](https://grafana.com/) for data visualization
- [Bash](https://en.wikipedia.org/wiki/Bash_(Unix_shell)) scripts for data export

## Two Options: Direct Ports or Traefik
There are two options to host this project:
- **Option 1 - Direct Ports:** Direct Ports: This directly exposes Grafana on Port 3000 of your machine.
  - This option is best-suited when you plan to host the project inside your home network.
  - The file `docker-compose.ports.yml` corresponds to this option.
- **Option 2 - Traefik:** This makes the Grafana container available to a Traefik container that is already present on your machine.
  - You need to set up Traefik yourself. The Traefik container is not part of this project.
  - This option is best-suited when you want to host this project on a VPS. You can set up Traefik such that you can reach Grafana through a domain and have HTTPS encryption.

## Prerequisites
- Linux machine with access to the internet (to fetch data from the Mobile Alerts API)
- Docker and Docker Compose

## Getting Started
### 1. Clone the Repo to Your Server
```bash
$ git clone https://github.com/davidaugustat/mobile-alerts-grafana.git
```
### 2. Create a `.env` File
Rename the `.env.example` file to `.env` and change at least the following values:
- `DB_PASSWORD`: Use a secure random-generated password.
- `SENSOR_IDS`: The Mobile Alerts sensor IDs you want to track as a comma-separated string (no spaces). You can find these IDs on the back of your sensor devices.
- `GF_SECURITY_ADMIN_PASSWORD`: Default password for the Grafana admin user. Use a secure random-generated password.

If you want to use the "Traefik" approach, you should also set the variable `GRAFANA_DOMAIN` to the domain where you want to host the project.

### 3. Spin up the Containers
Navigate to this repository's root directory and then run either
```bash
$ docker-compose -f docker-compose.ports.yml up -d
```
if you want to use the "Direct Ports" approach or
```bash
$ docker-compose -f docker-compose.traefik.yml up -d
```
if you want to use the "Traefik" approach.

You can then navigate to your Grafana URL, e.g. 
- `http:localhost:3000` if you used the "Direct Ports" approach or
- `https://sensors.example.com` if you used the "Traefik" approach.
There you can log in with the Grafana credentials you defined in your `.env` file.

## Configuring Grafana
TODO

## Exporting / Backups
TODO

## How to Set Up Traefik (Example)
There are numerous ways to configure Traefik. Here is an example `docker-compose.yml` file for a Traefik instance.
This Traefik container

- offers HTTPS (TLS encryption) through [Let's Encrypt](https://letsencrypt.org/)
- auto-redirects from HTTP to HTTPS
- makes use of an external Docker network `traefik-proxy`. Other Docker containers (like this project) can connect their containers to this network to make them available to `Traefik`.


```yaml
services:
  traefik:
    image: traefik:v3.3
    command:
      # Docker as provider:
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"

      # Endpoints:
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"

      # Let's Encrypt:
      - "--certificatesresolvers.myresolver.acme.tlschallenge=true"
      - "--certificatesresolvers.myresolver.acme.email=mail@example.com"
      - "--certificatesresolvers.myresolver.acme.storage=/letsencrypt/acme.json"

      # auto-redirect HTTP to HTTPS (for all services):
      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
      - "--entrypoints.web.http.redirections.entrypoint.scheme=https"

    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "letsencrypt:/letsencrypt"
    networks:
      - traefik-proxy
    restart: unless-stopped

volumes:
  letsencrypt:

networks:
  traefik-proxy:
    external: true
```

To set up Traefik:
1. Save this file in a directory `Traefik` as `docker-compose.yml`
2. Execute the following command to create the external network `traefik-proxy`
    ```bash
    $ docker network create traefik-proxy
    ```
3. From the directory `Traefik` run
    ```bash
    $ docker compose up -d
    ```
    to launch Traefik.