#!/usr/bin/env python
# coding: utf-8

# # Cluster Setup
# 
# This should be used to create and shutdown a cluster which can be shared between different notebooks. The cluster name will be displayed and that can be used for connecting to this cluster in other notebooks.

from dask_gateway import Gateway


gateway = Gateway()
options = gateway.cluster_options()
# Use 4 GB or some notebooks will fail.
options.worker_memory = 4


# Make new cluster. 
# Remember to use Dashboard (link in output below) to check that all workers are running.
num_workers = 16
cluster = gateway.new_cluster(options)
cluster.scale(num_workers)
client = cluster.get_client()
print(cluster.name)
client


# Stop the cluster.
cluster_name = cluster.name
gateway.stop_cluster(cluster_name)

