# utils/program_filters.py
# Application-layer filtering for program discovery results.
# Discovery returns all programs; business logic decides what to show.

from typing import List


def filter_by_degree_level(
    programs: List[dict],
    levels: List[str],
) -> List[dict]:
    """
    Filter programs by degree level.
    
    Args:
        programs: List of program dicts with 'degree_level' key
        levels: List of degree levels to keep (e.g., ["Master's", "PhD", "Doctoral", "MBA"])
    
    Returns:
        Filtered list of programs matching the specified levels
    
    Examples:
        # Graduate programs only
        grad_programs = filter_by_degree_level(
            all_programs,
            ["Master's", "PhD", "Doctoral", "MBA", "MPhil"]
        )
        
        # Undergraduate only
        undergrad = filter_by_degree_level(
            all_programs,
            ["Bachelor's", "Associate's"]
        )
        
        # Master's only (no PhD)
        masters = filter_by_degree_level(
            all_programs,
            ["Master's", "MBA", "MPhil"]
        )
    """
    if not levels:
        return programs
    
    return [p for p in programs if p.get("degree_level") in levels]


def filter_graduate_programs(programs: List[dict]) -> List[dict]:
    """Convenience function: return only graduate-level programs."""
    return filter_by_degree_level(
        programs,
        ["Master's", "PhD", "Doctoral", "MBA", "MPhil"]
    )


def filter_undergraduate_programs(programs: List[dict]) -> List[dict]:
    """Convenience function: return only undergraduate programs."""
    return filter_by_degree_level(
        programs,
        ["Bachelor's", "Associate's"]
    )
