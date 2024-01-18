# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: twitch.proto
# Protobuf Python Version: 4.25.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x0ctwitch.proto\x12\x06Twitch\x1a\x1fgoogle/protobuf/timestamp.proto\"\xba\x01\n\x16TwitchLiveNotification\x12\x10\n\x08guild_id\x18\x01 \x01(\x03\x12\x11\n\tstream_id\x18\x02 \x01(\x03\x12\x0f\n\x07user_id\x18\x03 \x01(\x05\x12\x14\n\x0cviewer_count\x18\x04 \x01(\x05\x12\x0c\n\x04name\x18\x05 \x01(\t\x12\r\n\x05title\x18\x06 \x01(\t\x12\x15\n\rthumbnail_url\x18\x07 \x01(\t\x12\x0c\n\x04game\x18\x08 \x01(\t\x12\x12\n\nstarted_at\x18\t \x01(\x04\".\n\x19TwitchOfflineNotification\x12\x11\n\tstream_id\x18\x01 \x01(\x03\"7\n\x15\x41\x64\x64TwitchNotification\x12\x10\n\x08guild_id\x18\x01 \x01(\x03\x12\x0c\n\x04name\x18\x02 \x01(\t\"=\n\x18RemoveTwitchNotification\x12\x0f\n\x07user_id\x18\x01 \x01(\x05\x12\x10\n\x08guild_id\x18\x02 \x01(\x03\"/\n\tOAuthCode\x12\x0c\n\x04\x63ode\x18\x02 \x01(\t\x12\x14\n\x0credirect_uri\x18\x04 \x01(\t\"X\n\nTwitchUser\x12\n\n\x02id\x18\x01 \x01(\x05\x12\r\n\x05login\x18\x02 \x01(\t\x12\x14\n\x0c\x64isplay_name\x18\x03 \x01(\t\x12\x19\n\x11profile_image_url\x18\x04 \x01(\t\"\x1f\n\x10OAuthUrlResponse\x12\x0b\n\x03url\x18\x01 \x01(\t\"5\n\x0e\x43reateOAuthUrl\x12\r\n\x05state\x18\x01 \x01(\t\x12\x14\n\x0credirect_uri\x18\x02 \x01(\t\"\x07\n\x05\x45mpty2\xb8\x03\n\x12TwitchNotification\x12\x43\n\x10LiveNotification\x12\x1e.Twitch.TwitchLiveNotification\x1a\r.Twitch.Empty\"\x00\x12I\n\x13OfflineNotification\x12!.Twitch.TwitchOfflineNotification\x1a\r.Twitch.Empty\"\x00\x12=\n\x12OAuthAuthorization\x12\x11.Twitch.OAuthCode\x1a\x12.Twitch.TwitchUser\"\x00\x12\x42\n\x0cOAuthBaseUrl\x12\x16.Twitch.CreateOAuthUrl\x1a\x18.Twitch.OAuthUrlResponse\"\x00\x12\x46\n\x0f\x41\x64\x64Notification\x12\x1d.Twitch.AddTwitchNotification\x1a\x12.Twitch.TwitchUser\"\x00\x12G\n\x12RemoveNotification\x12 .Twitch.RemoveTwitchNotification\x1a\r.Twitch.Empty\"\x00\x62\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'twitch_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
    DESCRIPTOR._options = None
    _globals['_TWITCHLIVENOTIFICATION']._serialized_start = 58
    _globals['_TWITCHLIVENOTIFICATION']._serialized_end = 244
    _globals['_TWITCHOFFLINENOTIFICATION']._serialized_start = 246
    _globals['_TWITCHOFFLINENOTIFICATION']._serialized_end = 292
    _globals['_ADDTWITCHNOTIFICATION']._serialized_start = 294
    _globals['_ADDTWITCHNOTIFICATION']._serialized_end = 349
    _globals['_REMOVETWITCHNOTIFICATION']._serialized_start = 351
    _globals['_REMOVETWITCHNOTIFICATION']._serialized_end = 412
    _globals['_OAUTHCODE']._serialized_start = 414
    _globals['_OAUTHCODE']._serialized_end = 461
    _globals['_TWITCHUSER']._serialized_start = 463
    _globals['_TWITCHUSER']._serialized_end = 551
    _globals['_OAUTHURLRESPONSE']._serialized_start = 553
    _globals['_OAUTHURLRESPONSE']._serialized_end = 584
    _globals['_CREATEOAUTHURL']._serialized_start = 586
    _globals['_CREATEOAUTHURL']._serialized_end = 639
    _globals['_EMPTY']._serialized_start = 641
    _globals['_EMPTY']._serialized_end = 648
    _globals['_TWITCHNOTIFICATION']._serialized_start = 651
    _globals['_TWITCHNOTIFICATION']._serialized_end = 1091
# @@protoc_insertion_point(module_scope)
