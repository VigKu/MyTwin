import numpy as np
from sentence_transformers import SentenceTransformer
from rapidfuzz import process, fuzz
from typing import Optional, Tuple

class LRUSemanticPromptCache:
    def __init__(self, threshold: float = 0.85, lexical_threshold:float = 95.0 ,max_size: int = 15, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize the LRU semantic prompt cache.
        :param threshold: Minimum cosine similarity score (0.0 to 1.0) to trigger a cache hit.
        :param max_size: Maximum number of prompts to store before evicting the least recently used.
        :param embedding_model: The local huggingface model used to vectorize prompts.
        """
        self.threshold = threshold
        self.lexical_threshold = lexical_threshold
        self.max_size = max_size
        self.model = SentenceTransformer(embedding_model)
        
        # Parallel lists representing our cache tracking order.
        # Index 0 is always the Least Recently Used (oldest/coldest).
        # The last index is always the Most Recently Used (newest/freshest).
        self.cache_prompts = []     
        self.cache_embeddings = []  
        self.cache_responses = []   

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        dot_product = np.dot(vec1, vec2)
        norm_a = np.linalg.norm(vec1)
        norm_b = np.linalg.norm(vec2)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot_product / (norm_a * norm_b))

    def query(self, prompt: str) -> Tuple[Optional[str], Optional[float]]:
        if not self.cache_prompts:
            return None, None


        #Tier 1 Find the highest lexical match
        lex_score = 0
        # Find the single closest match using word-order insensitive scoring
        lex_match = process.extractOne(
            prompt, 
            self.cache_prompts, 
            # scorer=fuzz.token_sort_ratio
        )
        if lex_match:
            _, lex_score, lex_index = lex_match
            # If the structural similarity is incredibly high, hit the cache
            print(f"Lexcial Similarity: {lex_score:.2f}%)")
            if lex_score >= self.lexical_threshold:
                print(f"⚡ Lexical Cache Hit! (Lexcial Similarity: {lex_score:.2f}%)")
                # Extract the hit elements
                hit_prompt = self.cache_prompts.pop(lex_index)
                hit_embedding = self.cache_embeddings.pop(lex_index)
                hit_response = self.cache_responses.pop(lex_index)
                
                # Append them to the end to mark them as "Most Recently Used"
                self.cache_prompts.append(hit_prompt)
                self.cache_embeddings.append(hit_embedding)
                self.cache_responses.append(hit_response)

                return hit_response, lex_score

        #Tier 2 Find the highest semantic match
        query_embedding = self.model.encode(prompt)
        best_score = -1.0
        best_index = -1

        for idx, cached_emb in enumerate(self.cache_embeddings):
            score = self._cosine_similarity(query_embedding, cached_emb)
            if score > best_score:
                best_score = score
                best_index = idx

        # Check if the closest match satisfies our similarity threshold
        if best_score >= self.threshold:
            # --- LRU UPDATE LOGIC ---
            # Extract the hit elements
            hit_prompt = self.cache_prompts.pop(best_index)
            hit_embedding = self.cache_embeddings.pop(best_index)
            hit_response = self.cache_responses.pop(best_index)
            
            # Append them to the end to mark them as "Most Recently Used"
            self.cache_prompts.append(hit_prompt)
            self.cache_embeddings.append(hit_embedding)
            self.cache_responses.append(hit_response)
            
            return hit_response, best_score
        
        return None, best_score

    def add(self, prompt: str, response: str):
        """Add a new prompt. Evicts the Least Recently Used (index 0) if capacity is reached."""
        # Check if we are at capacity before adding a new item
        if len(self.cache_prompts) >= self.max_size:
            print(f"-> [CACHE FULL] Limit of {self.max_size} reached. Evicting the Least Recently Used (LRU) entry.")
            # Evict index 0 since it hasn't been used or queried in the longest time
            self.cache_prompts.pop(0)
            self.cache_embeddings.pop(0)
            self.cache_responses.pop(0)

        # Add the brand-new entry to the end (Most Recently Used position)
        embedding = self.model.encode(prompt)
        self.cache_prompts.append(prompt)
        self.cache_embeddings.append(embedding)
        self.cache_responses.append(response)
