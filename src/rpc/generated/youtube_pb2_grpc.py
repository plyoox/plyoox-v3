# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from . import youtube_pb2 as youtube__pb2


class YoutubeStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.VideoPublish = channel.unary_unary(
            "/Youtube.Youtube/VideoPublish",
            request_serializer=youtube__pb2.YoutubeNotification.SerializeToString,
            response_deserializer=youtube__pb2.Empty.FromString,
        )
        self.AddNotification = channel.unary_unary(
            "/Youtube.Youtube/AddNotification",
            request_serializer=youtube__pb2.AddYoutubeNotification.SerializeToString,
            response_deserializer=youtube__pb2.YouTubeUser.FromString,
        )
        self.RemoveNotification = channel.unary_unary(
            "/Youtube.Youtube/RemoveNotification",
            request_serializer=youtube__pb2.RemoveYoutubeNotification.SerializeToString,
            response_deserializer=youtube__pb2.Empty.FromString,
        )


class YoutubeServicer(object):
    """Missing associated documentation comment in .proto file."""

    def VideoPublish(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def AddNotification(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")

    def RemoveNotification(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Method not implemented!")
        raise NotImplementedError("Method not implemented!")


def add_YoutubeServicer_to_server(servicer, server):
    rpc_method_handlers = {
        "VideoPublish": grpc.unary_unary_rpc_method_handler(
            servicer.VideoPublish,
            request_deserializer=youtube__pb2.YoutubeNotification.FromString,
            response_serializer=youtube__pb2.Empty.SerializeToString,
        ),
        "AddNotification": grpc.unary_unary_rpc_method_handler(
            servicer.AddNotification,
            request_deserializer=youtube__pb2.AddYoutubeNotification.FromString,
            response_serializer=youtube__pb2.YouTubeUser.SerializeToString,
        ),
        "RemoveNotification": grpc.unary_unary_rpc_method_handler(
            servicer.RemoveNotification,
            request_deserializer=youtube__pb2.RemoveYoutubeNotification.FromString,
            response_serializer=youtube__pb2.Empty.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler("Youtube.Youtube", rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


# This class is part of an EXPERIMENTAL API.
class Youtube(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def VideoPublish(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/Youtube.Youtube/VideoPublish",
            youtube__pb2.YoutubeNotification.SerializeToString,
            youtube__pb2.Empty.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
        )

    @staticmethod
    def AddNotification(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/Youtube.Youtube/AddNotification",
            youtube__pb2.AddYoutubeNotification.SerializeToString,
            youtube__pb2.YouTubeUser.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
        )

    @staticmethod
    def RemoveNotification(
        request,
        target,
        options=(),
        channel_credentials=None,
        call_credentials=None,
        insecure=False,
        compression=None,
        wait_for_ready=None,
        timeout=None,
        metadata=None,
    ):
        return grpc.experimental.unary_unary(
            request,
            target,
            "/Youtube.Youtube/RemoveNotification",
            youtube__pb2.RemoveYoutubeNotification.SerializeToString,
            youtube__pb2.Empty.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
        )
