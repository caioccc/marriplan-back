from app.services.pinterest_service import *  # noqa: F401,F403from pinterest_dl import PinterestDL


def get_images(query, num_images=50):
    images = []
    try:
        images = PinterestDL.with_api().search(
            query=query,  # Search query for Pinterest
            num=num_images,  # Maximum number of images to scrape
            min_resolution=(200, 200),  # Minimum resolution for images
            delay=0.4,  # Delay between requests (default: 0.2)
        )
    except Exception as e:
        images = PinterestDL.with_browser(
            browser_type="chromium",  # Browser type to use ('chromium' or 'firefox')
            headless=True,  # Run browser in headless mode
            ensure_alt=True,  # Ensure every image has alt text (default: False)
        ).scrape(
            url="https://www.pinterest.com/search/pins/?q={}".format(query),  # URL to scrape
            num=num_images,  # Maximum number of images to scrape
        )
    return images
