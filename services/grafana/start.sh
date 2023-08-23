#!/usr/bin/env bash
docker volume create grafana-storage
docker run -d --network="host" -p 9090:9090 -v /home/ec2-user/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus
docker run -it --rm -d --name=grafana -p 3000:3000 -v grafana-storage:/var/lib/grafana grafana/grafana-oss:latest
