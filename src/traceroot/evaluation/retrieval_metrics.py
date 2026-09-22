def recall_at_k(
    relevant_sources: list[str],
    retrieved_sources: list[str],
    k: int,
) -> float:
    """
    Calculate recall at k for a single query.

    Args:
        relevant_sources (list[str]): List of relevant sources for the query.
        retrieved_sources (list[str]): List of sources retrieved by the system.
        k (int): The number of top retrieved sources to consider.

    Returns:
        float: Recall at k, which is the proportion of relevant sources found in the top k retrieved sources.
    """
    if not relevant_sources:
        raise ValueError("relevant_sources must not be empty")

    if k <= 0:
        raise ValueError("k must be greater than 0")

    # Limit the retrieved sources to the top k
    top_k_retrieved = set(retrieved_sources[:k])
    relevant_set = set(relevant_sources)

    # Calculate the number of relevant sources found in the top k
    relevant_found = len(top_k_retrieved.intersection(relevant_set))

    # Calculate recall at k
    recall = relevant_found / len(relevant_set)
    return recall