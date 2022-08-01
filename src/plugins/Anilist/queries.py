SEARCH_QUERY = """
query ($page: Int = 1, $id: Int, $type: MediaType, $isAdult: Boolean = false, $search: String, $status: MediaStatus, $source: MediaSource, $season: MediaSeason, $seasonYear: Int, $year: String, $yearLesser: FuzzyDateInt, $yearGreater: FuzzyDateInt, $sort: [MediaSort] = [POPULARITY_DESC, SCORE_DESC]) {
  Page(page: $page, perPage: 5) {
    pageInfo {
      currentPage
      hasNextPage
    }
    media(id: $id, type: $type, season: $season, status: $status, source: $source, search: $search, seasonYear: $seasonYear, startDate_like: $year, startDate_lesser: $yearLesser, startDate_greater: $yearGreater, sort: $sort, isAdult: $isAdult) {
      id
      title {
        english
        romaji
        native
      }
      description
    }
  }
}
"""

INFO_QUERY = """
query ($page: Int = 1, $id: Int, $type: MediaType, $isAdult: Boolean = false, $search: String, $sort: [MediaSort] = [POPULARITY_DESC, SCORE_DESC]) {
  Page(page: $page, perPage: 1) {
    pageInfo {
      currentPage
      hasNextPage
    }
    media(id: $id, type: $type, search: $search, sort: $sort, isAdult: $isAdult) {
      id
      title {
        english
        romaji
      }
      description
      status
      startDate {
        year
        month
        day
      }
      endDate {
        year
        month
        day
      }
      episodes
      season
      seasonYear
      bannerImage
      coverImage {
        large
        color
      }
      rankings {
        type
        allTime
      }
      countryOfOrigin
      averageScore
      meanScore
      synonyms
      trailer {
        site
        id
      }
      tags {
        name
      }
      siteUrl
      episodes
      duration
      genres
      relations {
        nodes {
          title {
            romaji
          }
          siteUrl
        }
      }
      stats {
        scoreDistribution {
          score
          amount
      	}
      }
    }
  }
}
"""
