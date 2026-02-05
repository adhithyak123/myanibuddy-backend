import requests
from collections import defaultdict

def get_recommendations(user_ratings, all_ratings_data=None, max_per_genre=15):
    """
    Dynamic anime recommendations organized by genre
    Finds anime similar to what you rated highly, grouped by genre
    """
    
    if not user_ratings or len(user_ratings) < 1:
        return get_default_recommendations()
    
    # Get your favorite anime (rated 7+)
    favorites = [r for r in user_ratings if r["rating"] >= 7]
    
    if not favorites:
        favorites = sorted(user_ratings, key=lambda x: x["rating"], reverse=True)[:5]
    
    # Fetch similar anime with their genres
    all_recommendations = {}  # {anime_id: {'score': X, 'genres': [...]}}
    seen_ids = set([r["anime_id"] for r in user_ratings])
    
    print(f" Finding recommendations based on {len(favorites)} favorites...")
    
    for fav in favorites[:8]:  # Check top 8 favorites
        similar = fetch_similar_anime_with_genres(fav["anime_id"], fav["rating"])
        for anime_id, anime_data in similar.items():
            if anime_id not in seen_ids:
                if anime_id not in all_recommendations:
                    all_recommendations[anime_id] = anime_data
                else:
                    # If already seen, boost its score
                    all_recommendations[anime_id]['score'] += anime_data['score']
    
    print(f"✅ Found {len(all_recommendations)} unique recommendations")
    
    # Organize by genre
    genre_recommendations = defaultdict(list)
    
    for anime_id, data in all_recommendations.items():
        for genre in data.get('genres', ['Other']):
            genre_recommendations[genre].append({
                'id': anime_id,
                'score': data['score']
            })
    
    # Sort each genre by score and limit
    final_recommendations = {}
    for genre, anime_list in genre_recommendations.items():
        sorted_anime = sorted(anime_list, key=lambda x: x['score'], reverse=True)
        anime_ids = [a['id'] for a in sorted_anime[:max_per_genre]]
        if anime_ids:
            final_recommendations[genre] = anime_ids
    
    # Sort genres by number of recommendations (most popular first)
    sorted_genres = sorted(final_recommendations.items(), key=lambda x: len(x[1]), reverse=True)
    final_recommendations = dict(sorted_genres)
    
    print(f" Organized into {len(final_recommendations)} genres")
    
    # Always add a mixed "For You" section with top picks across all genres
    all_sorted = sorted(all_recommendations.items(), key=lambda x: x[1]['score'], reverse=True)
    top_picks = [anime_id for anime_id, _ in all_sorted[:20]]
    
    return {
        "⭐ Top Picks For You": top_picks,
        **final_recommendations
    }


def fetch_similar_anime_with_genres(anime_id, user_rating):
    """
    Fetch similar anime with their genres from Anilist
    """
    query = """
    query ($id: Int) {
      Media(id: $id, type: ANIME) {
        recommendations(sort: RATING_DESC, perPage: 15) {
          nodes {
            mediaRecommendation {
              id
              averageScore
              popularity
              genres
            }
          }
        }
        relations {
          nodes {
            id
            type
            averageScore
            genres
          }
        }
      }
    }
    """
    
    try:
        response = requests.post(
            'https://graphql.anilist.co',
            json={'query': query, 'variables': {'id': anime_id}},
            timeout=10
        )
        data = response.json()
        
        similar_anime = {}
        
        if 'data' in data and data['data']['Media']:
            media = data['data']['Media']
            
            # Add recommendations with genre info
            if media.get('recommendations'):
                for rec in media['recommendations']['nodes']:
                    if rec.get('mediaRecommendation'):
                        rec_anime = rec['mediaRecommendation']
                        anime_rec_id = rec_anime.get('id')
                        if anime_rec_id:
                            # Score based on popularity and user's rating
                            base_score = user_rating
                            popularity_bonus = (rec_anime.get('popularity', 0) / 10000)
                            score_bonus = (rec_anime.get('averageScore', 0) / 100)
                            
                            similar_anime[anime_rec_id] = {
                                'score': base_score + popularity_bonus + score_bonus,
                                'genres': rec_anime.get('genres', [])
                            }
            
            # Add related anime (sequels, side stories, etc)
            if media.get('relations'):
                for rel in media['relations']['nodes']:
                    rel_id = rel.get('id')
                    rel_type = rel.get('type')
                    if rel_id and rel_type in ['SEQUEL', 'PREQUEL', 'SIDE_STORY', 'ALTERNATIVE', 'SPIN_OFF']:
                        similar_anime[rel_id] = {
                            'score': user_rating * 1.5,  # Boost related anime
                            'genres': rel.get('genres', [])
                        }
        
        return similar_anime
    
    except Exception as e:
        print(f"❌ Error fetching similar anime for {anime_id}: {e}")
        return {}


def get_default_recommendations():
    """
    For new users - fetch trending anime organized by genre
    """
    query = """
    query {
      Page(page: 1, perPage: 50) {
        media(type: ANIME, sort: TRENDING_DESC, status: FINISHED) {
          id
          genres
        }
      }
    }
    """
    
    try:
        response = requests.post(
            'https://graphql.anilist.co',
            json={'query': query},
            timeout=10
        )
        data = response.json()
        
        if 'data' in data and data['data']['Page']:
            genre_map = defaultdict(list)
            
            for anime in data['data']['Page']['media']:
                anime_id = anime['id']
                for genre in anime.get('genres', ['Other']):
                    genre_map[genre].append(anime_id)
            
            # Limit each genre
            result = {}
            for genre, ids in genre_map.items():
                result[genre] = ids[:15]
            
            return result
        
    except Exception as e:
        print(f" Error fetching trending anime: {e}")
    
    return {
        "Trending Now": [5114, 16498, 11061, 1535, 9253, 30276, 38000, 40748, 28851, 32281]
    }