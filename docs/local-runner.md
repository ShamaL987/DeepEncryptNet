# DeepEncryptNet Local Runner Setup

## Overview

The `local-runner` folder is the local runnable package for DeepEncryptNet. The user does not need the full source code repository in order to run the system locally. The only requirement is to copy the `local-runner` folder to any location on the computer and use the provided batch files.

This runner package is designed to make the local setup simple and repeatable. Once started, it will pull the required Docker image, apply the local configuration, mount the current runner folder as the required files directory, and start the DeepEncryptNet system.

## How to Run the System

1. Copy the `local-runner` folder anywhere on the computer and copy the tracker-exe/deepencryptnet_local.exe file to the same folder.
2. Open the folder.
3. Double-click `run.bat`.
4. Wait until the Docker image is pulled and the container starts.
5. after the container starts, run configure.bat.
6. run the tracker-exe/deepencryptnet_local.exe file and select the port to monitor.
7. run the pipline from UI

After the startup process is completed, the DeepEncryptNet application will be available locally through the browser.

## UI Access

Once the system is running, the user interface can be accessed using the following local address:

```text
http://localhost:8000
```

If the configured port is changed in the Docker Compose file, the URL should be updated accordingly.

```text
Default username: admin@deepencryptnet.com
Default password: TempPassword123!
```

## How to Stop the System

To stop the running DeepEncryptNet local instance:

1. Open the same `local-runner` folder.
2. Double-click `stop.bat`.

This will stop the local Docker container started by the runner package.

## Folder Structure

A recommended structure for the local runner package is shown below.

```text
local-runner/
├── docker-compose.yml
├── .env
├── run.bat
├── stop.bat
└── local_setup.md
```

## Configuration Details

### Port Configuration

If the local application port or database port needs to be changed, update the `docker-compose.yml` file.

Example:

```yaml
ports:
  - "8000:8000"
  - "5432:5432"
```

In this configuration:

* The application UI is exposed through local port `8000`
* The database is exposed through local port `5432`

If a different port is required on the local machine, the left side of each mapping can be changed.

Example:

```yaml
ports:
  - "8080:8000"
  - "5433:5432"
```

With this change, the UI would then be accessible at:

```text
http://localhost:8080
```

### Environment Configuration

If runtime values need to be changed, update the related values in the `docker-compose.yml` file or `.env` file, depending on how the runner package is configured.

Typical configuration values that may need to be updated include:

* `APP_ENV`
* `ADMIN_BOOTSTRAP_TOKEN`
* `JWT_SECRET_KEY`
* `JWT_ALGORITHM`
* `JWT_TIME`
* `API_TOKEN_ENCRYPTION_KEY`
* `DATABASE_HOST`
* `DATABASE_PORT`
* `DATABASE_NAME`
* `DATABASE_USER`
* `DATABASE_PASSWORD`
* `POSTGRES_DB`
* `POSTGRES_USER`
* `POSTGRES_PASSWORD`

These values control the local runtime environment, authentication-related settings, and database connectivity.

## Volume Mounting Behavior

The runner package is designed so that the folder containing the batch file can be used directly as the mounted local directory for the container.

This means the user can copy the `local-runner` folder to any place on the computer and run it from there. During startup, that local folder is mounted into the container path used by the application for file access.

Container mount target:

```text
/app/data/files
```

This allows the system to work using the current runner folder location without requiring manual path reconfiguration each time the folder is moved.

## Requirements

Before running the local setup, ensure the following are available on the computer:

* Docker Desktop installed
* Docker running successfully
* Docker Compose support available through Docker Desktop
* Internet access available for pulling the Docker image, if it is not already cached locally

## Notes

* The `run.bat` file is responsible for starting the system.
* The `stop.bat` file is responsible for stopping the system.
* If configuration values are modified, restart the system for the changes to take effect.
* If the Docker image is private, Docker login may be required before running the batch file.
* If the Docker image is public, no separate Docker Hub login is required for pulling the image.

## Summary

The local setup process is intentionally simple:

1. Copy the `local-runner` folder anywhere on the computer.
2. Double-click `run.bat`.
3. Access the UI from the browser using `[http://lo](http://lo)
