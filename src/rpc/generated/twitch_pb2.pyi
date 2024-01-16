from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class TwitchLiveNotification(_message.Message):
    __slots__ = ("guild_id", "stream_id", "name", "title", "thumbnail_url", "game")
    GUILD_ID_FIELD_NUMBER: _ClassVar[int]
    STREAM_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    THUMBNAIL_URL_FIELD_NUMBER: _ClassVar[int]
    GAME_FIELD_NUMBER: _ClassVar[int]
    guild_id: int
    stream_id: int
    name: str
    title: str
    thumbnail_url: str
    game: str
    def __init__(self, guild_id: _Optional[int] = ..., stream_id: _Optional[int] = ..., name: _Optional[str] = ..., title: _Optional[str] = ..., thumbnail_url: _Optional[str] = ..., game: _Optional[str] = ...) -> None: ...

class TwitchOfflineNotification(_message.Message):
    __slots__ = ("stream_id",)
    STREAM_ID_FIELD_NUMBER: _ClassVar[int]
    stream_id: int
    def __init__(self, stream_id: _Optional[int] = ...) -> None: ...

class AddTwitchNotification(_message.Message):
    __slots__ = ("guild_id", "name")
    GUILD_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    guild_id: int
    name: str
    def __init__(self, guild_id: _Optional[int] = ..., name: _Optional[str] = ...) -> None: ...

class RemoveTwitchNotification(_message.Message):
    __slots__ = ("user_id", "guild_id")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    GUILD_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: int
    guild_id: int
    def __init__(self, user_id: _Optional[int] = ..., guild_id: _Optional[int] = ...) -> None: ...

class OAuthCode(_message.Message):
    __slots__ = ("code", "redirect_uri")
    CODE_FIELD_NUMBER: _ClassVar[int]
    REDIRECT_URI_FIELD_NUMBER: _ClassVar[int]
    code: str
    redirect_uri: str
    def __init__(self, code: _Optional[str] = ..., redirect_uri: _Optional[str] = ...) -> None: ...

class TwitchUser(_message.Message):
    __slots__ = ("id", "login", "display_name", "profile_image_url")
    ID_FIELD_NUMBER: _ClassVar[int]
    LOGIN_FIELD_NUMBER: _ClassVar[int]
    DISPLAY_NAME_FIELD_NUMBER: _ClassVar[int]
    PROFILE_IMAGE_URL_FIELD_NUMBER: _ClassVar[int]
    id: int
    login: str
    display_name: str
    profile_image_url: str
    def __init__(self, id: _Optional[int] = ..., login: _Optional[str] = ..., display_name: _Optional[str] = ..., profile_image_url: _Optional[str] = ...) -> None: ...

class OAuthUrlResponse(_message.Message):
    __slots__ = ("url",)
    URL_FIELD_NUMBER: _ClassVar[int]
    url: str
    def __init__(self, url: _Optional[str] = ...) -> None: ...

class CreateOAuthUrl(_message.Message):
    __slots__ = ("state", "redirect_uri")
    STATE_FIELD_NUMBER: _ClassVar[int]
    REDIRECT_URI_FIELD_NUMBER: _ClassVar[int]
    state: str
    redirect_uri: str
    def __init__(self, state: _Optional[str] = ..., redirect_uri: _Optional[str] = ...) -> None: ...

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...
