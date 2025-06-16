# PoC Task Breakdown

This document outlines the engineering tasks required to build the "restreaming as support" Proof of Concept.

---

## Epic 1: Coordinator Server

The central service responsible for orchestration, verification, and reward calculation.

-   **[Issue #1] Setup Basic Server & Database:**
    -   Initialize a new FastAPI or Express.js project.
    -   Set up a basic PostgreSQL database schema with tables for `streams`, `nodes`, and `probe_results`.
    -   Create a Dockerfile for the Coordinator server.

-   **[Issue #2] Implement Core Endpoints:**
    -   `POST /streams`: Endpoint for a Sponsor to register a stream and a (fake) token balance.
    -   `GET /streams`: Endpoint for Node Clients to discover available streams.
    -   `POST /nodes/heartbeat`: Endpoint for Node Clients to announce their presence and report their `/stats.json` URL.

-   **[Issue #3] Implement Stats Collector Service:**
    -   Create a background worker that periodically polls the `/stats.json` endpoint for every active node.
    -   It should parse the JSON and store the results (uptime, status) in the `probe_results` table.

-   **[Issue #4] Implement Spot-Check Prober Service:**
    -   Create a background worker that runs at random intervals.
    -   It will select a "healthy" node and attempt a real RTMP connection using `ffprobe` or a similar library.
    -   It will log success/failure to the `probe_results` table and flag any fraudulent nodes.

-   **[Issue #5] Implement Payout & Dashboard Logic:**
    -   Create a service that calculates rewards based on the data in `probe_results`.
    -   Create a simple, read-only HTML dashboard to display active streams, nodes, and their measured uptime.

---

## Epic 2: Node Client

The Dockerized package that operators will run. The goal is zero-friction setup.

-   **[Issue #6] Create Node Client Wrapper:**
    -   Write a simple Python or Bash script that acts as the entrypoint for the Docker container.
    -   This script will be responsible for starting the `rtmp_relay` server and sending heartbeats to the Coordinator.

-   **[Issue #7] Dockerize the Node Client:**
    -   Create a `Dockerfile` that packages the wrapper script and the `elnormous/rtmp_relay` server together.
    -   The container should be configurable via environment variables (`COORDINATOR_URL`, `STREAM_ID`, etc.).

---

## Epic 3: Infrastructure & Documentation

The supporting elements needed to run the PoC.

-   **[Issue #8] Deploy Central Ingest Server:**
    -   Set up a cloud instance running `elnormous/rtmp_relay` in "host" mode to act as the single ingest point for the PoC.

-   **[Issue #9] Deploy Coordinator Server:**
    -   Deploy the Coordinator server application and its database to a cloud environment.

-   **[Issue #10] Create Tester Documentation:**
    -   Write a simple `README.md` for the PoC testers with clear, step-by-step instructions on how to run the Node Client Docker container.

--- 