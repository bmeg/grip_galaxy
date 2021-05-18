#!/usr/bin/env python

import re
import sys
import yaml
import json
import requests
from requests.auth import HTTPBasicAuth

from concurrent import futures

import grpc
from gripper import gripper_pb2, gripper_pb2_grpc
from google.protobuf import json_format

from bioblend.galaxy import GalaxyInstance

class GalaxyServicer(gripper_pb2_grpc.GRIPSourceServicer):
    def __init__(self, galaxy_url, galaxy_key):
        self.galaxy_url = galaxy_url
        self.galaxy_key = galaxy_key
        self.gi = GalaxyInstance(galaxy_url, key=galaxy_key)

    def GetCollections(self, request, context):
        for i in ["histories", "datasets", "hda"]:
            o = gripper_pb2.Collection()
            o.name = i
            yield o

    def GetCollectionInfo(self, request, context):
        if request.name == "histories":
            o = gripper_pb2.CollectionInfo()
            o.search_fields.extend( ["$.id"] )
            return o
        if request.name == "datasets":
            o = gripper_pb2.CollectionInfo()
            o.search_fields.extend( ["$.id"] )
            return o
        if request.name == "hda":
            o = gripper_pb2.CollectionInfo()
            o.search_fields.extend( ["$.history_id", "$.dataset_id"] )
            return o

    def GetIDs(self, request, context):
        if request.name == "histories":
            for h in self.gi.histories.get_histories():
                o = gripper_pb2.RowID()
                o.id = h['id']
                yield o

        if request.name == "datasets":
            offset = 0
            while True:
                res = self.gi.datasets.get_datasets(offset=offset)
                if len(res) == 0:
                    break
                for d in res:
                    o = gripper_pb2.RowID()
                    o.id = d['id']
                    yield o
                offset += len(res)

        if request.name == "hda":
            for h in self.gi.histories.get_histories():
                for d in self.gi.histories.show_matching_datasets(history_id=h['id']):
                    o = gripper_pb2.RowID()
                    o.id = "%s:%s" % (h['id'], d['id'])
                    yield o


    def GetRows(self, request, context):
        if request.name == "histories":
            for gh in self.gi.histories.get_histories():
                h = self.gi.histories.show_history(gh['id'])
                o = gripper_pb2.Row()
                o.id = gh['id']
                json_format.ParseDict(gh, o.data)
                yield o

        if request.name == "datasets":
            offset = 0
            while True:
                res = self.gi.datasets.get_datasets(offset=offset)
                if len(res) == 0:
                    break
                for gd in res:
                    o = gripper_pb2.Row()
                    d = self.gi.datasets.show_dataset(gd['id'])
                    o.id = d['id']
                    json_format.ParseDict(d, o.data)
                    yield o
                offset += len(res)

        if request.name == "hda":
            for h in self.gi.histories.get_histories():
                for d in self.gi.histories.show_matching_datasets(history_id=h['id']):
                    o = gripper_pb2.Row()
                    o.id = "%s:%s" % (h['id'], d['id'])
                    json_format.ParseDict({"history_id":h['id'], "dataset_id":d['id']}, o.data)
                    yield o

    def GetRowsByID(self, request_iterator, context):
        for req in request_iterator:
            if req.collection == "histories":
                h = self.gi.histories.show_history(req.id)
                o = gripper_pb2.Row()
                o.id = req.id
                o.requestID = req.requestID
                json_format.ParseDict(h, o.data)
                yield o
            if req.collection == "datasets":
                o = gripper_pb2.Row()
                d = self.gi.datasets.show_dataset(req.id)
                o.id = req.id
                o.requestID = req.requestID
                json_format.ParseDict(d, o.data)
                yield o
            if req.collection == "hda":
                o = gripper_pb2.Row()
                o.id = req.id
                o.requestID = req.requestID
                h, d = req.id.split(":")
                json_format.ParseDict({"history_id":h, "dataset_id":d}, o.data)
                yield o

    def GetRowsByField(self, req, context):
        if req.collection == "hda":
            if req.field == "$.history_id":
                for d in self.gi.histories.show_matching_datasets(history_id=req.value):
                    o = gripper_pb2.Row()
                    o.id = "%s:%s" % (req.value, d['id'])
                    json_format.ParseDict({"history_id":req.value, "dataset_id":d['id']}, o.data)
                    yield o
            if req.field == "$.dataset_id":
                d = self.gi.datasets.show_dataset(req.value)
                if d is not None:
                    o = gripper_pb2.Row()
                    o.id = "%s:%s" % (d['history_id'], req.value)
                    json_format.ParseDict({"dataset_id":req.value, "history_id":d['history_id']}, o.data)
                    yield o

def serve(port, galaxy_url, galaxy_key):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    gripper_pb2_grpc.add_GRIPSourceServicer_to_server(
      GalaxyServicer(galaxy_url, galaxy_key), server)
    server.add_insecure_port('[::]:%s' % port)
    server.start()
    print("Serving: %s" % (port))
    server.wait_for_termination()


if __name__ == "__main__":
    serve(50051, sys.argv[1], sys.argv[2])
