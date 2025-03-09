import math

def create_pagination_metadata(page, per_page, total_items, endpoint_args=None):
    """Helper function to create consistent pagination metadata"""
    # Calculate number of pages
    pages = math.ceil(total_items / per_page) if total_items > 0 else 1
    
    # Ensure page is within valid range
    page = max(1, min(page, pages))
    
    # Calculate start and end indexes for display
    start_idx = (page - 1) * per_page + 1 if total_items > 0 else 0
    end_idx = min(start_idx + per_page - 1, total_items)
    
    # Calculate page range (show 5 pages around current page)
    page_range_radius = 2
    page_range_start = max(1, page - page_range_radius)
    page_range_end = min(pages, page + page_range_radius)
    
    # Ensure we always show at least 5 pages when possible
    if page_range_end - page_range_start + 1 < min(5, pages):
        if page_range_start == 1:
            page_range_end = min(5, pages)
        elif page_range_end == pages:
            page_range_start = max(1, pages - 4)
    
    # Other args to preserve in pagination links
    other_args = endpoint_args or {}
    if 'page' in other_args:
        other_args.pop('page')
        
    return {
        'page': page,
        'per_page': per_page,
        'pages': pages,
        'total': total_items,
        'has_prev': page > 1,
        'has_next': page < pages,
        'start_idx': start_idx,
        'end_idx': end_idx,
        'page_range_start': page_range_start,
        'page_range_end': page_range_end,
        'other_args': other_args
    }
