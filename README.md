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
Navigate to the root of your local clone of this repository on the command line, then build the container:
```
cd microfvs
docker build -t microfvs .
```
This may take a while because it is building FVS from source (currently pinned to FVS release `FS2024.4` to ensure reproducible build on that passes basic tests for FVS simulations on Ubuntu OS). Go make a cup of coffee. 

### Run the API locally inside the Docker container
The Docker container running the MicroFVS server should be accessible on port 80, you'll need to forward that to your local machine to be able to communicate with the MicroFVS service. To forward to localhost 8080, for example:
`docker run -p 8080:80 microfvs`

### Open a web browser and explore the documentation
Use your web browser to go to the URL `http://localhost:<your-port>/docs` and you should the auto-generated FastAPI documentation for the MicroFVS web service. 

### Utilize the web service
Once the web service is up-and-running inside your Docker container, you should be able to interact with it by making requests to the MicroFVS endpoints using the pattern `http://localhost:<your-port>/<endpoint>` along with any parameters that might be involved in making GET or POST requests using the API. You should be able to launch example requests from the documentation page, or from your favorite programming language that can prepare web requests like Python or R. Stay tuned as we develop wrappers for the API to make access from Python and R simpler. 