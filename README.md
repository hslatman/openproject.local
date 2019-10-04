# openproject.local
Local OpenProject (https://www.openproject.org/) instance using Docker Compose

## Description

This repository contains an example setup for running the Community Edition of [OpenProject](https://www.openproject.org/) using Docker Compose.
The configuration is based on the description for [using OpenProject with Docker](https://www.openproject.org/docker/), but uses Docker Compose for more easily managing the containers configuration.

## Usage

1. Clone the repository
1. Copy the .env.dist file to .env and change the (Postgres) environment variables to your liking
1. Run _docker-compose up -d_

When you run the command for the first time, it will take a while to download the images for OpenProject and PostgreSQL.
The OpenProject container will configure itself with default settings and the environment settings for the database configuration.
After the containers started successfully, the application can be found at http://127.0.0.1:8080 by default with default access credentials.

## Import

This repository also contains a small Python script that can be used to import Work Packages to an OpenProject instance (including the one running locally in Docker containers).
An API Key is required to allow the script to authenticate itself to OpenProject, which can be created while being logged in to OpenProject.

## TODO

* Improve import of relations between Work Packages