# MicroFVS
This repository includes the code for an API employed by a web service developed by [Vibrant Planet](https://www.vibrantplanet.net/) for executing simulations using the [Forest Vegetation Simulator (FVS)](https://www.fs.usda.gov/managing-land/forest-management/fvs), a forest growth-and-yield developed by the USDA Forest Service. 

This API is the backbone of a microservice (hence the name "MicroFVS") allowing users to interact with FVS in a contained and well-maintained environment without requiring the installation of any specific software. The core functionality enabled by the API is the execution of FVS simulations and retrieval of results from them in a standardized format (JSON).

The API exposes basic templates and building blocks for constructing plain-text FVS Keyfiles which provide the instructions to FVS for executing a growth-and-yield simulation on a single forest stand. These resources are intended to help users develop their own Keyfile templates and to use their own management and natural disturbance recipes in these simulations. 

The API also provides access to a [national compendium of silvicultural treatments](https://doi.org/10.2737/RDS-2022-0037)[^1] prepared by a team of silviculture experts from each National Forest System Region and Research Station of the US Forest Service in the form of FVS Keyword Component (KCP) files.

[^1]: Houtman, Rachel M.; Day, Michelle A.; Hooten, Erin; Ritchie, Martin W.; Jain, Theresa B.; Schuler, Thomas M. 2023. Forest Vegetation Simulator keyword component (KCP) files associated with the compendium of silvicultural treatments for forest types in the United States. Updated 04 June 2024. Fort Collins, CO: Forest Service Research Data Archive. https://doi.org/10.2737/RDS-2022-0037

## Getting Started
You'll need to have Docker and Git installed to be able to get this working. 

### Clone this repository
Use the GitHub website to clone this repo to your machine, or use the command line:
`git clone <repository-url>`

### Build the Docker container
Navigate to the root of your local clone of this repository on the command line, then build the container. FVS binaries are copied from a pinned release image (`ghcr.io/vibrant-planet-open-science/usfs-fvs:FS2026.1` by default, but feel free to try `ghcr.io/vibrant-planet-open-science/usfs-fvs:latest`), so the build should complete in a few minutes:
```
cd microfvs
docker build --target microfvs -t microfvs .
```
To use a different FVS release tag, pass `FVS_TAG` as a build argument, for example:
```
docker build --target microfvs --build-arg FVS_TAG=FS2026.1 -t microfvs .
```
or 
```
docker build --target microfvs --build-arg FVS_TAG=latest -t microfvs .
```

### Run the API locally inside the Docker container
The Docker container running the MicroFVS server listens on port 80. Forward that to your local machine to communicate with the service—for example:

```bash
docker run -p 8080:80 microfvs
```

The container starts Uvicorn with `--root-path /microfvs`, matching typical reverse-proxy deployments. Uvicorn does **not** infer this from `X-Forwarded-Prefix`; it is set in the image `CMD`.

To run at the site root instead (for example a quick local smoke test without nginx), override the command:

```bash
docker run -p 8080:80 microfvs uvicorn microfvs.main:app --host 0.0.0.0 --port 80
```

### Open a web browser and explore the documentation
With the default `/microfvs` root path, access the docs through a reverse proxy at `http://localhost:<your-port>/microfvs/docs` (see below), or on a host where the service is mounted at that prefix—for example `https://example.org/microfvs/docs`.

If you overrode the command to run at the site root, use `http://localhost:<your-port>/docs` instead.

### Reverse proxy (recommended for local and production)
When the proxy **strips** the path prefix before forwarding requests to MicroFVS (the usual nginx pattern), Uvicorn's `--root-path` must match the external prefix. That keeps the OpenAPI/Swagger UI and the landing-page link to `/docs` working under the prefix.

**Example nginx location** (prefix stripped before the app sees the request):

```nginx
location /microfvs/ {
    proxy_pass http://127.0.0.1:8080/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

With this setup, clients reach `https://example.org/microfvs/docs`; nginx forwards `/docs` to the container. Do not hit the container directly at `/docs` while `--root-path` is set—the Swagger UI expects the prefixed URL.

### Utilize the web service
Once the web service is up-and-running, interact with endpoints using the external URL pattern—for example `https://example.org/microfvs/run` when the default root path is in effect, or `http://localhost:<your-port>/<endpoint>` when running at the site root locally. 


## Development

A **dev container** is provided under [`.devcontainer/`](.devcontainer/) for VS Code and Cursor. Open the repository with **Dev Containers: Reopen in Container** to get the `dev` Docker target, Python tooling, and extensions preconfigured. On first open, `postCreateCommand` runs `uv sync --frozen --extra dev` (creating a project-local `.venv` in your clone, gitignored) and installs pre-commit hooks. After pulling changes that touch the Dockerfile or lockfile, **rebuild** the dev container (or run `uv sync --extra dev` manually).

The `.venv` directory lives on your host via the bind-mounted workspace (Linux binaries from the container). You can delete it and re-run `uv sync --extra dev` to recreate.

To run the API locally inside the dev container (port 8000 is forwarded automatically):

```bash
uv run uvicorn microfvs.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open `http://localhost:8000/docs` on your machine. The dev container serves at the site root for convenience; the production Docker image uses `--root-path /microfvs` intended for use behind a reverse proxy.

If you don't want to use a dev container, install dev dependencies and hooks the same way before opening a pull request:

```bash
uv sync --extra dev
uv pre-commit install
```

Hooks run on each commit (secret scan, Ruff, mypy). Run them manually with `pre-commit run --all-files`. CI runs the same checks on on files included in pull requests via the Lint workflow.