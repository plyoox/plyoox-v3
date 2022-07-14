from typing import TypedDict, Literal, Any


class _AnilistTitle(TypedDict):
    english: str
    romaji: str
    native: str


class _AnilistDate(TypedDict):
    year: int
    month: int
    day: int


class _AnilistTrailer(TypedDict):
    site: str
    id: str


class _AnilistTag(TypedDict):
    name: str


class _AnilistRaking(TypedDict):
    type: Literal["POPULAR", "RATED"]
    allTime: bool


class AnilistSearchResponse(TypedDict):
    id: int
    title: _AnilistTitle
    description: str


class AnilistDetailedResponse(TypedDict):
    id: int
    title: _AnilistTitle
    description: str
    status: Literal["RELEASING", "FINISHED", "NOT_YET_AVAILABLE", "CANCELLED", "HIATUS"]
    startDate: _AnilistDate
    endDate: _AnilistDate
    episodes: int
    season: Literal["WINTER", "SPRING", "SUMMER", "FALL"]
    seasonYear: int
    coverImage: dict[str, str]
    rankings: list[_AnilistRaking]
    countryOfOrigin: str
    averageScore: int
    meanScore: int
    synonyms: list[str]
    trailer: _AnilistTrailer
    tags: list[_AnilistTag]
    siteUrl: str
    episodes: int
    duration: int
    genres: list[str]
    relations: dict
    bannerImage: str
